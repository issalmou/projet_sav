"""Agent SAV autonome basé sur LangGraph.

Le graphe est une boucle ReAct, avec un garde-fou backend supplémentaire :

        START → agent ─(appels d'outils ?)─┐
                  ▲  ▲                      │ oui
                  │  │                      ▼
                  │  └──────────────────  tools
                  │
                  │ non (réponse finale) ─┬─ séquence conforme ──→ END
                  │                       │
                  └── "gate" (nudge) ◄────┘ séquence incomplète
                  │
                  │ (iterations >= max, tool_calls en attente)
                  ▼
              finalize → END

                  │ (iterations >= max, réponse texte non conforme sur un
                  │  invariant CRITIQUE — search_docs / escalate_to_technician)
                  ▼
              force_invariant → END

- `agent`    : un tour LLM avec outils (`LLMService.run_tools`). Renvoie soit
               du texte final, soit des appels d'outils.
- `tools`    : exécute chaque outil (`app.ai.agent.tools.execute_tool`) avec le
               `AgentContext`, ré-injecte les résultats.
- `gate`     : le backend, pas seulement le prompt, vérifie que l'agent a
               respecté l'enchaînement search_docs → submit_diagnosis →
               record_client_feedback avant de le laisser conclure en texte
               libre ; sinon il injecte une consigne corrective et reboucle.
- `finalize` : force une réponse texte sans outil quand le quota d'itérations
               est atteint alors qu'un appel d'outil restait en attente.
- `force_invariant` : dernier recours quand le LLM ignore les nudges du gate
               jusqu'à épuisement du quota. Ne s'applique qu'aux invariants
               pour lesquels le backend a une action réelle à exécuter à sa
               place (search_docs, escalate_to_technician) — les autres
               (submit_diagnosis, record_client_feedback) exigeraient de
               fabriquer un contenu qui n'existe pas, donc restent non forcés.

La persistance métier (conversation, messages, tickets) reste dans les
services : le graphe ne manipule que la liste de messages du tour courant.
L'état LangGraph est volatil ; la base de données reste la source de vérité.
"""
from __future__ import annotations

import operator
import re
import uuid
from dataclasses import dataclass
from typing import Annotated, Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from app.ai.agent.context import AgentContext
from app.ai.agent.prompts import build_agent_system_prompt, build_diagnostic_recap
from app.ai.agent.tools import TOOL_SPECS, execute_tool
from app.ai.exceptions import LLMError
from app.ai.llm import LLMService
from app.ai.memory import ConversationMemory
from app.ai.rag.retriever import RetrieverService
from app.core.config import settings
from app.core.logger import logger
from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent
from app.models.message import Message
from app.models.product import Product
from app.models.user import User
from app.services.ticket_service import TicketService

# Nombre maximal de tours `agent` (chaque tour peut demander plusieurs outils).
# Un dialogue SAV réel dépasse rarement 2-3 tours d'outils.
MAX_AGENT_ITERATIONS = settings.AGENT_MAX_ITERATIONS

_FINALIZE_NUDGE = (
    "Réponds maintenant directement au client, en français (ou dans sa langue), "
    "en te basant sur les informations déjà recueillies. N'appelle plus d'outil."
)
_GENERIC_FALLBACK_REPLY = (
    "Je n'ai pas pu finaliser ma réponse. Pouvez-vous reformuler ou préciser votre demande ?"
)

# Outils purement informatifs dont la présence dans `ctx.tool_trace` dispense
# de l'exigence search_docs — jamais les outils de ticket : `execute_tool` les
# ajoute au trace même en cas de refus, ce qui permettrait de contourner
# search_docs en tentant (et se faisant refuser) un outil de ticket en premier.
_NON_DIAGNOSTIC_TOOLS = frozenset({"get_warranty", "check_ticket_status"})

_GATE_NUDGES = {
    "record_client_feedback": (
        "Tu n'as pas encore enregistré le retour du client sur les étapes que tu avais proposées "
        "précédemment. Effectue un VRAI appel d'outil record_client_feedback(resolved=true s'il dit "
        "que c'est réglé, false s'il dit que ça persiste) via le mécanisme de function/tool calling "
        "AVANT de rédiger ta réponse — ne l'écris jamais comme du texte, cela ne serait pas exécuté."
    ),
    "search_docs": (
        "Tu n'as pas encore consulté la documentation technique du produit pour cette conversation. "
        "Appelle search_docs avec une requête ciblée sur le symptôme décrit AVANT de répondre."
    ),
    "submit_diagnosis": (
        "Tu as consulté la documentation mais tu n'as pas encore enregistré de diagnostic structuré. "
        "Appelle submit_diagnosis(cause, steps) avec la cause probable et des étapes concrètes et "
        "numérotées AVANT de répondre au client."
    ),
    "escalate_to_technician": (
        "Le seuil de tentatives de diagnostic infructueuses est atteint : tu ne peux plus proposer "
        "de nouveau diagnostic toi-même. Appelle escalate_to_technician(reason) avec une raison "
        "factuelle AVANT de répondre au client."
    ),
}

# Les deux seuls motifs de garde-fou pour lesquels le backend a une action de
# dernier recours réelle (cf. `force_invariant_node`), sans rien inventer.
_FORCEABLE_INVARIANTS = {
    "search_docs": lambda last_user_text: {"query": last_user_text},
    "escalate_to_technician": lambda last_user_text: {"reason": ""},
}


# Certains modèles locaux écrivent parfois `record_client_feedback(...)` comme
# texte au lieu d'un vrai appel d'outil : reconnu seulement sous ce format
# strict, sans eval/exec — une capture regex mappée explicitement sur un booléen.
_PSEUDO_FEEDBACK_CALL_RE = re.compile(
    r"\brecord_client_feedback\s*\(\s*resolved\s*=\s*(true|false)\s*\)", re.IGNORECASE
)


def _parse_pseudo_feedback_call(text: str) -> bool | None:
    """Reconnaît une pseudo-invocation `record_client_feedback(resolved=...)`
    écrite en texte plutôt qu'appelée réellement. Retourne le booléen `resolved`
    si (et seulement si) le texte contient EXACTEMENT ce format ; sinon `None`
    (aucun salvage — le nudge habituel s'applique)."""

    match = _PSEUDO_FEEDBACK_CALL_RE.search(text or "")
    if match is None:
        return None
    return match.group(1).lower() == "true"


def _strip_unanswered_tool_calls(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retire d'un message `assistant` les `tool_calls` restés sans réponse d'outil.

    Un appel d'outil jamais exécuté laissé dans l'historique produit une
    séquence invalide pour les API compatibles OpenAI/Mistral (un message
    `assistant` porteur de `tool_calls` doit être suivi d'un `tool` par id).
    """

    answered_ids = {m.get("tool_call_id") for m in messages if m.get("role") == "tool"}

    cleaned: list[dict[str, Any]] = []
    for message in messages:
        tool_calls = message.get("tool_calls")
        if message.get("role") == "assistant" and tool_calls:
            pending = [tc for tc in tool_calls if tc.get("id") not in answered_ids]
            if pending:
                message = {k: v for k, v in message.items() if k != "tool_calls"}
                if not (message.get("content") or "").strip():
                    continue
        cleaned.append(message)
    return cleaned


class AgentState(TypedDict):
    messages: Annotated[list[dict[str, Any]], operator.add]
    iterations: Annotated[int, operator.add]


def _gate_violation(ctx: AgentContext) -> str | None:
    """Garde-fou B6 : l'agent s'apprête à conclure en texte libre — vérifie que
    l'enchaînement search_docs → submit_diagnosis → record_client_feedback a
    réellement été respecté. Retourne la clé de l'outil manquant (une entrée
    de `_GATE_NUDGES`), ou `None` si rien ne bloque.

    Décision **entièrement déterministe**, basée sur l'état persistant de
    `Conversation` et sur les outils réellement exécutés ce tour
    (`ctx.tool_trace`) — jamais une heuristique sur le texte généré par le LLM.
    """

    conv = ctx.conversation

    # Test sur `ctx.tool_trace` (appelé CE tour), pas sur l'état courant de
    # `awaiting_step_feedback` : un nouveau submit_diagnosis le remet à True
    # pour le tour suivant et redéclencherait sinon cette règle à tort.
    if ctx.turn_started_awaiting_feedback and "record_client_feedback" not in ctx.tool_trace:
        return "record_client_feedback"

    # Un search_docs en erreur compte comme une tentative (sinon boucle
    # infinie tant que le RAG est indisponible).
    if (
        not conv.search_performed
        and "search_docs" not in ctx.tool_trace
        and not (set(ctx.tool_trace) & _NON_DIAGNOSTIC_TOOLS)
    ):
        return "search_docs"

    # Un ticket déjà actif (même créé lors d'un tour antérieur) dispense de
    # relancer un diagnostic : l'escalade est une étape terminale. Sinon,
    # submit_diagnosis est obligatoire avant de répondre, sauf si le seuil
    # d'échecs est atteint — l'escalade devient alors elle-même obligatoire.
    if (
        conv.search_performed
        and not conv.awaiting_step_feedback
        and not conv.problem_resolved
        and ctx.created_ticket_id is None
        and not ctx.has_active_ticket
    ):
        if ctx.escalation_allowed:
            if "escalate_to_technician" not in ctx.tool_trace:
                return "escalate_to_technician"
        elif "submit_diagnosis" not in ctx.tool_trace:
            return "submit_diagnosis"

    return None


@dataclass
class AgentTurnResult:
    """Résultat d'un tour d'agent : texte de réponse + éventuel ticket créé."""

    reply_text: str
    created_ticket_id: UUID | None
    tools_used: list[str]


def _build_graph(llm: LLMService, ctx: AgentContext, user_message: str):
    async def agent_node(state: AgentState) -> dict[str, Any]:
        result = await llm.run_tools(state["messages"], TOOL_SPECS)
        message: dict[str, Any] = {"role": "assistant", "content": result.text or ""}
        if result.tool_calls:
            message["tool_calls"] = [tc.as_message() for tc in result.tool_calls]
        return {"messages": [message], "iterations": 1}

    async def tools_node(state: AgentState) -> dict[str, Any]:
        last = state["messages"][-1]
        outputs: list[dict[str, Any]] = []
        for tc in last.get("tool_calls", []):
            content = await execute_tool(ctx, tc["name"], tc.get("arguments", {}))
            outputs.append(
                {"role": "tool", "tool_call_id": tc["id"], "name": tc["name"], "content": content}
            )
        return {"messages": outputs, "iterations": 0}

    async def gate_node(state: AgentState) -> dict[str, Any]:
        reason = _gate_violation(ctx)

        # Salvage uniquement quand record_client_feedback est réellement requis
        # et que le texte correspond exactement au format pseudo-appel attendu ;
        # le vrai outil est exécuté via `execute_tool`, rien n'est dupliqué ici.
        if reason == "record_client_feedback":
            last_text = state["messages"][-1].get("content") or ""
            resolved = _parse_pseudo_feedback_call(last_text)
            if resolved is not None:
                call_id = f"call_{uuid.uuid4().hex[:12]}"
                output = await execute_tool(ctx, "record_client_feedback", {"resolved": resolved})
                return {
                    "messages": [
                        {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {"id": call_id, "name": "record_client_feedback", "arguments": {"resolved": resolved}}
                            ],
                        },
                        {"role": "tool", "tool_call_id": call_id, "name": "record_client_feedback", "content": output},
                    ],
                    "iterations": 0,
                }

        nudge = _GATE_NUDGES.get(reason, _GATE_NUDGES["search_docs"])
        return {"messages": [{"role": "user", "content": nudge}], "iterations": 0}

    async def force_invariant_node(state: AgentState) -> dict[str, Any]:
        """Dernier recours anti-boucle, distinct de `finalize_node` : exécute le
        vrai outil (jamais un contenu inventé) puis redemande une réponse."""

        reason = _gate_violation(ctx)
        tool_name = reason if reason in _FORCEABLE_INVARIANTS else "search_docs"
        # Le message client réel de ce tour, pas une consigne du gate (elle
        # aussi injectée en role="user", donc indiscernable par simple filtrage).
        arguments = _FORCEABLE_INVARIANTS[tool_name](user_message)
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        output = await execute_tool(ctx, tool_name, arguments)

        messages = _strip_unanswered_tool_calls(state["messages"])
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"id": call_id, "name": tool_name, "arguments": arguments}],
                },
                {"role": "tool", "tool_call_id": call_id, "name": tool_name, "content": output},
                {"role": "user", "content": _FINALIZE_NUDGE},
            ]
        )
        try:
            text = await llm.generate_reply(messages)
        except LLMError:
            logger.warning("Agent force_invariant: LLM en échec, réponse générique", exc_info=True)
            text = _GENERIC_FALLBACK_REPLY
        return {"messages": [{"role": "assistant", "content": text or _GENERIC_FALLBACK_REPLY}], "iterations": 0}

    async def finalize_node(state: AgentState) -> dict[str, Any]:
        # Neutralise les `tool_calls` orphelins du dernier tour (ils ne seront
        # jamais exécutés) et pousse le nudge comme message `user` : une
        # séquence terminée par `system` est refusée par Mistral et fragile
        # ailleurs, alors qu'un dernier message `user` est valide partout.
        messages = _strip_unanswered_tool_calls(state["messages"])
        messages.append({"role": "user", "content": _FINALIZE_NUDGE})
        try:
            text = await llm.generate_reply(messages)
        except LLMError:
            logger.warning("Agent finalize: LLM en échec, réponse générique", exc_info=True)
            text = _GENERIC_FALLBACK_REPLY
        return {"messages": [{"role": "assistant", "content": text or _GENERIC_FALLBACK_REPLY}], "iterations": 0}

    def route(state: AgentState) -> str:
        last = state["messages"][-1]
        if not last.get("tool_calls"):
            if state["iterations"] < MAX_AGENT_ITERATIONS:
                if _gate_violation(ctx) is not None:
                    return "gate"
                return END
            # Quota épuisé, LLM non conforme : force un invariant forçable en
            # dernier recours, sinon accepte le texte tel quel (mieux qu'une
            # boucle sans fin).
            if _gate_violation(ctx) in _FORCEABLE_INVARIANTS:
                return "force_invariant"
            return END
        if state["iterations"] >= MAX_AGENT_ITERATIONS:
            return "finalize"
        return "tools"

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("gate", gate_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("force_invariant", force_invariant_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        route,
        {"tools": "tools", "gate": "gate", "finalize": "finalize", "force_invariant": "force_invariant", END: END},
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("gate", "agent")
    graph.add_edge("finalize", END)
    graph.add_edge("force_invariant", END)
    return graph.compile()


class SavAgent:
    """Point d'entrée de l'agent : un tour = un message client → une réponse."""

    def __init__(self, llm_service: LLMService | None = None, retriever: RetrieverService | None = None) -> None:
        self._llm = llm_service or LLMService()
        self._retriever = retriever or RetrieverService()

    async def run_turn(
        self,
        *,
        session,
        user: User,
        conversation: Conversation,
        history: list[Message],
        user_message: str,
        events: list[ConversationEvent] | None = None,
    ) -> AgentTurnResult:
        """Exécute le graphe pour le message courant et retourne la réponse + le ticket éventuel."""

        events = events or []
        product = await session.get(Product, conversation.product_id)
        ctx = AgentContext(
            session=session,
            user=user,
            conversation=conversation,
            retriever=self._retriever,
            ticket_service=TicketService(session),
            llm_service=self._llm,
        )
        # Calculé une seule fois, avant tout outil de ce tour (cf. AgentContext.has_active_ticket).
        ctx.has_active_ticket = (
            await ctx.ticket_service.get_active_ticket_by_conversation(ctx.conversation_id)
        ) is not None

        system_prompt = build_agent_system_prompt(
            product,
            user.preferred_language,
            awaiting_ticket_confirmation=conversation.pending_ticket_confirmation,
            awaiting_step_feedback=conversation.awaiting_step_feedback,
            escalation_allowed=ctx.escalation_allowed,
        )
        initial_messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        recap = build_diagnostic_recap(conversation, events)
        if recap:
            initial_messages.append({"role": "system", "content": recap})
        initial_messages.extend(ConversationMemory.to_llm_messages(history))
        # `history` inclut déjà le message client courant (persisté avant l'appel).
        if not initial_messages or initial_messages[-1].get("content") != user_message:
            initial_messages.append({"role": "user", "content": user_message})

        compiled = _build_graph(self._llm, ctx, user_message)
        try:
            final_state: AgentState = await compiled.ainvoke(
                {"messages": initial_messages, "iterations": 0}
            )
        except LLMError:
            raise
        except Exception:
            logger.error("Agent run_turn: échec inattendu du graphe", exc_info=True)
            raise

        reply_text = _strip_internal_leak(_extract_final_reply(final_state["messages"]))
        return AgentTurnResult(
            reply_text=reply_text,
            created_ticket_id=ctx.created_ticket_id,
            tools_used=list(ctx.tool_trace),
        )


def _extract_final_reply(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "assistant" and message.get("content") and not message.get("tool_calls"):
            return message["content"].strip()
    return _GENERIC_FALLBACK_REPLY


# Un modèle local faible peut citer/paraphraser le récapitulatif interne
# (`build_diagnostic_recap`) dans sa réponse finale malgré la consigne du
# prompt : détecté par marqueurs textuels distinctifs, remplacé par un
# message générique plutôt qu'un nettoyage qui risquerait de laisser passer une variante.
_INTERNAL_LEAK_MARKERS = (
    "récapitulatif du diagnostic",
    "ne le recopie ni ne le paraphrase",
    "usage interne uniquement",
)


def _strip_internal_leak(reply_text: str) -> str:
    lowered = reply_text.lower()
    if any(marker in lowered for marker in _INTERNAL_LEAK_MARKERS):
        logger.warning("Agent: fuite de contenu interne détectée et bloquée dans la réponse finale")
        return _GENERIC_FALLBACK_REPLY
    return reply_text


__all__ = ["MAX_AGENT_ITERATIONS", "AgentTurnResult", "SavAgent"]
