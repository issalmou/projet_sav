"""Tests de TicketSummaryService : génération de la description/titre du ticket.

Sans DB : objets factices pour Conversation / Product / Message /
ConversationEvent (accès en lecture seule, duck-typing). Le LLM est un double.
"""
import types

import pytest

from app.ai.agent.ticket_summary import TicketSummaryService, _fallback_title, _parse_llm_reply
from app.ai.exceptions import LLMRequestError


def _conv(**over):
    d = dict(title="Panne imprimante", diagnostic_attempts=2, problem_resolved=False)
    d.update(over)
    return types.SimpleNamespace(**d)


def _product():
    return types.SimpleNamespace(name="Imprimante X100", reference="IMP-X100")


def _msg(role, content):
    return types.SimpleNamespace(role=role, content=content)


def _event(event_type, payload):
    return types.SimpleNamespace(event_type=event_type, payload=payload)


def _events():
    return [
        _event("search", {"query": "démarrage imprimante", "titles": ["Guide démarrage"]}),
        _event("diagnosis", {"cause": "Alimentation défaillante", "steps": ["Vérifier le câble", "Tester une autre prise"]}),
        _event("feedback", {"resolved": False, "attempt": 1}),
        _event("feedback", {"resolved": False, "attempt": 2}),
    ]


class _LLM:
    def __init__(self, reply):
        self._reply = reply
        self.calls = []

    async def generate_reply(self, messages):
        self.calls.append(messages)
        if isinstance(self._reply, Exception):
            raise self._reply
        return self._reply


HISTORY = [_msg("user", "Mon imprimante ne démarre plus"), _msg("assistant", "Essayons quelques vérifications."), _msg("user", "Toujours rien")]


# --- parsing --------------------------------------------------------


def test_parse_llm_reply_extracts_title_and_body():
    d = _parse_llm_reply("TITRE: Panne alimentation X100\n\nProblème\n--------\nNe démarre plus")
    assert d.title == "Panne alimentation X100"
    assert "Ne démarre plus" in d.description


def test_parse_llm_reply_empty_is_none():
    assert _parse_llm_reply("   ") is None


def test_parse_llm_reply_without_sentinel_keeps_body():
    d = _parse_llm_reply("Problème\n--------\ntexte")
    assert d.title == "" and "texte" in d.description


# --- titre fallback -----------------------------------------------


def test_fallback_title_replaces_generic_conversation_title():
    t = _fallback_title(_conv(title="Nouvelle conversation"), _product(), ["Mon imprimante ne démarre plus"])
    assert t.startswith("Mon imprimante")


def test_fallback_title_keeps_specific_conversation_title():
    assert _fallback_title(_conv(title="Erreur E17 imprimante"), _product(), []) == "Erreur E17 imprimante"


def test_fallback_title_uses_product_when_nothing_else():
    assert "Imprimante X100" in _fallback_title(_conv(title=None), _product(), [])


# --- build : LLM OK -------------------------------------------


@pytest.mark.asyncio
async def test_build_uses_llm_reply_when_available():
    llm = _LLM("TITRE: Titre du LLM\n\nProblème\n--------\nrédigé par le LLM")
    draft = await TicketSummaryService(llm).build(
        conversation=_conv(), product=_product(), history=HISTORY, events=_events(), escalation_reason="raison"
    )
    assert draft.title == "Titre du LLM"
    assert "rédigé par le LLM" in draft.description
    assert llm.calls  # le LLM a bien été sollicité


# --- build : repli déterministe -------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", [LLMRequestError("provider down"), "", "   "])
async def test_build_falls_back_deterministically(reply):
    draft = await TicketSummaryService(_LLM(reply)).build(
        conversation=_conv(), product=_product(), history=HISTORY, events=_events(),
        escalation_reason="Diagnostic infructueux après 2 tentatives",
    )

    assert draft.title.strip()
    for section in (
        "Problème",
        "Symptômes",
        "Diagnostic",
        "Étapes proposées",
        "Résultats des tentatives",
        "Documentation consultée",
        "Conclusion",
        "Raison de l'escalade",
    ):
        assert section in draft.description, section

    # contenu réellement issu de la conversation / du journal — rien d'inventé
    assert "Mon imprimante ne démarre plus" in draft.description
    assert "Alimentation défaillante" in draft.description
    assert "Vérifier le câble" in draft.description
    assert "démarrage imprimante" in draft.description
    assert "Tentative 1" in draft.description and "Tentative 2" in draft.description
    assert "Diagnostic infructueux après 2 tentatives" in draft.description

    # ordre des rubriques respecté
    positions = [draft.description.index(s) for s in ("Problème", "Diagnostic", "Conclusion", "Raison de l'escalade")]
    assert positions == sorted(positions)


@pytest.mark.asyncio
async def test_build_fallback_marks_missing_sections_not_renseigne():
    draft = await TicketSummaryService(_LLM(LLMRequestError("x"))).build(
        conversation=_conv(diagnostic_attempts=0), product=_product(),
        history=[_msg("user", "Bonjour, un souci")], events=[], escalation_reason=None,
    )
    assert "Non renseigné" in draft.description
    assert draft.description.strip()


@pytest.mark.asyncio
async def test_build_never_returns_empty_description():
    draft = await TicketSummaryService(_LLM("")).build(
        conversation=_conv(title=None, diagnostic_attempts=0), product=None, history=[], events=[], escalation_reason=None
    )
    assert draft.title.strip() and draft.description.strip()


__all__: list[str] = []
