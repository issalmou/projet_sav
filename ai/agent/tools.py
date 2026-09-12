"""Outils de l'agent SAV — chaque outil est une fonction métier sécurisée.

Le produit, le client et la conversation viennent toujours de `AgentContext`
(jamais d'un argument fourni par le LLM), et les compteurs de diagnostic sont
gérés uniquement par le backend : le LLM ne fait que déclencher les outils.
"""
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.ai.agent.context import AgentContext
from app.ai.agent.ticket_summary import TicketSummaryService
from app.ai.exceptions import EmbeddingError
from app.ai.providers.base import ToolSpec
from app.core.logger import logger
from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent, events_since_last_new_issue
from app.models.message import Message
from app.models.product import Product
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketAutoCreate

_FALLBACK_TICKET_TITLE = "Ticket créé automatiquement par l'agent SAV"
_MAX_STEPS = 8
# Préfixe d'énumération en tête d'étape (« 1. », « 2) », « - ») — retiré pour
# stocker l'étape « nue » (l'affichage renumérote).
_STEP_PREFIX_RE = re.compile(r"^\s*(?:\d+[.)]\s*|[-*•]\s+)")


# --- Utilitaires internes --------------------------------------------------


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "oui", "resolved", "resolu", "résolu"}


def _clean_steps(steps: object) -> list[str]:
    if isinstance(steps, str):
        raw = [s for s in steps.replace("\r", "\n").split("\n")]
    elif isinstance(steps, (list, tuple)):
        raw = list(steps)
    else:
        raw = []
    out: list[str] = []
    for item in raw:
        text = _STEP_PREFIX_RE.sub("", str(item).strip()).strip()
        if text:
            out.append(text)
    return out[:_MAX_STEPS]


def _log_event(ctx: AgentContext, event_type: str, payload: dict) -> None:
    ctx.session.add(
        ConversationEvent(conversation_id=ctx.conversation_id, event_type=event_type, payload=payload)
    )


async def _load_history(ctx: AgentContext) -> list[Message]:
    result = await ctx.session.execute(
        select(Message).where(Message.conversation_id == ctx.conversation_id).order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def _load_events(ctx: AgentContext) -> list[ConversationEvent]:
    result = await ctx.session.execute(
        select(ConversationEvent)
        .where(ConversationEvent.conversation_id == ctx.conversation_id)
        .order_by(ConversationEvent.created_at)
    )
    return list(result.scalars().all())


# --- Implémentations ------------------------------------------------------


async def search_docs(ctx: AgentContext, query: str) -> str:
    """Recherche documentaire filtrée sur le produit de la conversation."""

    query = (query or "").strip()
    if not query:
        return "Requête vide : précise ce que tu cherches."

    try:
        chunks = await ctx.retriever.retrieve(query, product_id=ctx.product_id)
    except EmbeddingError:
        logger.warning("Agent tool search_docs: RAG indisponible (embeddings)", exc_info=True)
        return "La recherche documentaire est momentanément indisponible."
    except Exception:
        logger.error("Agent tool search_docs: échec inattendu", exc_info=True)
        return "La recherche documentaire a échoué."

    titles = sorted({c.title for c in chunks})
    ctx.conversation.search_performed = True
    ctx.session.add(ctx.conversation)
    _log_event(ctx, "search", {"query": query, "count": len(chunks), "titles": titles})
    await ctx.session.commit()

    if not chunks:
        return "Aucun document pertinent trouvé dans la base de connaissances pour ce produit."

    return "\n\n".join(f"[{c.title}] {c.text}" for c in chunks)


async def get_warranty(ctx: AgentContext) -> str:
    """Durée de garantie standard du produit de la conversation."""

    product = await ctx.session.get(Product, ctx.product_id)
    if product is None:  # théoriquement impossible (FK), sécurité
        return "Produit introuvable."
    if product.warranty_months is None:
        return f"Aucune durée de garantie n'est renseignée pour le produit « {product.name} »."
    return (
        f"Le produit « {product.name} » (référence {product.reference}) bénéficie d'une "
        f"garantie standard de {product.warranty_months} mois à compter de l'achat."
    )


async def check_ticket_status(ctx: AgentContext) -> str:
    """Y a-t-il un ticket de support ouvert pour cette conversation ?"""

    ticket = await ctx.ticket_service.get_active_ticket_by_conversation(ctx.conversation_id)
    if ticket is None:
        return "Aucun ticket de support n'est actuellement ouvert pour cette conversation."
    assigned = "assigné à un technicien" if ticket.assigned_technician_id else "pas encore assigné"
    return f"Un ticket de support est ouvert (statut : {ticket.status}, {assigned})."


async def submit_diagnosis(ctx: AgentContext, cause: str, steps: list[str]) -> str:
    """Enregistre une hypothèse de cause + des étapes de résolution à faire tester au client."""

    if not ctx.conversation.search_performed:
        return (
            "Tu dois d'abord consulter la documentation du produit (search_docs) avant de "
            "proposer un diagnostic. Fais la recherche, puis rappelle submit_diagnosis."
        )

    if ctx.escalation_allowed:
        # Refusé ici, pas seulement en fin de tour : sinon l'agent pourrait
        # esquiver l'escalade indéfiniment en renouvelant son diagnostic.
        return (
            "Le seuil de tentatives de diagnostic infructueuses est atteint : tu ne peux plus "
            "proposer de nouveau diagnostic toi-même. Appelle escalate_to_technician(reason) "
            "pour transmettre le dossier à un technicien."
        )

    clean_steps = _clean_steps(steps)
    if not clean_steps:
        return "Fournis au moins une étape de vérification concrète et ordonnée pour le client."

    cause = (cause or "").strip()
    if not cause:
        # Une liste d'étapes sans hypothèse n'est pas un diagnostic.
        return "Indique la cause probable (ou une hypothèse) avant d'enregistrer le diagnostic."

    ctx.conversation.awaiting_step_feedback = True
    ctx.conversation.problem_resolved = False
    ctx.session.add(ctx.conversation)
    _log_event(ctx, "diagnosis", {"cause": cause, "steps": clean_steps})
    await ctx.session.commit()

    return (
        "Diagnostic enregistré. Présente maintenant au client, en clair : la cause probable "
        "(ou les hypothèses), puis les étapes NUMÉROTÉES à effectuer, et termine en lui "
        "demandant de les tester et de te dire si le problème persiste."
    )


async def record_client_feedback(ctx: AgentContext, resolved: bool) -> str:
    """Enregistre le retour du client après les étapes proposées (résolu ou non)."""

    if resolved:
        ctx.conversation.problem_resolved = True
        ctx.conversation.awaiting_step_feedback = False
        ctx.session.add(ctx.conversation)
        _log_event(ctx, "feedback", {"resolved": True})
        await ctx.session.commit()
        return (
            "Le client confirme que le problème est résolu. Conclus la conversation "
            "poliment. NE crée PAS de ticket."
        )

    # Verrou DB (FOR UPDATE) avant lecture+incrément : sans lui, deux requêtes
    # concurrentes pourraient lire la même valeur et perdre un incrément.
    await ctx.session.refresh(ctx.conversation, with_for_update=True)

    if ctx.conversation.awaiting_step_feedback:
        ctx.conversation.diagnostic_attempts += 1
    ctx.conversation.awaiting_step_feedback = False
    attempt_no = ctx.conversation.diagnostic_attempts
    ctx.session.add(ctx.conversation)
    _log_event(ctx, "feedback", {"resolved": False, "attempt": attempt_no})
    await ctx.session.commit()

    if ctx.escalation_allowed:
        return (
            f"Tentative n°{attempt_no} infructueuse. Le seuil de diagnostic "
            f"({ctx.escalation_threshold}) est atteint : tu ne peux plus proposer de nouveau "
            "diagnostic. Escalade via escalate_to_technician(reason)."
        )
    return (
        f"Tentative n°{attempt_no} infructueuse (seuil d'escalade : {ctx.escalation_threshold}). "
        "Relance le diagnostic : nouvelle recherche documentaire si utile, nouvelle hypothèse, "
        "nouvelles étapes via submit_diagnosis. N'escalade pas encore."
    )


async def start_new_issue(ctx: AgentContext, summary: str) -> str:
    """Réarme le diagnostic pour un nouveau problème dans la même conversation.

    Refusé tant que l'incident courant n'est pas réellement conclu (résolu,
    ou ticketé puis fermé), pour ne pas servir à esquiver le diagnostic en
    cours. Ne supprime jamais l'historique : pose un marqueur `new_issue`
    (cf. `events_since_last_new_issue`) et réinitialise l'état du diagnostic.
    """

    conv = ctx.conversation

    if not conv.search_performed:
        return "Rien à réinitialiser : aucun diagnostic n'a encore été entamé dans cette conversation."

    # Requête fraîche (pas `ctx.has_active_ticket`, figé en début de tour) :
    # un ticket a pu être créé plus tôt dans ce même tour.
    if await ctx.ticket_service.get_active_ticket_by_conversation(ctx.conversation_id) is not None:
        return (
            "Un ticket est actif pour cette conversation : impossible de démarrer un nouveau "
            "sujet tant qu'il n'est pas fermé. Utilise check_ticket_status si besoin de faire un point."
        )

    if not conv.problem_resolved:
        # Diagnostic encore ouvert, ou ticket déjà fermé pour cet incident :
        # les deux états sont indiscernables sur `Conversation` seule, d'où
        # le recours au journal du cycle en cours.
        current_cycle_events = events_since_last_new_issue(await _load_events(ctx))
        had_ticket_this_cycle = any(e.event_type == "ticket" for e in current_cycle_events)
        if not had_ticket_this_cycle:
            return (
                "Le diagnostic en cours n'est pas terminé : termine-le (nouvelle étape, retour "
                "client, ou escalade) avant de démarrer un nouveau sujet."
            )

    conv.search_performed = False
    conv.awaiting_step_feedback = False
    conv.problem_resolved = False
    conv.diagnostic_attempts = 0
    ctx.session.add(conv)
    _log_event(ctx, "new_issue", {"summary": (summary or "").strip()})
    await ctx.session.commit()

    return (
        "Nouveau sujet enregistré, distinct du précédent. Traite-le comme un tout nouveau "
        "diagnostic : consulte la documentation (search_docs) puis établis un diagnostic "
        "structuré (submit_diagnosis) pour CE problème, en repartant de zéro."
    )


async def request_ticket_creation(ctx: AgentContext, problem_summary: str) -> str:
    """Chemin « demande explicite » : enregistre une PROPOSITION de ticket (ne crée rien)."""

    existing = await ctx.ticket_service.get_active_ticket_by_conversation(ctx.conversation_id)
    if existing is not None:
        return (
            f"Un ticket est déjà ouvert pour cette conversation (statut : {existing.status}). "
            "Inutile d'en proposer un nouveau."
        )

    if not ctx.conversation.search_performed:
        return (
            "Mène d'abord un vrai diagnostic (search_docs, puis submit_diagnosis avec des "
            "étapes concrètes) avant de proposer un ticket."
        )

    ctx.conversation.pending_ticket_confirmation = True
    ctx.session.add(ctx.conversation)
    await ctx.session.commit()
    ctx.proposed_summary = (problem_summary or "").strip() or None
    ctx.ticket_proposed_this_run = True  # empêche une confirmation dans le même tour
    return (
        "Proposition de ticket enregistrée. Demande MAINTENANT au client de confirmer "
        "explicitement (oui / non). Ne crée rien tant qu'il n'a pas répondu — sa confirmation "
        "viendra dans son PROCHAIN message."
    )


async def decline_ticket_proposal(ctx: AgentContext) -> str:
    """Chemin « demande explicite » : acte un refus clair du client à la proposition de ticket.

    Sans cet outil, une confirmation tardive et hors contexte pourrait plus
    tard créer un ticket pour une proposition déjà caduque.
    """

    if not ctx.conversation.pending_ticket_confirmation:
        return "Aucune proposition de ticket n'est en attente : rien à faire."

    ctx.conversation.pending_ticket_confirmation = False
    ctx.session.add(ctx.conversation)
    await ctx.session.commit()
    return "Refus enregistré, la proposition de ticket est close. Ne crée aucun ticket. Continue d'aider le client normalement."


async def create_ticket(ctx: AgentContext, description: str) -> str:
    """Chemin « demande explicite » : crée le ticket APRÈS confirmation du client."""

    if ctx.ticket_proposed_this_run:
        return (
            "La proposition de ticket vient d'être faite dans cet échange : tu ne peux pas la "
            "confirmer toi-même. Attends la réponse explicite du client à son prochain message."
        )

    if not ctx.conversation.pending_ticket_confirmation:
        return (
            "Impossible : aucune proposition de ticket n'est en attente de confirmation. "
            "Appelle d'abord request_ticket_creation, puis attends la confirmation du client."
        )

    return await _create_ticket_from_context(
        ctx, escalation_reason=None, llm_hint=(description or "").strip() or None, escalated=False
    )


async def escalate_to_technician(ctx: AgentContext, reason: str) -> str:
    """Chemin « échec du diagnostic » : crée automatiquement un ticket (CDC §17).

    Autorisé UNIQUEMENT si le diagnostic a atteint le seuil d'échecs défini
    côté backend. Aucune confirmation client supplémentaire n'est requise.
    """

    reason = (reason or "").strip()

    if not ctx.escalation_allowed:
        return (
            f"Escalade refusée : seulement {ctx.conversation.diagnostic_attempts} tentative(s) "
            f"de diagnostic infructueuse(s) sur {ctx.escalation_threshold} requises. Poursuis le "
            "diagnostic (nouvelle recherche, nouvelles étapes)."
        )

    return await _create_ticket_from_context(
        ctx, escalation_reason=reason or None, llm_hint=None, escalated=True
    )


def _ticket_already_open_message(ticket: Ticket) -> str:
    return (
        f"Un ticket est déjà ouvert pour cette conversation (statut : {ticket.status}). "
        "Aucun doublon n'est créé. Informe le client que sa demande est déjà prise en charge."
    )


async def _create_ticket_from_context(
    ctx: AgentContext, *, escalation_reason: str | None, llm_hint: str | None, escalated: bool
) -> str:
    """Cœur commun de création de ticket : anti-doublon + description générée + assignation.

    La vérification « pas de ticket actif » suivie de la création n'est pas
    atomique à elle seule : la garantie réelle est l'index unique partiel
    PostgreSQL `ux_tickets_active_per_conversation`, qui fait échouer en
    `IntegrityError` la transaction perdante d'une course, rattrapée plus bas.
    """

    existing = await ctx.ticket_service.get_active_ticket_by_conversation(ctx.conversation_id)
    if existing is not None:
        ctx.conversation.pending_ticket_confirmation = False
        ctx.session.add(ctx.conversation)
        await ctx.session.commit()
        return _ticket_already_open_message(existing)

    history = await _load_history(ctx)
    events = await _load_events(ctx)
    product = await ctx.session.get(Product, ctx.product_id)

    # Le ticket ne décrit que le cycle de diagnostic en cours, jamais un
    # incident précédent déjà clos (l'historique complet reste consultable).
    scoped_events = events_since_last_new_issue(events)
    if len(scoped_events) != len(events):
        boundary_at = events[len(events) - len(scoped_events) - 1].created_at
        history = [m for m in history if m.created_at >= boundary_at]
    events = scoped_events

    draft = await TicketSummaryService(ctx.llm_service).build(
        conversation=ctx.conversation,
        product=product,
        history=history,
        events=events,
        escalation_reason=escalation_reason or llm_hint,
    )

    data = TicketAutoCreate(
        title=draft.title or ctx.conversation.title or _FALLBACK_TICKET_TITLE,
        description=draft.description,
        product_id=ctx.product_id,  # source de vérité : la conversation
    )
    try:
        ticket = await ctx.ticket_service.create_ticket(ctx.user, data, conversation_id=ctx.conversation_id)
    except IntegrityError:
        # Course perdue face à la contrainte DB : le rollback expire toutes
        # les instances de la session, `ctx.user` est donc aussi rechargé.
        await ctx.session.rollback()
        ctx.conversation = await ctx.session.get(Conversation, ctx.conversation_id)
        ctx.user = await ctx.session.get(User, ctx.client_id)
        concurrent = await ctx.ticket_service.get_active_ticket_by_conversation(ctx.conversation_id)
        ctx.conversation.pending_ticket_confirmation = False
        ctx.session.add(ctx.conversation)
        await ctx.session.commit()
        if concurrent is None:  # défensif : cas quasi impossible (fermé entre-temps)
            return "Un ticket vient d'être créé pour cette conversation par une autre requête. Aucun doublon n'est créé."
        return _ticket_already_open_message(concurrent)

    ctx.conversation.pending_ticket_confirmation = False
    if escalated:
        ctx.conversation.awaiting_step_feedback = False
        ctx.escalated_this_run = True
        _log_event(ctx, "escalation", {"reason": escalation_reason or "", "attempts": ctx.conversation.diagnostic_attempts})
    _log_event(
        ctx,
        "ticket",
        {"ticket_id": str(ticket.id), "assigned": ticket.assigned_technician_id is not None, "auto": escalated},
    )
    ctx.session.add(ctx.conversation)
    await ctx.session.commit()
    ctx.created_ticket_id = ticket.id

    tech = (
        "et transmis à un technicien"
        if ticket.assigned_technician_id
        else "(aucun technicien disponible pour le moment — le staff l'assignera)"
    )
    return f"Ticket de support créé {tech}. Informe le client que sa demande est prise en charge."


# --- Registre + exécution -------------------------------------------------


_IMPLS = {
    "search_docs": search_docs,
    "get_warranty": get_warranty,
    "check_ticket_status": check_ticket_status,
    "submit_diagnosis": submit_diagnosis,
    "record_client_feedback": record_client_feedback,
    "start_new_issue": start_new_issue,
    "request_ticket_creation": request_ticket_creation,
    "create_ticket": create_ticket,
    "decline_ticket_proposal": decline_ticket_proposal,
    "escalate_to_technician": escalate_to_technician,
}

TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="search_docs",
        description=(
            "Recherche dans la base de connaissances SAV du produit concerné (manuels, FAQ, "
            "procédures). À utiliser AVANT tout diagnostic ou toute réponse technique."
        ),
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "La question ou les mots-clés à rechercher."}},
            "required": ["query"],
        },
    ),
    ToolSpec(
        name="get_warranty",
        description="Retourne la durée de garantie standard du produit concerné par la conversation.",
        parameters={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="check_ticket_status",
        description="Indique s'il existe déjà un ticket de support ouvert pour cette conversation, et son statut.",
        parameters={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="submit_diagnosis",
        description=(
            "À appeler quand tu es prêt à proposer une résolution : enregistre la cause probable "
            "et les étapes concrètes que le client devra tester. Nécessite d'avoir déjà appelé "
            "search_docs. Après cet appel, présente au client la cause et les étapes numérotées, "
            "puis demande-lui si le problème persiste."
        ),
        parameters={
            "type": "object",
            "properties": {
                "cause": {
                    "type": "string",
                    "description": "Cause probable ou hypothèses, formulées à partir de la documentation.",
                },
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Étapes de vérification/résolution concrètes et ordonnées (2 à 6 en général).",
                },
            },
            "required": ["cause", "steps"],
        },
    ),
    ToolSpec(
        name="record_client_feedback",
        description=(
            "À appeler au tour suivant, quand le client a répondu après avoir testé les étapes : "
            "indique si le problème est résolu (resolved=true) ou s'il persiste (resolved=false). "
            "Le backend met à jour le compteur de tentatives et t'indique la suite."
        ),
        parameters={
            "type": "object",
            "properties": {
                "resolved": {
                    "type": "boolean",
                    "description": "true si le client dit que le problème est résolu, false s'il persiste.",
                }
            },
            "required": ["resolved"],
        },
    ),
    ToolSpec(
        name="start_new_issue",
        description=(
            "À appeler UNIQUEMENT quand le client décrit, dans cette même conversation, un "
            "problème clairement DIFFÉRENT du précédent, ET que le précédent est déjà conclu "
            "(résolu, ou ticket créé puis fermé). Réarme le diagnostic pour ce nouveau problème "
            "(nouvelle recherche documentaire et nouveau diagnostic requis). Le backend refuse "
            "cet appel si le diagnostic précédent n'est pas réellement terminé."
        ),
        parameters={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Résumé court du nouveau problème décrit par le client.",
                }
            },
            "required": ["summary"],
        },
    ),
    ToolSpec(
        name="request_ticket_creation",
        description=(
            "Chemin « le client demande explicitement un ticket / un technicien ». Enregistre une "
            "proposition (ne crée rien). Il faut ensuite la confirmation explicite du client, qui "
            "viendra dans son message suivant."
        ),
        parameters={
            "type": "object",
            "properties": {
                "problem_summary": {
                    "type": "string",
                    "description": "Résumé court du problème non résolu (pour le suivi interne).",
                }
            },
            "required": ["problem_summary"],
        },
    ),
    ToolSpec(
        name="create_ticket",
        description=(
            "Crée le ticket APRÈS que le client a confirmé (chemin request_ticket_creation). "
            "À n'appeler qu'au tour où le client répond « oui » à la proposition faite au tour "
            "précédent."
        ),
        parameters={
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": (
                        "Indice de synthèse technique pour le technicien (symptômes, vérifications "
                        "faites et résultats). La description finale est mise en forme par le backend."
                    ),
                }
            },
            "required": ["description"],
        },
    ),
    ToolSpec(
        name="decline_ticket_proposal",
        description=(
            "À appeler quand le client REFUSE CLAIREMENT la proposition de ticket faite au tour "
            "précédent (ex. « non merci », « pas besoin »). Clôt la proposition sans créer de "
            "ticket. N'appelle PAS cet outil si la réponse du client est ambiguë — dans ce cas, "
            "redemande simplement une confirmation par oui ou non, sans appeler d'outil."
        ),
        parameters={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="escalate_to_technician",
        description=(
            "Chemin « le diagnostic a échoué ». Crée automatiquement un ticket et le transmet à "
            "un technicien, SANS confirmation supplémentaire. Autorisé uniquement une fois le "
            "seuil de tentatives infructueuses atteint (le backend vérifie)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Raison de l'escalade : pourquoi le problème n'a pas pu être résolu à distance.",
                }
            },
            "required": ["reason"],
        },
    ),
]


async def execute_tool(ctx: AgentContext, name: str, arguments: dict) -> str:
    """Exécute un outil demandé par le LLM. Toute erreur est renvoyée comme texte à l'agent."""

    impl = _IMPLS.get(name)
    if impl is None:
        return f"Outil inconnu : {name}."

    arguments = arguments or {}
    try:
        if name in ("get_warranty", "check_ticket_status", "decline_ticket_proposal"):
            output = await impl(ctx)
        elif name == "search_docs":
            output = await impl(ctx, str(arguments.get("query", "")))
        elif name == "submit_diagnosis":
            output = await impl(ctx, str(arguments.get("cause", "")), arguments.get("steps", []))
        elif name == "record_client_feedback":
            output = await impl(ctx, _as_bool(arguments.get("resolved")))
        elif name == "start_new_issue":
            output = await impl(ctx, str(arguments.get("summary", "")))
        elif name == "request_ticket_creation":
            output = await impl(ctx, str(arguments.get("problem_summary", "")))
        elif name == "create_ticket":
            output = await impl(ctx, str(arguments.get("description", "")))
        elif name == "escalate_to_technician":
            output = await impl(ctx, str(arguments.get("reason", "")))
        else:  # pragma: no cover - défensif
            output = await impl(ctx)
    except Exception:
        logger.error("Agent tool %s: échec inattendu", name, exc_info=True)
        # Le rollback expire les instances ORM : on les recharge depuis les
        # UUID capturés au démarrage du tour pour que la suite reste saine.
        try:
            await ctx.session.rollback()
            ctx.conversation = await ctx.session.get(Conversation, ctx.conversation_id)
            ctx.user = await ctx.session.get(User, ctx.client_id)
        except Exception:
            logger.error("Agent tool %s: rollback/rechargement échoué", name, exc_info=True)
        output = f"L'action « {name} » a échoué pour une raison technique."

    ctx.tool_trace.append(name)
    return output


__all__ = ["TOOL_SPECS", "execute_tool"]
