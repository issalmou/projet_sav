"""Génération automatique du titre et de la description d'un ticket SAV.

La description est SYNTHÉTISÉE à partir de la conversation et du journal de
diagnostic réellement effectué (`ConversationEvent`) — jamais inventée. Deux
chemins :

1. LLM (`_build_with_llm`) : rédige une synthèse structurée pour le technicien ;
2. Repli déterministe (`_fallback`) : assemble les mêmes rubriques directement
   à partir des événements et de l'historique, sans LLM.

Le repli garantit qu'un ticket peut TOUJOURS être créé, même si le fournisseur
LLM est indisponible / renvoie une réponse vide. La description n'est jamais
vide ni inexploitable.
"""
from __future__ import annotations

from typing import NamedTuple

from app.ai.exceptions import LLMError
from app.ai.llm import LLMService
from app.core.logger import logger
from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent
from app.models.message import Message
from app.models.product import Product

_MAX_TITLE_LEN = 120
_TITLE_SENTINEL = "TITRE:"

_SECTION_ORDER = (
    "Problème",
    "Symptômes",
    "Diagnostic",
    "Étapes proposées",
    "Résultats des tentatives",
    "Documentation consultée",
    "Conclusion",
    "Raison de l'escalade",
)

_GENERIC_TITLE_HINTS = ("nouvelle conversation", "question du client", "conversation", "sans titre")


class TicketDraft(NamedTuple):
    title: str
    description: str


class TicketSummaryService:
    """Construit `TicketDraft(title, description)` pour un ticket créé par l'agent."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self._llm = llm_service or LLMService()

    async def build(
        self,
        *,
        conversation: Conversation,
        product: Product | None,
        history: list[Message],
        events: list[ConversationEvent],
        escalation_reason: str | None = None,
    ) -> TicketDraft:
        """Retourne un brouillon de ticket : LLM si possible, repli déterministe sinon."""

        fallback = self._fallback(conversation, product, history, events, escalation_reason)

        try:
            draft = await self._build_with_llm(product, history, events, escalation_reason)
        except LLMError:
            logger.warning("TicketSummary: LLM en échec, repli déterministe", exc_info=True)
            draft = None
        except Exception:  # défensif : un repli vaut toujours mieux qu'une 500
            logger.error("TicketSummary: échec inattendu, repli déterministe", exc_info=True)
            draft = None

        if draft is None:
            return fallback

        title = _clean_title(draft.title) or fallback.title
        description = draft.description.strip() or fallback.description
        return TicketDraft(title=title, description=description)

    # --- LLM ----------------------------------------------------------

    async def _build_with_llm(
        self,
        product: Product | None,
        history: list[Message],
        events: list[ConversationEvent],
        escalation_reason: str | None,
    ) -> TicketDraft | None:
        transcript = _render_transcript(history)
        journal = _render_event_journal(events)
        product_line = (
            f"{product.name} (réf. {product.reference})" if product is not None else "produit non précisé"
        )

        system = (
            "Tu rédiges, pour un technicien SAV, la synthèse d'un incident à partir d'une "
            "conversation client et du journal de diagnostic. Règles STRICTES :\n"
            "- n'invente RIEN : n'utilise que ce qui figure dans la conversation ou le journal ;\n"
            "- si une rubrique n'a pas d'information, écris « Non renseigné » ;\n"
            "- style factuel, concis, pas de formule de politesse.\n\n"
            "Format EXACT de ta réponse :\n"
            f"{_TITLE_SENTINEL} <titre technique court, une ligne>\n\n"
            + "\n\n".join(f"{name}\n{'-' * len(name)}\n<contenu>" for name in _SECTION_ORDER)
        )
        user = (
            f"Produit : {product_line}\n\n"
            f"=== Conversation ===\n{transcript or '(vide)'}\n\n"
            f"=== Journal de diagnostic ===\n{journal or '(vide)'}\n\n"
            f"=== Raison de l'escalade ===\n{escalation_reason or 'Non précisée'}"
        )

        raw = await self._llm.generate_reply(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        return _parse_llm_reply(raw)

    # --- Repli déterministe -----------------------------------------

    @staticmethod
    def _fallback(
        conversation: Conversation,
        product: Product | None,
        history: list[Message],
        events: list[ConversationEvent],
        escalation_reason: str | None,
    ) -> TicketDraft:
        user_msgs = [m.content.strip() for m in history if m.role == "user" and m.content.strip()]
        diagnosis_events = [e for e in events if e.event_type == "diagnosis"]
        feedback_events = [e for e in events if e.event_type == "feedback"]
        search_events = [e for e in events if e.event_type == "search"]

        problem = user_msgs[0] if user_msgs else "Non renseigné"
        symptoms = (
            "\n".join(f"- {m}" for m in user_msgs[1:]) if len(user_msgs) > 1 else "Non renseigné"
        )

        causes = [str(e.payload.get("cause", "")).strip() for e in diagnosis_events]
        causes = [c for c in causes if c]
        diagnostic = "\n".join(f"- {c}" for c in causes) if causes else "Non renseigné"

        steps_lines: list[str] = []
        for idx, e in enumerate(diagnosis_events, start=1):
            steps = [str(s).strip() for s in (e.payload.get("steps") or []) if str(s).strip()]
            if steps:
                steps_lines.append(f"Série {idx} :")
                steps_lines.extend(f"  {i}. {s}" for i, s in enumerate(steps, start=1))
        proposed_steps = "\n".join(steps_lines) if steps_lines else "Non renseigné"

        results_lines: list[str] = []
        for e in feedback_events:
            resolved = bool(e.payload.get("resolved"))
            attempt = e.payload.get("attempt")
            label = f"Tentative {attempt}" if attempt else "Retour client"
            results_lines.append(
                f"- {label} : {'problème résolu' if resolved else 'le problème persiste'}"
            )
        results = "\n".join(results_lines) if results_lines else "Non renseigné"

        doc_lines: list[str] = []
        for e in search_events:
            query = str(e.payload.get("query", "")).strip()
            titles = [str(t).strip() for t in (e.payload.get("titles") or []) if str(t).strip()]
            if query:
                suffix = f" → {', '.join(titles)}" if titles else " → aucun document pertinent"
                doc_lines.append(f'- « {query} »{suffix}')
        documentation = "\n".join(doc_lines) if doc_lines else "Non renseigné"

        if conversation.problem_resolved:
            conclusion = "Le client a confirmé la résolution du problème."
        else:
            n = conversation.diagnostic_attempts
            conclusion = (
                f"Problème non résolu après {n} tentative(s) de diagnostic documenté. "
                "Intervention d'un technicien nécessaire."
            )

        reason = (escalation_reason or "").strip() or (
            f"Diagnostic infructueux : {conversation.diagnostic_attempts} tentative(s) "
            "de résolution proposées au client sans succès."
        )

        sections = {
            "Problème": problem,
            "Symptômes": symptoms,
            "Diagnostic": diagnostic,
            "Étapes proposées": proposed_steps,
            "Résultats des tentatives": results,
            "Documentation consultée": documentation,
            "Conclusion": conclusion,
            "Raison de l'escalade": reason,
        }
        description = _render_sections(sections)
        return TicketDraft(title=_fallback_title(conversation, product, user_msgs), description=description)


# --- Helpers -------------------------------------------------------------


def _render_transcript(history: list[Message]) -> str:
    lines = []
    for m in history:
        role = "Client" if m.role == "user" else "Agent"
        content = (m.content or "").strip()
        if content:
            lines.append(f"{role} : {content}")
    return "\n".join(lines)


def _render_event_journal(events: list[ConversationEvent]) -> str:
    lines = []
    for e in events:
        lines.append(f"[{e.event_type}] {e.payload}")
    return "\n".join(lines)


def _render_sections(sections: dict[str, str]) -> str:
    blocks = []
    for name in _SECTION_ORDER:
        body = sections.get(name, "Non renseigné").strip() or "Non renseigné"
        blocks.append(f"{name}\n{'-' * len(name)}\n{body}")
    return "\n\n".join(blocks)


def _parse_llm_reply(raw: str) -> TicketDraft | None:
    text = (raw or "").strip()
    if not text:
        return None

    title = ""
    body_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not title and stripped.upper().startswith(_TITLE_SENTINEL):
            title = stripped[len(_TITLE_SENTINEL):].strip().strip('"').strip()
            continue
        body_lines.append(line)

    description = "\n".join(body_lines).strip()
    if not description:
        return None
    return TicketDraft(title=title, description=description)


def _clean_title(raw: str) -> str:
    title = (raw or "").strip().strip('"\'«»').strip().rstrip(".!")
    if len(title) <= _MAX_TITLE_LEN:
        return title
    return title[:_MAX_TITLE_LEN].rsplit(" ", 1)[0].rstrip(".,;:!?") + "…"


def _fallback_title(conversation: Conversation, product: Product | None, user_msgs: list[str]) -> str:
    existing = (conversation.title or "").strip()
    if existing and not any(hint in existing.lower() for hint in _GENERIC_TITLE_HINTS):
        return _clean_title(existing)

    if user_msgs:
        return _clean_title(user_msgs[0])

    if product is not None:
        return f"Incident SAV — {product.name}"
    return "Incident SAV — intervention technicien"


__all__ = ["TicketDraft", "TicketSummaryService"]
