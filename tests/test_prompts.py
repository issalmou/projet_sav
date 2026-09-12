"""Tests de app.ai.prompts (titre de conversation) et app.ai.agent.prompts (agent SAV)."""
import uuid

from app.ai.agent.prompts import build_agent_system_prompt, build_diagnostic_recap
from app.ai.prompts import build_title_prompt
from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent
from app.models.product import Product


def test_build_title_prompt_defaults_to_french():
    assert "français" in build_title_prompt()


def test_build_title_prompt_adapts_to_known_language():
    assert "anglais" in build_title_prompt("en")


def test_build_title_prompt_forbids_generic_titles():
    prompt = build_title_prompt()
    assert "générique" in prompt


def _product() -> Product:
    return Product(reference="IMP-X100", name="Imprimante X100", category="imprimantes")


def _prompt(**over) -> str:
    kw = dict(awaiting_ticket_confirmation=False, awaiting_step_feedback=False, escalation_allowed=False)
    kw.update(over)
    return build_agent_system_prompt(_product(), "fr", **kw)


def test_agent_prompt_pins_the_product_and_lists_all_tools():
    prompt = _prompt()

    assert "Imprimante X100" in prompt and "IMP-X100" in prompt
    assert "FIXÉ" in prompt  # produit non négociable
    for tool in (
        "search_docs",
        "get_warranty",
        "check_ticket_status",
        "submit_diagnosis",
        "record_client_feedback",
        "request_ticket_creation",
        "create_ticket",
        "decline_ticket_proposal",
        "escalate_to_technician",
    ):
        assert tool in prompt, tool
    assert "Réponds en français" in prompt


def test_agent_prompt_describes_the_interactive_method():
    prompt = _prompt()
    assert "search_docs" in prompt and "avant tout diagnostic" in prompt.lower()
    assert "NUMÉROTÉES" in prompt
    assert "persiste" in prompt  # question de vérification


def test_agent_prompt_adapts_language():
    assert "Réponds en anglais" in build_agent_system_prompt(
        _product(), "en", awaiting_ticket_confirmation=False, awaiting_step_feedback=False, escalation_allowed=False
    )


def test_agent_prompt_step_feedback_block_conditional():
    assert "EN ATTENTE DU RETOUR CLIENT" not in _prompt()
    assert "EN ATTENTE DU RETOUR CLIENT" in _prompt(awaiting_step_feedback=True)


def test_agent_prompt_escalation_block_conditional():
    assert "ESCALADE OBLIGATOIRE" not in _prompt()
    with_ = _prompt(escalation_allowed=True)
    assert "ESCALADE OBLIGATOIRE" in with_ and "escalate_to_technician" in with_


def test_agent_prompt_ticket_confirmation_block_conditional():
    assert "PROPOSITION DE TICKET EN ATTENTE" not in _prompt()
    with_ = _prompt(awaiting_ticket_confirmation=True)
    assert "PROPOSITION DE TICKET EN ATTENTE" in with_
    assert "create_ticket" in with_ and "decline_ticket_proposal" in with_


# --- build_diagnostic_recap ------------------------------------------


def _event(event_type: str, payload: dict) -> ConversationEvent:
    return ConversationEvent(conversation_id=uuid.uuid4(), event_type=event_type, payload=payload)


def test_diagnostic_recap_is_none_without_events():
    assert build_diagnostic_recap(Conversation(diagnostic_attempts=0), []) is None


def test_diagnostic_recap_summarises_searches_hypotheses_steps_feedback():
    conv = Conversation(diagnostic_attempts=2)
    events = [
        _event("search", {"query": "erreur E17", "titles": ["Guide E17"]}),
        _event("diagnosis", {"cause": "Bac papier mal inséré", "steps": ["Retirer le bac", "Réinsérer"]}),
        _event("feedback", {"resolved": False, "attempt": 1}),
        _event("diagnosis", {"cause": "Capteur HS", "steps": ["Remplacer le capteur"]}),
        _event("feedback", {"resolved": False, "attempt": 2}),
    ]

    recap = build_diagnostic_recap(conv, events)

    assert "erreur E17" in recap and "Guide E17" in recap
    assert "Bac papier mal inséré" in recap and "Capteur HS" in recap
    assert "série 1" in recap.lower() and "série 2" in recap.lower()
    assert "tentative 1" in recap.lower()
    assert "infructueuses : 2" in recap


def test_diagnostic_recap_size_is_bounded_by_escalation_threshold():
    """A2 : le récapitulatif n'implémente aucune troncature — sa taille reste
    néanmoins bornée car `submit_diagnosis` (M2) refuse tout nouveau
    diagnostic au-delà de `AGENT_ESCALATION_MAX_FAILED_ATTEMPTS`. Ce test
    construit le cas RÉEL le plus défavorable (le maximum d'événements
    diagnosis/feedback qu'une conversation peut effectivement accumuler,
    chacun avec le nombre maximal d'étapes) et vérifie que le résultat reste
    d'une taille raisonnable pour un prompt système — pas un test de
    troncature (il n'y en a pas), un test du BORNAGE réel du système."""

    from app.core.config import settings

    threshold = settings.AGENT_ESCALATION_MAX_FAILED_ATTEMPTS
    max_steps = 8  # app.ai.agent.tools._MAX_STEPS

    conv = Conversation(diagnostic_attempts=threshold)
    events = []
    for i in range(1, threshold + 1):
        events.append(_event("search", {"query": f"symptôme {i}", "titles": [f"Guide {i}"]}))
        events.append(
            _event(
                "diagnosis",
                {"cause": f"Cause hypothétique numéro {i}", "steps": [f"Étape {i}.{j}" for j in range(max_steps)]},
            )
        )
        events.append(_event("feedback", {"resolved": False, "attempt": i}))

    recap = build_diagnostic_recap(conv, events)

    assert recap is not None
    # généreux mais borné : un prompt système reste exploitable par un LLM,
    # même à petite fenêtre de contexte (cf. décision Ollama qwen2.5:3b).
    assert len(recap) < 4000, len(recap)


__all__: list[str] = []
