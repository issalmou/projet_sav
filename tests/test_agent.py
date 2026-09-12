"""Tests de l'agent SAV LangGraph (via ChatService.handle_message).

Déterministe : le fournisseur LLM est scripté (`ScriptedLLMProvider`) — chaque
`LLMResult` du script est un tour d'agent (texte OU appels d'outils). Le
retriever est un stub. La base de données est réelle (tickets, conversation).
"""
import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.ai.agent.context import AgentContext
from app.ai.agent.graph import (
    MAX_AGENT_ITERATIONS,
    _GENERIC_FALLBACK_REPLY,
    _gate_violation,
    _parse_pseudo_feedback_call,
    _strip_internal_leak,
    _strip_unanswered_tool_calls,
)
from app.ai.agent.tools import execute_tool
from app.ai.llm import LLMService
from app.ai.providers._openai_compatible import _to_openai_messages
from app.ai.providers.base import LLMResult, ToolCall
from app.ai.providers.gemini_provider import _to_gemini_contents
from app.ai.rag.retriever import RetrievedChunk
from app.database.session import AsyncSessionLocal
from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.client_product import ClientProductItem
from app.schemas.user import UserCreate
from app.services.chat_service import ChatService
from app.services.client_product_service import ClientProductService
from app.services.ticket_service import TicketService
from app.services.user_service import UserService
from conftest import ScriptedLLMProvider, StubRetriever, unique_email


def _tc(name, **args):
    return ToolCall(id=f"c_{uuid.uuid4().hex[:8]}", name=name, arguments=args)


def _chunk(text="Vérifiez le bac papier.", title="Guide E17"):
    return RetrievedChunk(text=text, document_id=uuid.uuid4(), title=title, category="faq", distance=0.1)


def _assert_openai_tool_pairing_is_valid(messages):
    """Réplique la contrainte des API chat/completions compatibles OpenAI
    (OpenAI, Qwen, Llama, Ollama) : un message `assistant` porteur de
    `tool_calls` DOIT être suivi immédiatement d'un message `tool` par
    `tool_call_id`. Lève `AssertionError` si la séquence est invalide."""

    converted = _to_openai_messages(messages)
    for i, msg in enumerate(converted):
        if msg["role"] != "assistant" or not msg.get("tool_calls"):
            continue
        expected_ids = {tc["id"] for tc in msg["tool_calls"]}
        answered: set[str] = set()
        for follow in converted[i + 1:]:
            if follow["role"] == "tool":
                answered.add(follow["tool_call_id"])
            else:
                break
        missing = expected_ids - answered
        assert not missing, f"tool_calls sans réponse d'outil: {missing}"


class _SequenceCheckingProvider:
    """Provider factice qui, en plus de rejouer un script d'appels d'outils,
    VÉRIFIE que chaque liste de messages reçue est acceptable par une API
    OpenAI-compatible. Enregistre les messages réellement transmis."""

    def __init__(self, tool_script):
        self._script = list(tool_script)
        self.text_turns: list[list] = []
        self.tool_turns: list[list] = []

    async def agenerate(self, messages, **kwargs):
        self.text_turns.append(messages)
        _assert_openai_tool_pairing_is_valid(messages)
        return "Réponse finale forcée (séquence valide)."

    async def agenerate_tools(self, messages, tools):
        self.tool_turns.append(messages)
        _assert_openai_tool_pairing_is_valid(messages)
        if not self._script:
            return LLMResult(text="Script épuisé.")
        return self._script.pop(0)


@pytest_asyncio.fixture
async def agent_world(db_session, role_ids, product):
    """Client (produit affecté) + conversation + 1 technicien actif."""

    us = UserService(db_session)
    client = await us.create_user(
        UserCreate(email=unique_email("agent.client"), password="ValidPass1", role_id=role_ids["client"])
    )
    await ClientProductService(db_session).assign_products(
        client.id, [ClientProductItem(product_id=product.id, qte=1)]
    )

    # neutraliser les vrais techniciens de dev, en créer un déterministe
    pre = (
        await db_session.execute(
            select(User).join(Role, Role.id == User.role_id).where(Role.name == "technicien", User.is_active.is_(True))
        )
    ).scalars().all()
    for u in pre:
        u.is_active = False
    tech = User(email=unique_email("agent.tech"), hashed_password="x", role_id=role_ids["technicien"], is_active=True)
    db_session.add(tech)
    await db_session.commit()
    await db_session.refresh(client)
    await db_session.refresh(tech)

    conversation = Conversation(user_id=client.id, product_id=product.id)
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    yield {"client": client, "tech": tech, "product": product, "conversation": conversation}

    await db_session.execute(delete(Ticket).where(Ticket.client_id == client.id))
    await db_session.execute(delete(Conversation).where(Conversation.id == conversation.id))
    await db_session.execute(delete(User).where(User.id.in_([client.id, tech.id])))
    await db_session.commit()
    for u in pre:
        row = await db_session.get(User, u.id)
        if row is not None:
            row.is_active = True
    if pre:
        await db_session.commit()


_TICKET_LLM_REPLY = "TITRE: Incident four\n\nProblème\n--------\nPanne rapportée\n\nRaison de l'escalade\n--------------------\nDiagnostic infructueux"


def _service(db_session, script, *, chunks=None, retriever=None, text_reply=_TICKET_LLM_REPLY):
    ret = retriever or StubRetriever(chunks or [])
    return ChatService(
        db_session,
        llm_service=LLMService(provider=ScriptedLLMProvider(script, text_reply=text_reply)),
        retriever=ret,
    ), ret


async def _send(service, world, text):
    return await service.handle_message(world["client"], world["conversation"].id, text)


# --- Réponses simples / outils -----------------------------------------


@pytest.mark.asyncio
async def test_plain_answer_without_tools(db_session, agent_world):
    """B6 (backend) : même un échange simple doit passer par search_docs puis
    submit_diagnosis avant toute réponse finale — ce n'est plus laissé au
    choix du LLM (cf. `app.ai.agent.graph._gate_violation`)."""

    service, _ = _service(
        db_session,
        [
            LLMResult(tool_calls=(_tc("search_docs", query="bonjour"),)),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Aucune piste identifiée", steps=["Décrire le problème plus précisément"]),)),
            LLMResult(text="Bonjour, pouvez-vous préciser le problème rencontré ?"),
        ],
    )

    result = await _send(service, agent_world, "Bonjour")

    assert result.message.content == "Bonjour, pouvez-vous préciser le problème rencontré ?"
    assert result.message.role == "assistant"
    assert result.ticket_id is None


@pytest.mark.asyncio
async def test_agent_uses_search_docs_then_answers(db_session, agent_world):
    service, retriever = _service(
        db_session,
        [
            LLMResult(tool_calls=(_tc("search_docs", query="erreur E17"),)),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Bac papier", steps=["Vérifier le bac papier"]),)),
            LLMResult(text="D'après la documentation, vérifiez le bac papier."),
        ],
        chunks=[_chunk()],
    )

    result = await _send(service, agent_world, "Mon imprimante affiche E17")

    assert "bac papier" in result.message.content
    # le RAG a été filtré sur le produit de la conversation (source de vérité)
    assert retriever.received_product_ids == [agent_world["product"].id]


@pytest.mark.asyncio
async def test_agent_uses_get_warranty(db_session, agent_world):
    agent_world["product"].warranty_months = 24
    db_session.add(agent_world["product"])
    await db_session.commit()

    service, _ = _service(
        db_session,
        [
            LLMResult(tool_calls=(_tc("get_warranty"),)),
            LLMResult(text="Votre produit est garanti 24 mois."),
        ],
    )
    result = await _send(service, agent_world, "Quelle est la garantie ?")
    assert "24 mois" in result.message.content


@pytest.mark.asyncio
async def test_agent_uses_several_tools_in_one_turn(db_session, agent_world):
    service, _ = _service(
        db_session,
        [
            LLMResult(tool_calls=(_tc("search_docs", query="panne"), _tc("get_warranty"))),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Panne générale", steps=["Vérifier l'alimentation"]),)),
            LLMResult(text="Réponse combinée."),
        ],
        chunks=[_chunk()],
    )
    result = await _send(service, agent_world, "Ma machine est en panne, et la garantie ?")
    assert result.message.content == "Réponse combinée."


# --- Workflow interactif : diagnostic multi-tour --------------------


async def _diagnose(service, world, symptom, cause="Cause probable", steps=("Étape A", "Étape B")):
    """Un tour complet : search_docs -> submit_diagnosis -> réponse avec étapes."""
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("search_docs", query=symptom),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause=cause, steps=list(steps)),)),
        LLMResult(text=f"Cause : {cause}. 1. {steps[0]} 2. {steps[1]}. Le problème persiste-t-il ?"),
    ]
    return await _send(service, world, symptom)


@pytest.mark.asyncio
async def test_diagnosis_records_state_and_events(db_session, agent_world):
    service, _ = _service(db_session, [], chunks=[_chunk()])
    r1 = await _diagnose(service, agent_world, "Mon imprimante affiche E17")

    assert "persiste" in r1.message.content
    assert r1.ticket_id is None
    await db_session.refresh(agent_world["conversation"])
    conv = agent_world["conversation"]
    assert conv.search_performed is True
    assert conv.awaiting_step_feedback is True
    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == conv.id).order_by(ConversationEvent.created_at)
        )
    ).scalars().all()
    assert [e.event_type for e in events] == ["search", "diagnosis"]


@pytest.mark.asyncio
async def test_branch_A_problem_resolved_creates_no_ticket(db_session, agent_world):
    """Branche A : question -> RAG -> étapes -> client OK -> AUCUN ticket."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon imprimante affiche E17")

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=True),)),
        LLMResult(text="Parfait, ravi que ce soit réglé."),
    ]
    r2 = await _send(service, agent_world, "C'est bon, ça fonctionne maintenant")

    assert r2.ticket_id is None
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].problem_resolved is True
    tickets = (await db_session.execute(select(Ticket).where(Ticket.client_id == agent_world["client"].id))).scalars().all()
    assert tickets == []


@pytest.mark.asyncio
async def test_branch_B_auto_escalation_after_threshold(db_session, agent_world):
    """Branche B : échec x2 -> escalade automatique -> ticket + technicien + description."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus", cause="Alimentation", steps=("Vérifier le câble", "Tester une prise"))

    # tour 2 : échec -> nouvelle recherche + nouvelles étapes (attempt 1)
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("search_docs", query="four voyant éteint"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Carte de puissance", steps=["Débrancher 30 s", "Rebrancher"]),)),
        LLMResult(text="Nouvelle piste : 1. Débranchez 30 s 2. Rebranchez. Le problème persiste-t-il ?"),
    ]
    r2 = await _send(service, agent_world, "j'ai testé, ça ne marche toujours pas")
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].diagnostic_attempts == 1
    assert r2.ticket_id is None

    # tour 3 : échec -> attempt 2 == seuil -> escalade automatique
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("escalate_to_technician", reason="Alimentation HS, non réparable à distance après 2 séries de vérifications"),)),
        LLMResult(text="Le problème persiste malgré les vérifications. Je crée un ticket pour un technicien."),
    ]
    r3 = await _send(service, agent_world, "toujours rien")

    assert r3.ticket_id is not None
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].diagnostic_attempts == 2

    ticket = await db_session.get(Ticket, r3.ticket_id)
    assert ticket.client_id == agent_world["client"].id           # depuis la conversation
    assert ticket.product_id == agent_world["product"].id          # depuis la conversation
    assert ticket.conversation_id == agent_world["conversation"].id
    assert ticket.assigned_technician_id == agent_world["tech"].id  # technicien choisi backend
    assert "toujours rien" not in ticket.description                # phrase client brute non recopiée
    assert ticket.description.strip()

    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == agent_world["conversation"].id)
        )
    ).scalars().all()
    assert {"escalation", "ticket"} <= {e.event_type for e in events}


@pytest.mark.asyncio
async def test_escalation_refused_before_threshold(db_session, agent_world):
    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus")

    # une seule tentative infructueuse, puis l'agent tente d'escalader trop tôt
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("escalate_to_technician", reason="je veux escalader tout de suite"),)),
        LLMResult(text="Essayons encore une chose."),
    ]
    r2 = await _send(service, agent_world, "ça ne marche pas")

    assert r2.ticket_id is None
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].diagnostic_attempts == 1
    tickets = (await db_session.execute(select(Ticket).where(Ticket.client_id == agent_world["client"].id))).scalars().all()
    assert tickets == []


@pytest.mark.asyncio
async def test_explicit_request_then_confirm_next_turn(db_session, agent_world):
    """Chemin 1 : le client DEMANDE un ticket. B2 : create refusé le même tour."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon imprimante fait un bruit anormal")

    # tour 2 : le client demande un ticket ; l'agent NE PEUT PAS create dans le même tour
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("request_ticket_creation", problem_summary="bruit anormal non résolu"),)),
        LLMResult(tool_calls=(_tc("create_ticket", description="hop"),)),  # tentative interdite (B2)
        LLMResult(text="Souhaitez-vous que je crée un ticket ? (oui/non)"),
    ]
    r2 = await _send(service, agent_world, "je préfère qu'un technicien vienne")
    assert r2.ticket_id is None
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].pending_ticket_confirmation is True

    # tour 3 : confirmation -> ticket créé
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("create_ticket", description="Bruit anormal, non résolu après diagnostic."),)),
        LLMResult(text="Votre ticket est créé."),
    ]
    r3 = await _send(service, agent_world, "oui, créez le ticket")
    assert r3.ticket_id is not None
    ticket = await db_session.get(Ticket, r3.ticket_id)
    assert ticket.product_id == agent_world["product"].id
    assert "oui, créez le ticket" not in ticket.description.lower()


@pytest.mark.asyncio
async def test_explicit_request_then_decline_clears_proposal_permanently(db_session, agent_world):
    """I2 : le client REFUSE la proposition -> decline_ticket_proposal clôt la
    proposition. Une confirmation tardive et hors contexte, plusieurs tours
    plus tard, ne doit alors JAMAIS créer de ticket lié à cette ancienne
    proposition caduque."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon imprimante fait un bruit anormal")

    # tour 2 : demande de ticket, proposition enregistrée
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("request_ticket_creation", problem_summary="bruit anormal non résolu"),)),
        LLMResult(text="Souhaitez-vous que je crée un ticket ? (oui/non)"),
    ]
    await _send(service, agent_world, "je préfère qu'un technicien vienne")
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].pending_ticket_confirmation is True

    # tour 3 : le client refuse clairement
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("decline_ticket_proposal"),)),
        LLMResult(tool_calls=(_tc("search_docs", query="bruit anormal imprimante"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Pièce mal fixée", steps=["Resserrer le capot"]),)),
        LLMResult(text="D'accord, essayons plutôt ceci. Le bruit persiste-t-il ?"),
    ]
    r3 = await _send(service, agent_world, "non merci, pas la peine")
    assert r3.ticket_id is None
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].pending_ticket_confirmation is False

    # tour 4 (bien plus tard) : un « oui » hors contexte ne doit RIEN créer,
    # car aucune proposition n'est plus en attente.
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=True),)),
        LLMResult(text="Très bien, ravi que ce soit réglé."),
    ]
    r4 = await _send(service, agent_world, "oui")
    assert r4.ticket_id is None

    tickets = (await db_session.execute(select(Ticket).where(Ticket.client_id == agent_world["client"].id))).scalars().all()
    assert tickets == []


@pytest.mark.asyncio
async def test_second_escalation_does_not_report_ticket_id(db_session, agent_world):
    """B3 : un ticket actif existe déjà -> aucun ticket_id renvoyé (rien créé ce tour)."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Panne persistante")
    agent_world["conversation"].diagnostic_attempts = 2
    db_session.add(agent_world["conversation"])
    await db_session.commit()

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("escalate_to_technician", reason="1"),)),
        LLMResult(text="Ticket créé."),
    ]
    r1 = await _send(service, agent_world, "toujours rien")
    assert r1.ticket_id is not None

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("escalate_to_technician", reason="2"),)),
        LLMResult(text="Un ticket est déjà ouvert."),
    ]
    r2 = await _send(service, agent_world, "et alors ?")

    assert r2.ticket_id is None
    count = (await db_session.execute(select(Ticket).where(Ticket.client_id == agent_world["client"].id))).scalars().all()
    assert len(count) == 1


# --- Garde-fou B6 : enchaînement search_docs -> submit_diagnosis ------
# -> record_client_feedback GARANTI par le backend, pas par le seul prompt.


class _FakeConv:
    def __init__(self, **kw):
        self.search_performed = kw.get("search_performed", False)
        self.awaiting_step_feedback = kw.get("awaiting_step_feedback", False)
        self.problem_resolved = kw.get("problem_resolved", False)


class _FakeGateCtx:
    """Double minimal de AgentContext : `_gate_violation` ne lit que ces 5 attributs."""

    def __init__(
        self,
        *,
        conv,
        tool_trace=(),
        created_ticket_id=None,
        turn_started_awaiting_feedback=False,
        has_active_ticket=False,
        escalation_allowed=False,
    ):
        self.conversation = conv
        self.tool_trace = list(tool_trace)
        self.created_ticket_id = created_ticket_id
        self.turn_started_awaiting_feedback = turn_started_awaiting_feedback
        self.has_active_ticket = has_active_ticket
        self.escalation_allowed = escalation_allowed


def test_gate_requires_search_docs_before_any_final_answer():
    ctx = _FakeGateCtx(conv=_FakeConv())
    assert _gate_violation(ctx) == "search_docs"


def test_gate_search_docs_attempt_satisfies_even_if_it_failed():
    """Un search_docs APPELÉ (même si son exécution a échoué, ex. RAG en
    panne) compte comme une tentative : sinon le backend boucle indéfiniment
    tant que le RAG est indisponible, sans jamais pouvoir répondre au client."""

    ctx = _FakeGateCtx(conv=_FakeConv(search_performed=False), tool_trace=["search_docs"])
    assert _gate_violation(ctx) is None


def test_gate_non_diagnostic_tools_exempt_search_docs():
    """Une question de garantie pure (get_warranty) ne doit pas forcer une
    recherche documentaire inutile."""

    ctx = _FakeGateCtx(conv=_FakeConv(), tool_trace=["get_warranty"])
    assert _gate_violation(ctx) is None


def test_gate_check_ticket_status_exempts_search_docs():
    ctx = _FakeGateCtx(conv=_FakeConv(), tool_trace=["check_ticket_status"])
    assert _gate_violation(ctx) is None


@pytest.mark.parametrize(
    "tool_name", ["request_ticket_creation", "create_ticket", "escalate_to_technician"]
)
def test_gate_refused_ticket_tool_attempt_does_not_exempt_search_docs(tool_name):
    """I1 : une TENTATIVE (refusée par sa précondition métier dans tools.py)
    de request_ticket_creation / create_ticket / escalate_to_technician ne
    doit JAMAIS dispenser de search_docs — sinon l'agent pourrait contourner
    le diagnostic obligatoire en tentant (et se faisant refuser) un de ces
    outils en tout premier message, puis en concluant en texte libre."""

    ctx = _FakeGateCtx(conv=_FakeConv(search_performed=False), tool_trace=[tool_name])
    assert _gate_violation(ctx) == "search_docs"


def test_gate_requires_submit_diagnosis_after_search():
    ctx = _FakeGateCtx(conv=_FakeConv(search_performed=True), tool_trace=["search_docs"])
    assert _gate_violation(ctx) == "submit_diagnosis"


def test_gate_satisfied_once_diagnosis_submitted_this_turn():
    ctx = _FakeGateCtx(
        conv=_FakeConv(search_performed=True), tool_trace=["search_docs", "submit_diagnosis"]
    )
    assert _gate_violation(ctx) is None


def test_gate_satisfied_when_awaiting_feedback_set_this_turn():
    """`submit_diagnosis` a mis `awaiting_step_feedback=True` : plus besoin de
    l'avoir dans `tool_trace`, l'état de la conversation suffit."""

    ctx = _FakeGateCtx(conv=_FakeConv(search_performed=True, awaiting_step_feedback=True))
    assert _gate_violation(ctx) is None


def test_gate_no_submit_diagnosis_needed_once_resolved():
    ctx = _FakeGateCtx(conv=_FakeConv(search_performed=True, problem_resolved=True))
    assert _gate_violation(ctx) is None


def test_gate_no_submit_diagnosis_needed_once_ticket_created():
    ctx = _FakeGateCtx(conv=_FakeConv(search_performed=True), created_ticket_id=uuid.uuid4())
    assert _gate_violation(ctx) is None


def test_gate_no_submit_diagnosis_needed_when_ticket_already_active_from_previous_turn():
    """C1 : un ticket actif créé lors d'un tour ANTÉRIEUR (donc absent de
    `ctx.created_ticket_id`, réinitialisé à chaque tour) dispense aussi de
    relancer un diagnostic — l'escalade est une étape terminale (CDC §17)."""

    ctx = _FakeGateCtx(conv=_FakeConv(search_performed=True), has_active_ticket=True)
    assert _gate_violation(ctx) is None


def test_gate_still_requires_submit_diagnosis_without_active_ticket():
    """Non-régression : sans ticket actif, la règle 3 continue de s'appliquer normalement."""

    ctx = _FakeGateCtx(conv=_FakeConv(search_performed=True), has_active_ticket=False)
    assert _gate_violation(ctx) == "submit_diagnosis"


def test_gate_forces_escalation_once_threshold_reached():
    """M2 : une fois le seuil de tentatives infructueuses atteint, c'est
    l'escalade elle-même qui devient obligatoire — plus un simple nouveau
    submit_diagnosis. Le backend empêche le LLM de repousser indéfiniment le
    transfert au technicien (CDC §17)."""

    ctx = _FakeGateCtx(conv=_FakeConv(search_performed=True), escalation_allowed=True)
    assert _gate_violation(ctx) == "escalate_to_technician"


def test_gate_satisfied_once_escalation_called_this_turn():
    ctx = _FakeGateCtx(
        conv=_FakeConv(search_performed=True),
        escalation_allowed=True,
        tool_trace=["escalate_to_technician"],
    )
    assert _gate_violation(ctx) is None


def test_gate_new_diagnosis_no_longer_satisfies_once_threshold_reached():
    """Un simple submit_diagnosis (sans escalade) ne suffit plus une fois le
    seuil atteint — contrairement au comportement avant M2."""

    ctx = _FakeGateCtx(
        conv=_FakeConv(search_performed=True),
        escalation_allowed=True,
        tool_trace=["submit_diagnosis"],
    )
    assert _gate_violation(ctx) == "escalate_to_technician"


def test_gate_requires_record_client_feedback_when_pending_at_turn_start():
    ctx = _FakeGateCtx(
        conv=_FakeConv(search_performed=True, awaiting_step_feedback=True),
        turn_started_awaiting_feedback=True,
    )
    assert _gate_violation(ctx) == "record_client_feedback"


def test_gate_satisfied_once_feedback_recorded_and_resolved():
    """`record_client_feedback(resolved=True)` clôt le cycle : plus de
    violation, même si `turn_started_awaiting_feedback` reste vrai (c'est un
    instantané pris à l'ouverture du tour, jamais mis à jour en cours de tour)."""

    ctx = _FakeGateCtx(
        conv=_FakeConv(search_performed=True, awaiting_step_feedback=False, problem_resolved=True),
        turn_started_awaiting_feedback=True,
        tool_trace=["record_client_feedback"],
    )
    assert _gate_violation(ctx) is None


def test_gate_requires_new_diagnosis_after_unresolved_feedback():
    """`record_client_feedback(resolved=False)` a bien libéré R1, mais R3
    prend immédiatement le relais : un NOUVEAU submit_diagnosis est requis
    avant de répondre — l'agent ne peut pas se contenter d'avoir enregistré
    l'échec, il doit relancer un vrai diagnostic (CDC : nouvelle tentative)."""

    ctx = _FakeGateCtx(
        conv=_FakeConv(search_performed=True, awaiting_step_feedback=False, problem_resolved=False),
        turn_started_awaiting_feedback=True,
        tool_trace=["record_client_feedback"],
    )
    assert _gate_violation(ctx) == "submit_diagnosis"


def test_gate_satisfied_after_feedback_and_new_diagnosis_same_turn():
    """Le cas réellement observé en usage réel : record_client_feedback(False)
    PUIS un nouveau submit_diagnosis dans le même tour — plus rien ne bloque."""

    ctx = _FakeGateCtx(
        conv=_FakeConv(search_performed=True, awaiting_step_feedback=True, problem_resolved=False),
        turn_started_awaiting_feedback=True,
        tool_trace=["record_client_feedback", "search_docs", "submit_diagnosis"],
    )
    assert _gate_violation(ctx) is None


# --- Filet de sécurité (Option B, point 12) : pseudo-invocation texte ---
# de record_client_feedback au lieu d'un vrai appel d'outil structuré.


def test_parse_pseudo_feedback_call_resolved_true():
    assert _parse_pseudo_feedback_call("record_client_feedback(resolved=true)") is True


def test_parse_pseudo_feedback_call_resolved_false():
    assert _parse_pseudo_feedback_call("record_client_feedback(resolved=false)") is False


def test_parse_pseudo_feedback_call_is_case_insensitive():
    assert _parse_pseudo_feedback_call("RECORD_CLIENT_FEEDBACK(RESOLVED=TRUE)") is True
    assert _parse_pseudo_feedback_call("Record_Client_Feedback(Resolved=False)") is False


def test_parse_pseudo_feedback_call_tolerates_extra_whitespace():
    assert _parse_pseudo_feedback_call("record_client_feedback (  resolved  =  false  )") is False


def test_parse_pseudo_feedback_call_embedded_in_a_sentence():
    text = "Je note votre retour : record_client_feedback(resolved=false) merci de votre patience."
    assert _parse_pseudo_feedback_call(text) is False


def test_parse_pseudo_feedback_call_no_match_on_plain_text():
    assert _parse_pseudo_feedback_call("Je vais enregistrer votre retour.") is None


def test_parse_pseudo_feedback_call_no_match_on_other_tool_name():
    assert _parse_pseudo_feedback_call("submit_diagnosis(resolved=false)") is None
    assert _parse_pseudo_feedback_call("not_record_client_feedback(resolved=false)") is None


def test_parse_pseudo_feedback_call_no_match_with_extra_parameters():
    assert _parse_pseudo_feedback_call('record_client_feedback(resolved=false, reason="x")') is None
    assert _parse_pseudo_feedback_call('record_client_feedback(reason="x", resolved=false)') is None


def test_parse_pseudo_feedback_call_no_match_on_invalid_value():
    assert _parse_pseudo_feedback_call("record_client_feedback(resolved=1)") is None
    assert _parse_pseudo_feedback_call('record_client_feedback(resolved="false")') is None
    assert _parse_pseudo_feedback_call("record_client_feedback(resolved=maybe)") is None


@pytest.mark.asyncio
async def test_gate_salvages_pseudo_feedback_call_and_continues_unresolved(db_session, agent_world):
    """Reproduit le cas réel observé avec Ollama (qwen2.5) : le modèle écrit
    `record_client_feedback(resolved=false)` comme texte au lieu de l'appeler.
    Le backend doit convertir cette pseudo-invocation en un VRAI appel de
    l'outil existant (compteur, événement), puis laisser l'agent reprendre
    normalement le diagnostic — sans perdre le tour ni fausser l'état."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus")

    service._agent._llm._provider._script[:] = [
        LLMResult(text="record_client_feedback(resolved=false)"),  # pseudo-invocation texte
        LLMResult(tool_calls=(_tc("search_docs", query="four voyant éteint"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Carte de puissance", steps=["Débrancher 30 s", "Rebrancher"]),)),
        LLMResult(text="Nouvelle piste : 1. Débranchez 30 s 2. Rebranchez. Le problème persiste-t-il ?"),
    ]
    result = await _send(service, agent_world, "j'ai testé, ça ne marche toujours pas")

    # la pseudo-syntaxe n'a jamais fuité au client, et une vraie réponse a été générée
    assert "record_client_feedback" not in result.message.content
    assert result.message.content == "Nouvelle piste : 1. Débranchez 30 s 2. Rebranchez. Le problème persiste-t-il ?"

    await db_session.refresh(agent_world["conversation"])
    conv = agent_world["conversation"]
    assert conv.diagnostic_attempts == 1  # vraiment incrémenté par le VRAI record_client_feedback
    assert conv.awaiting_step_feedback is True  # remis à True par le nouveau submit_diagnosis

    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == conv.id).order_by(ConversationEvent.created_at)
        )
    ).scalars().all()
    feedback_events = [e for e in events if e.event_type == "feedback"]
    assert len(feedback_events) == 1
    assert feedback_events[0].payload == {"resolved": False, "attempt": 1}


@pytest.mark.asyncio
async def test_gate_salvages_pseudo_feedback_call_resolved_true(db_session, agent_world):
    """Même mécanisme, mais resolved=true : conclut sans ticket, sans incrément."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus")

    service._agent._llm._provider._script[:] = [
        LLMResult(text="record_client_feedback(resolved=true)"),
        LLMResult(text="Parfait, ravi que ce soit réglé."),
    ]
    result = await _send(service, agent_world, "c'est bon, ça fonctionne")

    assert result.message.content == "Parfait, ravi que ce soit réglé."
    assert result.ticket_id is None
    await db_session.refresh(agent_world["conversation"])
    conv = agent_world["conversation"]
    assert conv.problem_resolved is True
    assert conv.diagnostic_attempts == 0
    tickets = (await db_session.execute(select(Ticket).where(Ticket.client_id == agent_world["client"].id))).scalars().all()
    assert tickets == []


@pytest.mark.asyncio
async def test_gate_does_not_salvage_when_record_client_feedback_is_not_the_required_action(db_session, agent_world):
    """Le salvage ne doit JAMAIS se déclencher en dehors du contexte où B6 a
    identifié record_client_feedback comme l'action requise — même si le texte
    produit par le LLM correspond au format strict. Ici, c'est search_docs qui
    est requis (aucun diagnostic n'était en attente) : le texte doit être
    traité comme une réponse prématurée ordinaire (nudge), pas comme un
    salvage, et l'outil ne doit surtout pas être exécuté par erreur."""

    service, _ = _service(
        db_session,
        [
            LLMResult(text="record_client_feedback(resolved=false)"),  # ne doit PAS être salvé ici
            LLMResult(tool_calls=(_tc("search_docs", query="four ne s'allume plus"),)),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Fusible", steps=["Vérifier le fusible"]),)),
            LLMResult(text="Cause probable : fusible. 1. Vérifiez le fusible. Le problème persiste-t-il ?"),
        ],
        chunks=[_chunk()],
    )

    result = await _send(service, agent_world, "Mon four ne s'allume plus")

    assert result.message.content == "Cause probable : fusible. 1. Vérifiez le fusible. Le problème persiste-t-il ?"
    await db_session.refresh(agent_world["conversation"])
    conv = agent_world["conversation"]
    assert conv.diagnostic_attempts == 0  # record_client_feedback n'a jamais été exécuté
    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == conv.id)
        )
    ).scalars().all()
    assert not any(e.event_type == "feedback" for e in events)


@pytest.mark.asyncio
async def test_gate_forces_full_sequence_end_to_end(db_session, agent_world):
    """Intégration : le LLM tente de répondre directement (aucun outil) —
    le backend refuse, injecte une consigne corrective et reboucle, jusqu'à
    ce que search_docs PUIS submit_diagnosis aient réellement été appelés.
    Aucune confiance dans le prompt seul : c'est le graphe qui l'impose."""

    service, _ = _service(
        db_session,
        [
            LLMResult(text="Voici quelques conseils généraux sans avoir rien vérifié."),  # rejeté (gate: search_docs)
            LLMResult(tool_calls=(_tc("search_docs", query="four ne s'allume plus"),)),
            LLMResult(text="D'après mon expérience, ça devrait aller."),  # rejeté (gate: submit_diagnosis)
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Fusible", steps=["Vérifier le fusible"]),)),
            LLMResult(text="Cause probable : fusible. 1. Vérifiez le fusible. Le problème persiste-t-il ?"),
        ],
        chunks=[_chunk()],
    )

    result = await _send(service, agent_world, "Mon four ne s'allume plus")

    # la réponse finale est bien la DERNIÈRE tentative conforme, pas les
    # tentatives prématurées rejetées par le garde-fou
    assert result.message.content == "Cause probable : fusible. 1. Vérifiez le fusible. Le problème persiste-t-il ?"
    assert "Voici quelques conseils" not in result.message.content
    assert "ça devrait aller" not in result.message.content

    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].search_performed is True
    assert agent_world["conversation"].awaiting_step_feedback is True

    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == agent_world["conversation"].id)
        )
    ).scalars().all()
    assert {"search", "diagnosis"} <= {e.event_type for e in events}


@pytest.mark.asyncio
async def test_gate_does_not_loop_forever_when_llm_never_complies(db_session, agent_world):
    """Si le LLM ignore systématiquement les consignes correctives, le
    garde-fou anti-boucle existant (`AGENT_MAX_ITERATIONS`) reste la limite
    ultime : le tour se termine quand même, avec une réponse (même imparfaite),
    jamais une boucle infinie.

    A1 : contrairement au comportement d'avant A1, `search_performed` doit
    désormais être VRAI — pas parce que le LLM l'a « prétendu » (il ne l'a
    jamais appelé), mais parce que le BACKEND lui-même a exécuté un vrai
    search_docs en dernier recours (`force_invariant_node`) avant de laisser
    sortir une réponse."""

    stubborn_script = [LLMResult(text=f"Réponse {i} sans aucun outil.") for i in range(MAX_AGENT_ITERATIONS + 3)]
    service, _ = _service(db_session, stubborn_script, chunks=[_chunk()])

    result = await _send(service, agent_world, "Mon four ne s'allume plus")

    assert result.message.content  # une réponse a bien été produite
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].search_performed is True
    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == agent_world["conversation"].id)
        )
    ).scalars().all()
    assert [e.event_type for e in events] == ["search"]  # un VRAI search_docs, exécuté une seule fois


# --- C1 : suivi après escalade (ticket actif = étape terminale) -----


@pytest.mark.asyncio
async def test_follow_up_after_escalation_does_not_force_new_diagnosis(db_session, agent_world):
    """C1 : une fois un ticket créé par escalade, un message de suivi du
    client (« des nouvelles ? ») doit pouvoir être traité via
    check_ticket_status SANS que le gate force un nouveau search_docs /
    submit_diagnosis — l'escalade est une étape terminale (CDC §17)."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus")

    # tour 2 : échec 1
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("search_docs", query="voyant éteint"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Carte de puissance", steps=["Débrancher 30 s"]),)),
        LLMResult(text="Nouvelle piste. Le problème persiste-t-il ?"),
    ]
    await _send(service, agent_world, "ça ne marche toujours pas")

    # tour 3 : échec 2 == seuil -> escalade automatique -> ticket créé
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("escalate_to_technician", reason="Panne non résolue après 2 tentatives"),)),
        LLMResult(text="Un ticket a été créé pour un technicien."),
    ]
    r3 = await _send(service, agent_world, "toujours rien")
    assert r3.ticket_id is not None

    # tour 4 : suivi -> check_ticket_status SEUL (pas de search_docs/submit_diagnosis)
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("check_ticket_status"),)),
        LLMResult(text="Votre ticket est bien ouvert, un technicien va vous contacter."),
    ]
    r4 = await _send(service, agent_world, "Avez-vous des nouvelles de mon ticket ?")

    assert r4.message.content == "Votre ticket est bien ouvert, un technicien va vous contacter."
    assert r4.ticket_id is None  # aucun NOUVEAU ticket créé ce tour

    # aucun nouvel événement de diagnostic (search/diagnosis) n'a été ajouté au tour 4
    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == agent_world["conversation"].id)
        )
    ).scalars().all()
    # exactement les événements des tours 1-3 : search, diagnosis, feedback, search, diagnosis, feedback, escalation, ticket
    assert len(events) == 8, [e.event_type for e in events]

    tickets = (await db_session.execute(select(Ticket).where(Ticket.client_id == agent_world["client"].id))).scalars().all()
    assert len(tickets) == 1  # toujours un seul ticket


@pytest.mark.asyncio
async def test_gate_resumes_normal_diagnosis_once_ticket_is_closed(db_session, agent_world):
    """Non-régression : une fois le ticket ACTIF fermé (`status='closed'`),
    le gate redevient exigeant comme avant — `has_active_ticket` reflète
    l'état réel en base, pas un simple souvenir figé."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus")

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("escalate_to_technician", reason="Panne non résolue"),)),
        LLMResult(text="Ticket créé."),
    ]
    agent_world["conversation"].diagnostic_attempts = 1  # une tentative de plus suffit pour atteindre le seuil (2)
    await db_session.commit()
    r2 = await _send(service, agent_world, "toujours rien")
    ticket_id = r2.ticket_id
    assert ticket_id is not None

    # le ticket est fermé (résolu par le technicien)
    ticket = await db_session.get(Ticket, ticket_id)
    ticket.status = "closed"
    await db_session.commit()

    # tour suivant : le client relance un problème -> le gate redevient
    # exigeant (plus aucun ticket actif ne le dispense). Le seuil
    # d'escalade (diagnostic_attempts) ne redescend jamais : conformément à
    # M2, c'est donc une NOUVELLE escalade (pas un nouveau submit_diagnosis)
    # qui est exigée — submit_diagnosis se refuserait lui-même (M2).
    service._agent._llm._provider._script[:] = [
        LLMResult(text="Tout devrait être réglé maintenant."),  # rejeté (gate: escalate_to_technician, ticket fermé + seuil déjà atteint)
        LLMResult(tool_calls=(_tc("escalate_to_technician", reason="Nouvelle panne, seuil déjà atteint précédemment"),)),
        LLMResult(text="Je crée un nouveau ticket pour cette nouvelle panne."),
    ]
    r3 = await _send(service, agent_world, "ça recommence")

    assert r3.message.content == "Je crée un nouveau ticket pour cette nouvelle panne."
    assert r3.ticket_id is not None
    assert r3.ticket_id != ticket_id  # un second ticket, distinct du premier (fermé)


# --- M2 : l'escalade devient obligatoire une fois le seuil atteint --


@pytest.mark.asyncio
async def test_gate_forces_escalation_when_llm_tries_yet_another_diagnosis(db_session, agent_world):
    """M2 : reproduit le contournement identifié en review — après avoir
    atteint le seuil d'échecs, le LLM tente de proposer ENCORE un nouveau
    diagnostic au lieu d'escalader. Le gate doit refuser et forcer
    escalate_to_technician."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus")

    # tour 2 : échec 1
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("search_docs", query="voyant éteint"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Carte de puissance", steps=["Débrancher 30 s"]),)),
        LLMResult(text="Nouvelle piste. Le problème persiste-t-il ?"),
    ]
    await _send(service, agent_world, "ça ne marche toujours pas")

    # tour 3 : échec 2 == seuil -> le LLM tente ENCORE un nouveau diagnostic
    # au lieu d'escalader (refusé par l'outil lui-même, cf. M2), puis finit
    # par escalader (accepté).
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Encore une autre piste", steps=["Vérifier X"]),)),
        LLMResult(tool_calls=(_tc("escalate_to_technician", reason="Panne non résolue après 2 séries de vérifications"),)),
        LLMResult(text="Le problème persiste. Je crée un ticket pour un technicien."),
    ]
    r3 = await _send(service, agent_world, "toujours rien")

    assert r3.ticket_id is not None
    assert r3.message.content == "Le problème persiste. Je crée un ticket pour un technicien."
    await db_session.refresh(agent_world["conversation"])
    # le submit_diagnosis refusé (seuil atteint) n'a rien enregistré :
    # aucun nouvel événement "diagnosis" pour ce tour.
    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == agent_world["conversation"].id)
        )
    ).scalars().all()
    diagnosis_events = [e for e in events if e.event_type == "diagnosis"]
    assert len(diagnosis_events) == 2  # uniquement les 2 diagnostics légitimes (tours 1 et 2)
    assert agent_world["conversation"].awaiting_step_feedback is False


# --- I1 : impossible de contourner search_docs via un outil refusé --


@pytest.mark.asyncio
async def test_premature_escalation_attempt_does_not_bypass_search_docs(db_session, agent_world):
    """I1 : reproduit exactement le contournement identifié en review — le LLM
    tente escalate_to_technician en tout premier message (refusé : seuil non
    atteint), puis essaie de conclure en texte libre. Le gate doit forcer
    search_docs malgré la tentative d'outil non-diagnostique."""

    service, _ = _service(
        db_session,
        [
            LLMResult(tool_calls=(_tc("escalate_to_technician", reason="je veux un technicien tout de suite"),)),
            LLMResult(text="Un technicien vous recontactera."),  # rejeté (gate: search_docs toujours requis)
            LLMResult(tool_calls=(_tc("search_docs", query="four ne s'allume plus"),)),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Fusible", steps=["Vérifier le fusible"]),)),
            LLMResult(text="Cause probable : fusible. Le problème persiste-t-il ?"),
        ],
        chunks=[_chunk()],
    )

    result = await _send(service, agent_world, "Mon four ne s'allume plus")

    assert result.message.content == "Cause probable : fusible. Le problème persiste-t-il ?"
    assert "technicien vous recontactera" not in result.message.content.lower()
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].search_performed is True
    tickets = (await db_session.execute(select(Ticket).where(Ticket.client_id == agent_world["client"].id))).scalars().all()
    assert tickets == []  # l'escalade prématurée a bien été refusée par escalate_to_technician lui-même


# --- A3 : filet de sécurité contre la fuite de contenu interne ------


def test_strip_internal_leak_replaces_leaked_recap_verbatim():
    leaked = (
        "[RÉCAPITULATIF DU DIAGNOSTIC EN COURS — USAGE INTERNE UNIQUEMENT, JAMAIS VISIBLE PAR LE CLIENT]\n"
        "- Recherches documentaires : \"erreur E17\"\n"
        "Voici où nous en sommes."
    )
    assert _strip_internal_leak(leaked) == _GENERIC_FALLBACK_REPLY


def test_strip_internal_leak_replaces_paraphrased_recap():
    """Reproduit le cas réel observé avec Ollama (qwen2.5) : le modèle ne
    recopie pas le bloc mot pour mot mais en cite la formule distinctive."""

    paraphrased = "Pour rappel, voici le récapitulatif du diagnostic en cours que j'ai noté : bac papier vérifié."
    assert _strip_internal_leak(paraphrased) == _GENERIC_FALLBACK_REPLY


def test_strip_internal_leak_leaves_normal_reply_untouched():
    normal = "D'après la documentation, vérifiez le bac papier. Le problème persiste-t-il ?"
    assert _strip_internal_leak(normal) == normal


@pytest.mark.asyncio
async def test_agent_reply_leaking_recap_is_replaced_end_to_end(db_session, agent_world):
    """A3 : reproduit le cas réel observé — le LLM répète le contenu du
    récapitulatif interne dans sa réponse finale. Le client ne doit JAMAIS
    recevoir ce texte, même si le gate lui-même est par ailleurs satisfait."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus")

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("search_docs", query="voyant éteint"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Carte de puissance", steps=["Débrancher 30 s"]),)),
        LLMResult(
            text=(
                "[RÉCAPITULATIF DU DIAGNOSTIC EN COURS — USAGE INTERNE UNIQUEMENT, JAMAIS VISIBLE PAR LE CLIENT]\n"
                "- Hypothèses déjà avancées : Alimentation\n"
                "Voici où nous en sommes, essayez de débrancher 30 secondes."
            )
        ),
    ]
    result = await _send(service, agent_world, "ça ne marche toujours pas")

    assert result.message.content == _GENERIC_FALLBACK_REPLY
    assert "RÉCAPITULATIF" not in result.message.content


# --- A1 : dernier recours quand le LLM ignore les nudges jusqu'au quota --


@pytest.mark.asyncio
async def test_force_invariant_escalates_when_llm_ignores_escalation_nudge(db_session, agent_world):
    """A1 : une fois l'escalade obligatoire (M2), si le LLM ignore
    systématiquement le nudge escalate_to_technician jusqu'à épuisement du
    quota, le backend escalade lui-même en dernier recours — jamais de
    réponse qui esquive indéfiniment le transfert au technicien."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus")

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("search_docs", query="voyant éteint"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Carte de puissance", steps=["Débrancher 30 s"]),)),
        LLMResult(text="Nouvelle piste. Le problème persiste-t-il ?"),
    ]
    await _send(service, agent_world, "ça ne marche toujours pas")

    stubborn = [LLMResult(text=f"Je ne sais plus quoi faire, tour {i}.") for i in range(MAX_AGENT_ITERATIONS + 3)]
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),  # attempt 2 == seuil
        *stubborn,
    ]
    result = await _send(service, agent_world, "toujours rien, je ne sais plus quoi faire")

    assert result.ticket_id is not None
    await db_session.refresh(agent_world["conversation"])
    ticket = await db_session.get(Ticket, result.ticket_id)
    assert ticket.client_id == agent_world["client"].id
    assert ticket.description.strip()  # description générée par le repli déterministe, jamais vide
    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == agent_world["conversation"].id)
        )
    ).scalars().all()
    assert {"escalation", "ticket"} <= {e.event_type for e in events}


# --- Point 4 : plusieurs sujets successifs dans la même conversation --


@pytest.mark.asyncio
async def test_new_issue_after_resolution_requires_fresh_diagnosis(db_session, agent_world):
    """Test obligatoire 1 : problème A résolu -> nouveau problème B -> nouveau
    diagnostic complet obligatoire (search_docs + submit_diagnosis), sans
    aucun changement de conversation ni de produit."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus", cause="Alimentation", steps=["Vérifier le câble", "Tester une prise"])

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=True),)),
        LLMResult(text="Parfait, ravi que ce soit réglé."),
    ]
    await _send(service, agent_world, "c'est bon ça marche")
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].problem_resolved is True

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("start_new_issue", summary="écran affiche une erreur"),)),
        LLMResult(text="Je vais regarder ça tout de suite."),  # rejeté (gate: search_docs requis pour le nouveau cycle)
        LLMResult(tool_calls=(_tc("search_docs", query="écran erreur"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Carte graphique", steps=["Redémarrer"]),)),
        LLMResult(text="Cause probable : carte graphique. Le problème persiste-t-il ?"),
    ]
    result = await _send(service, agent_world, "Maintenant l'écran affiche une erreur")

    assert result.message.content == "Cause probable : carte graphique. Le problème persiste-t-il ?"
    await db_session.refresh(agent_world["conversation"])
    conv = agent_world["conversation"]
    assert conv.problem_resolved is False  # nouveau cycle, l'ancien statut ne « fuit » pas
    assert conv.search_performed is True
    assert conv.awaiting_step_feedback is True
    assert conv.diagnostic_attempts == 0

    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == conv.id).order_by(ConversationEvent.created_at)
        )
    ).scalars().all()
    types_in_order = [e.event_type for e in events]
    assert "new_issue" in types_in_order
    # Test obligatoire 7 : les anciens événements (cycle 1) restent tous présents.
    assert types_in_order.count("search") == 2
    assert types_in_order.count("diagnosis") == 2
    assert types_in_order.count("feedback") == 1


@pytest.mark.asyncio
async def test_new_issue_can_reach_its_own_ticket_via_escalation(db_session, agent_world):
    """Test obligatoire 2 : problème A résolu -> problème B -> le nouveau
    cycle suit son propre workflow jusqu'à une escalade et un ticket, avec
    son propre compteur de tentatives repartant de zéro."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Problème A", cause="CauseA", steps=["EtapeA1", "EtapeA2"])
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=True),)),
        LLMResult(text="Réglé pour A."),
    ]
    await _send(service, agent_world, "ok réglé pour A")

    # Nouveau cycle B, qui échoue deux fois de suite -> escalade automatique.
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("start_new_issue", summary="Problème B"),)),
        LLMResult(tool_calls=(_tc("search_docs", query="B"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="CauseB1", steps=["EtapeB1", "EtapeB2"]),)),
        LLMResult(text="Cause B1. Persiste ?"),
    ]
    await _send(service, agent_world, "Problème B maintenant")

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("search_docs", query="B encore"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="CauseB2", steps=["EtapeB3"]),)),
        LLMResult(text="Cause B2. Persiste ?"),
    ]
    r2 = await _send(service, agent_world, "toujours pas pour B")
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].diagnostic_attempts == 1  # compteur du cycle B, pas hérité de A
    assert r2.ticket_id is None

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("escalate_to_technician", reason="Problème B non résolu après 2 tentatives"),)),
        LLMResult(text="Un ticket est créé pour le problème B."),
    ]
    r3 = await _send(service, agent_world, "toujours rien pour B")

    assert r3.ticket_id is not None
    ticket = await db_session.get(Ticket, r3.ticket_id)
    assert "CauseA" not in ticket.description  # le ticket décrit B, pas A (pas de mélange)
    assert ticket.client_id == agent_world["client"].id


@pytest.mark.asyncio
async def test_new_issue_without_prior_resolution_is_refused(db_session, agent_world):
    """start_new_issue doit être refusé tant que le diagnostic en cours n'est
    pas réellement terminé — sinon il permettrait d'esquiver
    submit_diagnosis / record_client_feedback."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus")  # awaiting_step_feedback=True, jamais résolu

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("start_new_issue", summary="autre problème"),)),
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),  # le vrai outil requis est toujours exigé
        LLMResult(tool_calls=(_tc("search_docs", query="four voyant éteint"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Carte de puissance", steps=["Débrancher 30 s"]),)),
        LLMResult(text="Nouvelle piste. Le problème persiste-t-il ?"),
    ]
    result = await _send(service, agent_world, "toujours rien, mais aussi un autre souci")

    # start_new_issue a été refusé (aucun reset) ; le workflow normal du
    # cycle 1 (toujours en cours) a repris la main.
    assert result.message.content == "Nouvelle piste. Le problème persiste-t-il ?"
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].diagnostic_attempts == 1
    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == agent_world["conversation"].id)
        )
    ).scalars().all()
    assert not any(e.event_type == "new_issue" for e in events)


@pytest.mark.asyncio
async def test_new_issue_after_active_ticket_is_refused_until_ticket_closes(db_session, agent_world):
    """Test obligatoire 3 : ticket actif du problème A -> nouveau problème B
    -> start_new_issue refusé tant que le ticket est actif (aucun deuxième
    ticket actif possible, et le nouveau sujet attend la fermeture)."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Mon four ne s'allume plus")

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
        LLMResult(tool_calls=(_tc("escalate_to_technician", reason="Panne non résolue"),)),
        LLMResult(text="Un ticket a été créé pour un technicien."),
    ]
    agent_world["conversation"].diagnostic_attempts = 1  # +1 via feedback -> atteint le seuil (2)
    await db_session.commit()
    r2 = await _send(service, agent_world, "toujours rien")
    ticket_id = r2.ticket_id
    assert ticket_id is not None

    # Test obligatoire 4 : le client peut consulter le statut sans relance
    # inutile d'un diagnostic pour l'ANCIEN problème.
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("check_ticket_status"),)),
        LLMResult(text="Votre ticket est bien ouvert, un technicien va vous contacter."),
    ]
    r3 = await _send(service, agent_world, "Des nouvelles de mon ticket ?")
    assert r3.message.content == "Votre ticket est bien ouvert, un technicien va vous contacter."
    assert r3.ticket_id is None  # aucun nouveau ticket

    # Nouveau problème B pendant que le ticket A est encore actif -> refusé.
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("start_new_issue", summary="problème d'écran"),)),
        LLMResult(text="D'accord, un technicien va s'occuper de tout ça."),
    ]
    r4 = await _send(service, agent_world, "Et en plus l'écran a un problème")
    assert r4.ticket_id is None
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].search_performed is True  # pas réinitialisé : refus confirmé
    events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == agent_world["conversation"].id)
        )
    ).scalars().all()
    assert not any(e.event_type == "new_issue" for e in events)

    # Le ticket ferme -> le nouveau problème peut enfin démarrer un cycle.
    ticket = await db_session.get(Ticket, ticket_id)
    ticket.status = "closed"
    await db_session.commit()

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("start_new_issue", summary="problème d'écran"),)),
        LLMResult(tool_calls=(_tc("search_docs", query="écran"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Carte graphique", steps=["Redémarrer"]),)),
        LLMResult(text="Cause probable : carte graphique. Le problème persiste-t-il ?"),
    ]
    r5 = await _send(service, agent_world, "L'écran a toujours un problème")
    assert r5.message.content == "Cause probable : carte graphique. Le problème persiste-t-il ?"
    await db_session.refresh(agent_world["conversation"])
    assert agent_world["conversation"].diagnostic_attempts == 0  # cycle neuf
    tickets = (
        await db_session.execute(select(Ticket).where(Ticket.client_id == agent_world["client"].id))
    ).scalars().all()
    assert len(tickets) == 1  # toujours un seul ticket au total (test obligatoire 3)


@pytest.mark.asyncio
async def test_multiple_successive_issues_do_not_mix_recaps(db_session, agent_world):
    """Test obligatoire 6 : trois problèmes successifs résolus -> le
    récapitulatif interne du 3e cycle ne contient JAMAIS les hypothèses ou
    étapes des cycles précédents (pas de mélange de diagnostics)."""

    from app.ai.agent.prompts import build_diagnostic_recap

    service, _ = _service(db_session, [], chunks=[_chunk()])

    await _diagnose(service, agent_world, "Problème A", cause="CauseA", steps=["EtapeA1", "EtapeA2"])
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=True),)),
        LLMResult(text="Réglé pour A."),
    ]
    await _send(service, agent_world, "ok réglé pour A")

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("start_new_issue", summary="Problème B"),)),
        LLMResult(tool_calls=(_tc("search_docs", query="B"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="CauseB", steps=["EtapeB"]),)),
        LLMResult(text="Cause B. Persiste ?"),
    ]
    await _send(service, agent_world, "Problème B maintenant")
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=True),)),
        LLMResult(text="Réglé pour B."),
    ]
    await _send(service, agent_world, "ok réglé pour B")

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("start_new_issue", summary="Problème C"),)),
        LLMResult(tool_calls=(_tc("search_docs", query="C"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="CauseC", steps=["EtapeC"]),)),
        LLMResult(text="Cause C. Persiste ?"),
    ]
    await _send(service, agent_world, "Problème C maintenant")

    conv = agent_world["conversation"]
    await db_session.refresh(conv)
    all_events = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == conv.id).order_by(ConversationEvent.created_at)
        )
    ).scalars().all()

    # Historique complet : les 3 cycles sont tous présents (rien détruit).
    causes_in_db = [e.payload.get("cause") for e in all_events if e.event_type == "diagnosis"]
    assert causes_in_db == ["CauseA", "CauseB", "CauseC"]

    # Récapitulatif « vivant » du cycle 3 : ne contient QUE CauseC.
    recap = build_diagnostic_recap(conv, all_events)
    assert "CauseC" in recap
    assert "CauseA" not in recap
    assert "CauseB" not in recap


@pytest.mark.asyncio
async def test_concurrent_requests_across_issue_cycles_still_cap_one_active_ticket(db_session, agent_world):
    """Test obligatoire 8 : même après un nouveau cycle de diagnostic
    (start_new_issue), deux requêtes concurrentes sur la même conversation
    ne peuvent toujours pas créer deux tickets actifs — la contrainte DB
    (I3) reste la garantie ultime, indépendante du nombre d'incidents."""

    service, _ = _service(db_session, [], chunks=[_chunk()])
    await _diagnose(service, agent_world, "Problème A")
    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("record_client_feedback", resolved=True),)),
        LLMResult(text="Réglé."),
    ]
    await _send(service, agent_world, "ok réglé")

    service._agent._llm._provider._script[:] = [
        LLMResult(tool_calls=(_tc("start_new_issue", summary="Problème B"),)),
        LLMResult(tool_calls=(_tc("search_docs", query="B"),)),
        LLMResult(tool_calls=(_tc("submit_diagnosis", cause="CauseB", steps=["EtapeB"]),)),
        LLMResult(text="Cause B. Persiste ?"),
    ]
    await _send(service, agent_world, "Problème B maintenant")

    conv = agent_world["conversation"]
    await db_session.refresh(conv)
    conv.diagnostic_attempts = 2  # seuil atteint pour le cycle B
    await db_session.commit()
    conversation_id = conv.id
    user_id = conv.user_id

    async def _attempt(label: str) -> str:
        async with AsyncSessionLocal() as session:
            c = await session.get(Conversation, conversation_id)
            u = await session.get(User, user_id)
            local_ctx = AgentContext(
                session=session,
                user=u,
                conversation=c,
                retriever=StubRetriever([_chunk()]),
                ticket_service=TicketService(session),
                llm_service=LLMService(provider=ScriptedLLMProvider([], text_reply=_TICKET_LLM_REPLY)),
            )
            return await execute_tool(local_ctx, "escalate_to_technician", {"reason": label})

    results = await asyncio.gather(_attempt("requête A"), _attempt("requête B"))
    assert any("prise en charge" in r.lower() for r in results)
    assert any("déjà ouvert" in r.lower() for r in results)

    tickets = (
        await db_session.execute(select(Ticket).where(Ticket.conversation_id == conversation_id))
    ).scalars().all()
    assert len(tickets) == 1


# --- Robustesse ------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_error_is_surfaced_and_agent_recovers(db_session, agent_world):
    class BoomRetriever:
        async def retrieve(self, q, *, product_id=None):
            raise RuntimeError("ChromaDB down")

    service, _ = _service(
        db_session,
        [
            LLMResult(tool_calls=(_tc("search_docs", query="x"),)),
            LLMResult(text="La recherche documentaire est indisponible, mais voici une piste générale."),
        ],
        retriever=BoomRetriever(),
    )
    result = await _send(service, agent_world, "Aide-moi")
    assert "indisponible" in result.message.content
    assert result.ticket_id is None


@pytest.mark.asyncio
async def test_max_iterations_forces_a_final_text_answer(db_session, agent_world):
    # l'agent boucle : il ne renvoie QUE des appels d'outils
    loop_calls = [LLMResult(tool_calls=(_tc("search_docs", query=f"q{i}"),)) for i in range(MAX_AGENT_ITERATIONS + 3)]
    service, _ = _service(db_session, loop_calls, chunks=[_chunk()])
    # le nœud finalize appelle agenerate() -> ScriptedLLMProvider.text_reply
    service._agent._llm._provider._text_reply = "Réponse finale forcée."

    result = await _send(service, agent_world, "Question qui boucle")

    assert result.message.content == "Réponse finale forcée."


def test_strip_unanswered_tool_calls_removes_only_orphans():
    """B1 (unité) : un tour d'outils répondu est conservé tel quel ; un tour
    d'outils orphelin et sans texte est retiré."""

    messages = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "a", "name": "search_docs", "arguments": {}}]},
        {"role": "tool", "tool_call_id": "a", "name": "search_docs", "content": "ok"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "b", "name": "search_docs", "arguments": {}}]},
    ]

    out = _strip_unanswered_tool_calls(messages)

    assert out[2]["tool_calls"][0]["id"] == "a"  # tour répondu : intact
    assert not any(
        m.get("role") == "assistant" and any(tc["id"] == "b" for tc in m.get("tool_calls", []))
        for m in out
    )  # tour orphelin : retiré
    _assert_openai_tool_pairing_is_valid(out)


def test_strip_unanswered_tool_calls_keeps_assistant_text():
    """Un message assistant qui a DU TEXTE mais aussi un tool_call orphelin
    garde le texte, perd seulement le tool_call."""

    messages = [
        {"role": "assistant", "content": "Je vérifie…", "tool_calls": [{"id": "x", "name": "search_docs", "arguments": {}}]},
    ]

    out = _strip_unanswered_tool_calls(messages)

    assert out == [{"role": "assistant", "content": "Je vérifie…"}]


def _finalize_message_list():
    """Reproduit la liste que `finalize_node` transmet au provider quand le
    quota est atteint après un appel d'outil : 5 tours répondus + 1 orphelin,
    nettoyé par `_strip_unanswered_tool_calls`, puis le nudge `user`."""

    from app.ai.agent.graph import _FINALIZE_NUDGE

    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "boucle"}]
    for i in range(5):
        msgs.append(
            {"role": "assistant", "content": "", "tool_calls": [{"id": f"c{i}", "name": "search_docs", "arguments": {"query": f"q{i}"}}]}
        )
        msgs.append({"role": "tool", "tool_call_id": f"c{i}", "name": "search_docs", "content": "res"})
    msgs.append(
        {"role": "assistant", "content": "", "tool_calls": [{"id": "c5", "name": "search_docs", "arguments": {"query": "q5"}}]}
    )
    return _strip_unanswered_tool_calls(msgs) + [{"role": "user", "content": _FINALIZE_NUDGE}]


def test_finalize_sequence_is_valid_for_openai_compatible_providers():
    """B1 : OpenAI, Qwen, Llama, Ollama et Mistral partagent `_to_openai_messages`."""

    final = _finalize_message_list()
    _assert_openai_tool_pairing_is_valid(final)
    converted = _to_openai_messages(final)
    assert converted[-1]["role"] == "user"  # Mistral exige user/tool en dernier


def test_finalize_sequence_is_valid_for_gemini():
    """B1 : chemin `agenerate` (finalize) de Gemini via `_to_gemini_contents`.

    La réponse d'outil Gemini est un tour "user" portant un `function_response`
    (l'API réelle rejette role="tool", cf. `test_real_gemini_tool_calling_round_trip`) :
    on vérifie donc la présence du `function_response`, pas un rôle littéral."""

    _system, contents = _to_gemini_contents(_finalize_message_list())

    for i, content in enumerate(contents):
        if any(getattr(part, "function_call", None) for part in content.parts):
            assert i + 1 < len(contents) and any(
                getattr(part, "function_response", None) for part in contents[i + 1].parts
            ), "un function_call Gemini n'est pas suivi de sa function_response"
    assert contents[-1].role == "user"


@pytest.mark.asyncio
async def test_finalize_after_tool_call_sends_openai_valid_sequence(db_session, agent_world):
    """B1 : quand AGENT_MAX_ITERATIONS est atteint alors que l'agent vient de
    demander un outil, le nœud `finalize` doit transmettre au provider une
    séquence de messages VALIDE (aucun `tool_calls` orphelin).

    Le test inspecte les messages RÉELLEMENT envoyés au provider — il ne
    dépend pas d'un provider qui les ignore."""

    script = [
        LLMResult(tool_calls=(_tc("search_docs", query=f"q{i}"),))
        for i in range(MAX_AGENT_ITERATIONS + 2)
    ]
    provider = _SequenceCheckingProvider(script)
    service = ChatService(
        db_session,
        llm_service=LLMService(provider=provider),
        retriever=StubRetriever([_chunk()]),
    )

    result = await service.handle_message(
        agent_world["client"], agent_world["conversation"].id, "question qui boucle"
    )

    # `agenerate` (finalize) n'a pas levé => la séquence était valide.
    assert result.message.content == "Réponse finale forcée (séquence valide)."
    assert provider.text_turns, "le nœud finalize n'a pas appelé le provider"

    final_messages = provider.text_turns[-1]
    _assert_openai_tool_pairing_is_valid(final_messages)  # explicite : ne lève pas
    assert final_messages[-1]["role"] == "user"  # le nudge de finalize, jamais "system"
    # le dernier message n'est plus un assistant porteur de tool_calls non satisfaits
    assert not any(
        m.get("role") == "assistant"
        and m.get("tool_calls")
        and any(
            tc["id"] not in {t.get("tool_call_id") for t in final_messages if t.get("role") == "tool"}
            for tc in m["tool_calls"]
        )
        for m in final_messages
    )


@pytest.mark.asyncio
async def test_history_is_passed_to_the_agent(db_session, agent_world):
    service1, _ = _service(
        db_session,
        [
            LLMResult(tool_calls=(_tc("search_docs", query="premier message"),)),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Cause 1", steps=["Étape 1"]),)),
            LLMResult(text="Premier tour."),
        ],
        chunks=[_chunk()],
    )
    await _send(service1, agent_world, "Premier message")

    # le diagnostic du 1er tour est en attente de retour client : le 2e tour
    # doit d'abord l'enregistrer (garde-fou B6) avant de pouvoir répondre.
    provider = ScriptedLLMProvider(
        [
            LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Cause 2", steps=["Étape 2"]),)),
            LLMResult(text="Deuxième tour."),
        ]
    )
    service2 = ChatService(db_session, llm_service=LLMService(provider=provider), retriever=StubRetriever([]))
    await service2.handle_message(agent_world["client"], agent_world["conversation"].id, "Deuxième message")

    # le 1er appel d'outils du 2e tour contient l'historique complet
    messages = provider.tool_turns[0]
    contents = [m.get("content") for m in messages]
    assert "Premier message" in contents
    assert "Premier tour." in contents
    assert "Deuxième message" in contents


__all__: list[str] = []
