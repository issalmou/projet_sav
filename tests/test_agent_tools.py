"""Tests unitaires des outils de l'agent SAV.

Le contexte (produit / client / conversation) est la source de vérité : un
argument d'identité fourni par le LLM est ignoré. Base PostgreSQL réelle
(tickets, conversations, événements). Le LLM de génération de description est
scripté (aucun appel réseau).
"""
import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.ai.agent.context import AgentContext
from app.ai.agent.tools import TOOL_SPECS, execute_tool
from app.ai.llm import LLMService
from app.database.session import AsyncSessionLocal
from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.client_product import ClientProductItem
from app.schemas.user import UserCreate
from app.services.client_product_service import ClientProductService
from app.services.ticket_service import TicketService
from app.services.user_service import UserService
from conftest import ScriptedLLMProvider, StubRetriever, unique_email

_LLM_TICKET_REPLY = "TITRE: Incident imprimante X100\n\nProblème\n--------\nPanne rapportée par le client"


def _llm() -> LLMService:
    return LLMService(provider=ScriptedLLMProvider([], text_reply=_LLM_TICKET_REPLY))


@pytest_asyncio.fixture
async def tool_ctx(db_session, role_ids, product):
    us = UserService(db_session)
    client = await us.create_user(
        UserCreate(email=unique_email("tool.client"), password="ValidPass1", role_id=role_ids["client"])
    )
    await ClientProductService(db_session).assign_products(
        client.id, [ClientProductItem(product_id=product.id, qte=1)]
    )
    pre = (
        await db_session.execute(
            select(User).join(Role, Role.id == User.role_id).where(Role.name == "technicien", User.is_active.is_(True))
        )
    ).scalars().all()
    for u in pre:
        u.is_active = False
    tech = User(email=unique_email("tool.tech"), hashed_password="x", role_id=role_ids["technicien"], is_active=True)
    db_session.add(tech)
    await db_session.commit()
    await db_session.refresh(client)

    conv = Conversation(user_id=client.id, product_id=product.id, title="t")
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)

    retriever = StubRetriever([])
    ctx = AgentContext(
        session=db_session,
        user=client,
        conversation=conv,
        retriever=retriever,
        ticket_service=TicketService(db_session),
        llm_service=_llm(),
    )
    # UUID nus, capturés AVANT le yield : un test peut déclencher un vrai
    # rollback DB (ex. I3, contrainte d'unicité violée) qui expire les
    # instances ORM `client`/`tech` sans les recharger (seuls `ctx.user` /
    # `ctx.conversation` le sont, cf. B4) — le teardown ne doit alors jamais
    # ré-accéder à `.id` sur un objet potentiellement expiré.
    client_id, conv_id, tech_id = client.id, conv.id, tech.id
    pre_ids = [u.id for u in pre]
    yield ctx, product, tech, retriever

    await db_session.execute(delete(Ticket).where(Ticket.client_id == client_id))
    await db_session.execute(delete(ConversationEvent).where(ConversationEvent.conversation_id == conv_id))
    await db_session.execute(delete(Conversation).where(Conversation.id == conv_id))
    await db_session.execute(delete(User).where(User.id.in_([client_id, tech_id])))
    await db_session.commit()
    for u_id in pre_ids:
        row = await db_session.get(User, u_id)
        if row is not None:
            row.is_active = True
    if pre:
        await db_session.commit()


async def _events(ctx) -> list[ConversationEvent]:
    result = await ctx.session.execute(
        select(ConversationEvent)
        .where(ConversationEvent.conversation_id == ctx.conversation_id)
        .order_by(ConversationEvent.created_at)
    )
    return list(result.scalars().all())


# --- Sécurité des identités ------------------------------------------


def test_tool_specs_never_expose_identity_parameters():
    """Aucun outil n'accepte product_id / client_id / conversation_id / technician_id."""

    forbidden = {"product_id", "client_id", "conversation_id", "technician_id", "assigned_technician_id", "user_id"}
    for spec in TOOL_SPECS:
        assert not (set(spec.parameters.get("properties", {})) & forbidden), spec.name

    names = {s.name for s in TOOL_SPECS}
    assert {"submit_diagnosis", "record_client_feedback", "escalate_to_technician"} <= names


@pytest.mark.asyncio
async def test_search_docs_uses_conversation_product_and_ignores_extra_args(tool_ctx):
    ctx, product, _, retriever = tool_ctx

    await execute_tool(ctx, "search_docs", {"query": "erreur", "product_id": str(uuid.uuid4())})

    assert retriever.received_product_ids == [product.id]


@pytest.mark.asyncio
async def test_escalate_uses_context_identity_not_llm_args(tool_ctx):
    """Même si le LLM injecte des identités, le ticket reste lié à la conversation."""

    ctx, product, tech, _ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.diagnostic_attempts = 2
    await ctx.session.commit()

    await execute_tool(
        ctx,
        "escalate_to_technician",
        {"reason": "bloqué", "client_id": str(uuid.uuid4()), "product_id": str(uuid.uuid4()), "technician_id": str(uuid.uuid4())},
    )

    ticket = await ctx.session.get(Ticket, ctx.created_ticket_id)
    assert ticket.client_id == ctx.conversation.user_id
    assert ticket.product_id == product.id
    assert ticket.conversation_id == ctx.conversation.id
    assert ticket.assigned_technician_id == tech.id


# --- search_docs -> état + journal -----------------------------------


@pytest.mark.asyncio
async def test_search_docs_marks_search_performed_and_logs_event(tool_ctx):
    ctx, product, _, _ = tool_ctx

    await execute_tool(ctx, "search_docs", {"query": "voyant rouge"})

    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.search_performed is True
    events = await _events(ctx)
    assert [e.event_type for e in events] == ["search"]
    assert events[0].payload["query"] == "voyant rouge"


# --- submit_diagnosis ----------------------------------------------


@pytest.mark.asyncio
async def test_submit_diagnosis_refused_without_search(tool_ctx):
    ctx, *_ = tool_ctx
    out = await execute_tool(ctx, "submit_diagnosis", {"cause": "x", "steps": ["a"]})
    assert "search_docs" in out
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.awaiting_step_feedback is False


@pytest.mark.asyncio
async def test_submit_diagnosis_requires_steps(tool_ctx):
    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    await ctx.session.commit()
    out = await execute_tool(ctx, "submit_diagnosis", {"cause": "x", "steps": []})
    assert "étape" in out.lower()


@pytest.mark.asyncio
async def test_submit_diagnosis_requires_non_empty_cause(tool_ctx):
    """M1 : une cause vide (ou blanche) est refusée — un diagnostic sans
    hypothèse n'est qu'une liste d'étapes, pas un vrai diagnostic."""

    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    await ctx.session.commit()

    out = await execute_tool(ctx, "submit_diagnosis", {"cause": "   ", "steps": ["Vérifier le câble"]})

    assert "cause" in out.lower()
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.awaiting_step_feedback is False
    events = await _events(ctx)
    assert events == []  # rien loggé : le refus intervient avant tout enregistrement


@pytest.mark.asyncio
async def test_submit_diagnosis_refused_once_escalation_threshold_reached(tool_ctx):
    """M2 : une fois le seuil d'échecs atteint, submit_diagnosis se refuse
    lui-même — l'escalade devient la seule issue possible, garantie
    indépendamment du garde-fou de fin de tour (qui ne bloque jamais un
    appel d'outil, seulement une conclusion en texte libre)."""

    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.diagnostic_attempts = 2  # == seuil par défaut
    await ctx.session.commit()

    out = await execute_tool(ctx, "submit_diagnosis", {"cause": "Nouvelle piste", "steps": ["Vérifier X"]})

    assert "escalate_to_technician" in out
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.awaiting_step_feedback is False
    events = [e for e in await _events(ctx) if e.event_type == "diagnosis"]
    assert events == []  # rien enregistré : le refus intervient avant tout log


@pytest.mark.asyncio
async def test_submit_diagnosis_sets_awaiting_and_logs(tool_ctx):
    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    await ctx.session.commit()

    await execute_tool(
        ctx, "submit_diagnosis", {"cause": "Capteur papier", "steps": ["1. Ouvrir le capot", "2. Nettoyer"]}
    )

    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.awaiting_step_feedback is True
    diag = [e for e in await _events(ctx) if e.event_type == "diagnosis"][0]
    assert diag.payload["cause"] == "Capteur papier"
    assert diag.payload["steps"] == ["Ouvrir le capot", "Nettoyer"]  # numérotation nettoyée


# --- record_client_feedback --------------------------------------


@pytest.mark.asyncio
async def test_feedback_resolved_sets_flag_no_counter(tool_ctx):
    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.awaiting_step_feedback = True
    await ctx.session.commit()

    out = await execute_tool(ctx, "record_client_feedback", {"resolved": True})

    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.problem_resolved is True
    assert ctx.conversation.awaiting_step_feedback is False
    assert ctx.conversation.diagnostic_attempts == 0
    assert "ne crée" in out.lower()


@pytest.mark.asyncio
async def test_feedback_unresolved_increments_only_when_awaiting(tool_ctx):
    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.awaiting_step_feedback = True
    await ctx.session.commit()

    await execute_tool(ctx, "record_client_feedback", {"resolved": False})
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.diagnostic_attempts == 1
    assert ctx.conversation.awaiting_step_feedback is False

    # 2e appel sans nouvelles étapes proposées -> pas de double comptage
    await execute_tool(ctx, "record_client_feedback", {"resolved": False})
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.diagnostic_attempts == 1


@pytest.mark.asyncio
async def test_feedback_string_resolved_is_coerced(tool_ctx):
    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.awaiting_step_feedback = True
    await ctx.session.commit()

    await execute_tool(ctx, "record_client_feedback", {"resolved": "true"})
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.problem_resolved is True


# --- escalate_to_technician -------------------------------------


@pytest.mark.asyncio
async def test_escalate_refused_below_threshold(tool_ctx):
    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.diagnostic_attempts = 1
    await ctx.session.commit()

    out = await execute_tool(ctx, "escalate_to_technician", {"reason": "bloqué"})

    assert "refus" in out.lower()
    assert ctx.created_ticket_id is None
    tickets = (await ctx.session.execute(select(Ticket).where(Ticket.conversation_id == ctx.conversation.id))).scalars().all()
    assert tickets == []


@pytest.mark.asyncio
async def test_escalate_creates_ticket_with_generated_description(tool_ctx):
    ctx, product, tech, _ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.diagnostic_attempts = 2
    ctx.session.add(ConversationEvent(conversation_id=ctx.conversation.id, event_type="search", payload={"query": "démarrage", "titles": ["Guide"]}))
    ctx.session.add(ConversationEvent(conversation_id=ctx.conversation.id, event_type="diagnosis", payload={"cause": "Alim", "steps": ["Vérifier câble"]}))
    ctx.session.add(ConversationEvent(conversation_id=ctx.conversation.id, event_type="feedback", payload={"resolved": False, "attempt": 1}))
    ctx.session.add(ConversationEvent(conversation_id=ctx.conversation.id, event_type="feedback", payload={"resolved": False, "attempt": 2}))
    await ctx.session.commit()

    out = await execute_tool(ctx, "escalate_to_technician", {"reason": "Alimentation HS après 2 séries de vérifications"})

    assert ctx.created_ticket_id is not None
    ticket = await ctx.session.get(Ticket, ctx.created_ticket_id)
    assert ticket.product_id == product.id
    assert ticket.client_id == ctx.conversation.user_id
    assert ticket.conversation_id == ctx.conversation.id
    assert ticket.assigned_technician_id == tech.id
    # description mise en forme par le backend (pas le texte brut du LLM args)
    assert "Incident imprimante X100" in ticket.title
    assert "Problème" in ticket.description
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.pending_ticket_confirmation is False
    types_ = {e.event_type for e in await _events(ctx)}
    assert {"escalation", "ticket"} <= types_
    assert "prise en charge" in out


@pytest.mark.asyncio
async def test_start_new_issue_refused_right_after_escalation_in_same_run(tool_ctx):
    """Audit de stabilisation : start_new_issue doit détecter un ticket créé
    PLUS TÔT DANS CE MÊME RUN (ex. juste après escalate_to_technician) —
    `ctx.has_active_ticket`, figé au début du tour, ne suffirait pas ici :
    l'outil doit interroger la base fraîchement (même défaut corrigé que
    request_ticket_creation / _create_ticket_from_context)."""

    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.diagnostic_attempts = 2
    # simule le fait que ctx.has_active_ticket a été figé à False au début
    # du tour (aucun ticket n'existait alors) — le bug corrigé est que
    # start_new_issue lui faisait encore confiance après coup.
    ctx.has_active_ticket = False
    await ctx.session.commit()

    escalate_out = await execute_tool(ctx, "escalate_to_technician", {"reason": "panne"})
    assert "prise en charge" in escalate_out
    assert ctx.created_ticket_id is not None

    out = await execute_tool(ctx, "start_new_issue", {"summary": "autre problème"})

    assert "ticket est actif" in out.lower()
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.search_performed is True  # pas réinitialisé : refus confirmé
    assert ctx.conversation.diagnostic_attempts == 2


@pytest.mark.asyncio
async def test_escalate_description_falls_back_when_llm_fails(tool_ctx):
    from app.ai.exceptions import LLMRequestError

    class _BoomProvider(ScriptedLLMProvider):
        async def agenerate(self, messages, **kwargs):
            raise LLMRequestError("provider down")

    ctx, product, tech, _ = tool_ctx
    ctx.llm_service = LLMService(provider=_BoomProvider([]))
    ctx.conversation.search_performed = True
    ctx.conversation.diagnostic_attempts = 2
    ctx.session.add(ConversationEvent(conversation_id=ctx.conversation.id, event_type="diagnosis", payload={"cause": "Alim", "steps": ["Vérifier câble secteur"]}))
    await ctx.session.commit()

    out = await execute_tool(ctx, "escalate_to_technician", {"reason": "raison X"})

    assert ctx.created_ticket_id is not None
    ticket = await ctx.session.get(Ticket, ctx.created_ticket_id)
    for section in ("Problème", "Diagnostic", "Étapes proposées", "Documentation consultée", "Conclusion", "Raison de l'escalade"):
        assert section in ticket.description, section
    assert "Vérifier câble secteur" in ticket.description
    assert ticket.description.strip()


# --- B2 : confirmation depuis un tour ultérieur -------------------


@pytest.mark.asyncio
async def test_request_ticket_creation_requires_diagnosis(tool_ctx):
    ctx, *_ = tool_ctx
    out = await execute_tool(ctx, "request_ticket_creation", {"problem_summary": "rien ne marche"})
    assert "diagnostic" in out.lower()
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.pending_ticket_confirmation is False


@pytest.mark.asyncio
async def test_request_then_create_ticket_same_run_is_refused(tool_ctx):
    """B2 : une proposition faite dans le tour courant ne vaut pas confirmation."""

    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    await ctx.session.commit()

    r1 = await execute_tool(ctx, "request_ticket_creation", {"problem_summary": "panne"})
    assert ctx.ticket_proposed_this_run is True
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.pending_ticket_confirmation is True

    r2 = await execute_tool(ctx, "create_ticket", {"description": "hop"})
    assert "prochain message" in r2.lower() or "attends" in r2.lower()
    assert ctx.created_ticket_id is None
    tickets = (await ctx.session.execute(select(Ticket).where(Ticket.conversation_id == ctx.conversation.id))).scalars().all()
    assert tickets == []


@pytest.mark.asyncio
async def test_create_ticket_allowed_when_confirmation_from_previous_run(tool_ctx):
    ctx, product, tech, _ = tool_ctx
    # simule : proposition faite à un tour ANTÉRIEUR (pending vrai, flag run faux)
    ctx.conversation.search_performed = True
    ctx.conversation.pending_ticket_confirmation = True
    await ctx.session.commit()
    assert ctx.ticket_proposed_this_run is False

    out = await execute_tool(ctx, "create_ticket", {"description": "Panne confirmée par le client"})

    assert ctx.created_ticket_id is not None
    ticket = await ctx.session.get(Ticket, ctx.created_ticket_id)
    assert ticket.client_id == ctx.conversation.user_id and ticket.product_id == product.id
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.pending_ticket_confirmation is False


@pytest.mark.asyncio
async def test_create_ticket_refused_without_pending_confirmation(tool_ctx):
    ctx, *_ = tool_ctx
    out = await execute_tool(ctx, "create_ticket", {"description": "hop"})
    assert "aucune proposition" in out.lower()
    assert ctx.created_ticket_id is None


# --- I2 : decline_ticket_proposal -----------------------------------


@pytest.mark.asyncio
async def test_decline_ticket_proposal_clears_pending_confirmation(tool_ctx):
    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.pending_ticket_confirmation = True
    await ctx.session.commit()

    out = await execute_tool(ctx, "decline_ticket_proposal", {})

    assert "refus" in out.lower()
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.pending_ticket_confirmation is False
    assert ctx.created_ticket_id is None


@pytest.mark.asyncio
async def test_decline_ticket_proposal_noop_without_pending_confirmation(tool_ctx):
    ctx, *_ = tool_ctx
    out = await execute_tool(ctx, "decline_ticket_proposal", {})
    assert "aucune proposition" in out.lower()


@pytest.mark.asyncio
async def test_create_ticket_refused_after_decline_even_much_later(tool_ctx):
    """I2 : une fois la proposition déclinée, une confirmation tardive et hors
    contexte ne doit plus jamais créer de ticket sans une NOUVELLE proposition."""

    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.pending_ticket_confirmation = True
    await ctx.session.commit()

    await execute_tool(ctx, "decline_ticket_proposal", {})

    out = await execute_tool(ctx, "create_ticket", {"description": "confirmation tardive et hors contexte"})
    assert "aucune proposition" in out.lower()
    assert ctx.created_ticket_id is None


# --- B3 : ticket déjà ouvert -> pas de ticket_id -----------------


@pytest.mark.asyncio
async def test_escalate_on_existing_ticket_does_not_report_new_ticket_id(tool_ctx):
    ctx, product, tech, _ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.diagnostic_attempts = 2
    await ctx.session.commit()

    # 1er ticket
    await execute_tool(ctx, "escalate_to_technician", {"reason": "1"})
    first_id = ctx.created_ticket_id
    assert first_id is not None

    # 2e tentative sur la même conversation (nouveau run)
    ctx.created_ticket_id = None
    ctx.escalated_this_run = False
    out = await execute_tool(ctx, "escalate_to_technician", {"reason": "2"})

    assert ctx.created_ticket_id is None  # B3 : rien créé ce tour
    assert "déjà" in out.lower()
    count = (await ctx.session.execute(select(Ticket).where(Ticket.conversation_id == ctx.conversation.id))).scalars().all()
    assert len(count) == 1


# --- I3 : anti-doublon atomique (contrainte DB de concurrence) --


@pytest.mark.asyncio
async def test_db_constraint_rejects_second_active_ticket_for_same_conversation(tool_ctx):
    """I3 : vérifie DIRECTEMENT la contrainte DB (migration
    a4f1c2d9e7b3, index unique partiel sur tickets.conversation_id pour les
    statuts non 'closed'), indépendamment de la couche applicative."""

    ctx, product, _, _ = tool_ctx

    t1 = Ticket(
        title="Ticket 1", description="d1", product_id=product.id,
        client_id=ctx.conversation.user_id, conversation_id=ctx.conversation.id, status="open",
    )
    ctx.session.add(t1)
    await ctx.session.commit()

    # SAVEPOINT (transaction imbriquée) : la violation de contrainte et son
    # rollback restent CONTENUS à ce niveau, sans expirer/invalider les
    # objets déjà chargés dans la session (client/tech, nécessaires au
    # teardown de la fixture).
    t2 = Ticket(
        title="Ticket 2", description="d2", product_id=product.id,
        client_id=ctx.conversation.user_id, conversation_id=ctx.conversation.id, status="in_progress",
    )
    with pytest.raises(IntegrityError):
        async with ctx.session.begin_nested():
            ctx.session.add(t2)
            await ctx.session.flush()


@pytest.mark.asyncio
async def test_db_constraint_allows_new_ticket_once_previous_is_closed(tool_ctx):
    """Non-régression : l'index étant PARTIEL (statut <> 'closed'), un
    nouveau ticket actif reste possible une fois le précédent fermé."""

    ctx, product, _, _ = tool_ctx

    t1 = Ticket(
        title="Ticket 1", description="d1", product_id=product.id,
        client_id=ctx.conversation.user_id, conversation_id=ctx.conversation.id, status="closed",
    )
    ctx.session.add(t1)
    await ctx.session.commit()

    t2 = Ticket(
        title="Ticket 2", description="d2", product_id=product.id,
        client_id=ctx.conversation.user_id, conversation_id=ctx.conversation.id, status="open",
    )
    ctx.session.add(t2)
    await ctx.session.commit()  # ne doit PAS lever : t1 est fermé, exclu de l'index


@pytest.mark.asyncio
async def test_ticket_creation_race_is_caught_gracefully(tool_ctx):
    """I3 : simule la course gagnée par une autre requête concurrente — un
    ticket actif a été committé par ailleurs ENTRE la vérification
    applicative « pas de ticket actif » et l'INSERT de cette invocation
    (c'est précisément le scénario non-atomique identifié en review). La
    contrainte DB doit bloquer le doublon, rattrapé proprement (pas de 500,
    pas de second ticket, message informatif, created_ticket_id reste None)."""

    ctx, product, tech, _ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.diagnostic_attempts = 2
    await ctx.session.commit()

    original_check = ctx.ticket_service.get_active_ticket_by_conversation
    calls = {"n": 0}

    async def _stale_then_real_check(conversation_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return None  # pré-vérification de CETTE invocation : rien vu, comme dans une vraie course
        return await original_check(conversation_id)

    ctx.ticket_service.get_active_ticket_by_conversation = _stale_then_real_check

    # une AUTRE requête a déjà créé et committé son ticket entre-temps
    concurrent_ticket = Ticket(
        title="Ticket concurrent", description="Créé par une autre requête pendant la course",
        product_id=product.id, client_id=ctx.conversation.user_id,
        conversation_id=ctx.conversation.id, status="open",
    )
    ctx.session.add(concurrent_ticket)
    await ctx.session.commit()

    out = await execute_tool(ctx, "escalate_to_technician", {"reason": "bloqué"})

    assert ctx.created_ticket_id is None  # cette invocation n'a PAS créé de second ticket
    assert "déjà ouvert" in out.lower()
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.pending_ticket_confirmation is False

    tickets = (
        await ctx.session.execute(select(Ticket).where(Ticket.conversation_id == ctx.conversation.id))
    ).scalars().all()
    assert len(tickets) == 1
    assert tickets[0].id == concurrent_ticket.id


@pytest.mark.asyncio
async def test_request_ticket_creation_refuses_when_ticket_already_active(tool_ctx):
    """CAS B (règle du ticket unique) : request_ticket_creation (chemin
    explicite) doit se refuser lui-même si un ticket actif existe déjà —
    qu'il ait été créé par escalade automatique ou par une demande
    explicite antérieure."""

    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.diagnostic_attempts = 2
    await ctx.session.commit()

    await execute_tool(ctx, "escalate_to_technician", {"reason": "premier ticket"})
    assert ctx.created_ticket_id is not None

    out = await execute_tool(ctx, "request_ticket_creation", {"problem_summary": "nouvelle demande"})

    assert "déjà ouvert" in out.lower()
    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.pending_ticket_confirmation is False
    tickets = (
        await ctx.session.execute(select(Ticket).where(Ticket.conversation_id == ctx.conversation.id))
    ).scalars().all()
    assert len(tickets) == 1


@pytest.mark.asyncio
async def test_escalation_refused_when_ticket_already_created_via_explicit_path(tool_ctx):
    """CAS D (croisement des deux chemins) : un ticket créé via la demande
    EXPLICITE du client (request_ticket_creation -> create_ticket) doit
    aussi bloquer une escalade automatique ultérieure sur la même
    conversation — la règle « un seul ticket actif » ne dépend pas du
    chemin qui l'a créé."""

    ctx, *_ = tool_ctx
    ctx.conversation.search_performed = True
    await ctx.session.commit()

    await execute_tool(ctx, "request_ticket_creation", {"problem_summary": "bruit anormal"})
    ctx.ticket_proposed_this_run = False  # simule un tour ultérieur (B2)
    await execute_tool(ctx, "create_ticket", {"description": "Confirmé par le client"})
    assert ctx.created_ticket_id is not None
    first_ticket_id = ctx.created_ticket_id

    ctx.created_ticket_id = None
    ctx.conversation.diagnostic_attempts = 2
    await ctx.session.commit()

    out = await execute_tool(ctx, "escalate_to_technician", {"reason": "nouvelle panne"})

    assert ctx.created_ticket_id is None  # aucun second ticket
    assert "déjà ouvert" in out.lower()
    tickets = (
        await ctx.session.execute(select(Ticket).where(Ticket.conversation_id == ctx.conversation.id))
    ).scalars().all()
    assert len(tickets) == 1
    assert tickets[0].id == first_ticket_id


@pytest.mark.asyncio
async def test_concurrent_escalation_requests_create_only_one_ticket(tool_ctx):
    """CAS E : deux requêtes RÉELLEMENT concurrentes (deux sessions DB
    indépendantes, exécutées via asyncio.gather) tentant d'escalader la
    même conversation ne doivent jamais produire plus d'un ticket actif —
    garanti par la contrainte DB atomique (migration
    a4f1c2d9e7b3), pas seulement par la vérification applicative
    (lecture-puis-écriture non atomique à elle seule)."""

    ctx, product, tech, _ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.diagnostic_attempts = 2
    await ctx.session.commit()
    conversation_id = ctx.conversation.id
    user_id = ctx.conversation.user_id

    async def _attempt(label: str) -> str:
        async with AsyncSessionLocal() as session:
            conv = await session.get(Conversation, conversation_id)
            user = await session.get(User, user_id)
            local_ctx = AgentContext(
                session=session,
                user=user,
                conversation=conv,
                retriever=StubRetriever([]),
                ticket_service=TicketService(session),
                llm_service=_llm(),
            )
            return await execute_tool(local_ctx, "escalate_to_technician", {"reason": label})

    results = await asyncio.gather(_attempt("requête A"), _attempt("requête B"))

    assert any("prise en charge" in r.lower() for r in results)  # une création a réussi
    assert any("déjà ouvert" in r.lower() for r in results)  # l'autre a été refusée proprement

    tickets = (
        await ctx.session.execute(select(Ticket).where(Ticket.conversation_id == conversation_id))
    ).scalars().all()
    assert len(tickets) == 1


# --- Verrou DB sur diagnostic_attempts (compteur d'escalade) -----


@pytest.mark.asyncio
async def test_concurrent_diagnostic_attempts_increments_are_not_lost(tool_ctx):
    """Verrou DB (SELECT ... FOR UPDATE, cf. record_client_feedback) : deux
    transactions concurrentes qui incrémentent diagnostic_attempts sur la
    MÊME conversation ne doivent jamais se marcher dessus (lecture-
    modification-écriture non atomique = incrément perdu classique). Ce
    test reproduit directement le motif utilisé en production
    (`session.refresh(conv, with_for_update=True)` puis `+= 1`),
    indépendamment des règles métier de `record_client_feedback` (qui
    n'autorisent qu'un seul incrément par cycle par construction, déjà
    couvert par `test_feedback_unresolved_increments_only_when_awaiting`)."""

    ctx, *_ = tool_ctx
    await ctx.session.commit()
    conversation_id = ctx.conversation.id

    async def _increment() -> None:
        async with AsyncSessionLocal() as session:
            conv = await session.get(Conversation, conversation_id)
            await session.refresh(conv, with_for_update=True)
            conv.diagnostic_attempts += 1
            session.add(conv)
            await session.commit()

    await asyncio.gather(_increment(), _increment())

    await ctx.session.refresh(ctx.conversation)
    assert ctx.conversation.diagnostic_attempts == 2  # aucun incrément perdu


# --- B4 : exception dans un outil -> rollback propre -------------


@pytest.mark.asyncio
async def test_tool_exception_rolls_back_and_context_stays_usable(tool_ctx):
    """Un échec non intercepté DANS un outil déclenche un rollback ; le contexte
    (conversation / user) doit rester exploitable ensuite (pas de MissingGreenlet)."""

    ctx, product, tech, _ = tool_ctx
    ctx.conversation.search_performed = True
    ctx.conversation.diagnostic_attempts = 2
    await ctx.session.commit()

    import app.ai.agent.tools as tools_mod

    async def _boom(ctx, *a):
        ctx.session.add(ConversationEvent(conversation_id=ctx.conversation_id, event_type="search", payload={}))
        raise RuntimeError("échec réel en cours de transaction")

    tools_mod._IMPLS["__boom__"] = _boom
    try:
        out = await execute_tool(ctx, "__boom__", {})
    finally:
        tools_mod._IMPLS.pop("__boom__", None)

    assert "échoué" in out.lower()
    # le contexte est toujours utilisable : l'escalade suivante fonctionne
    out2 = await execute_tool(ctx, "escalate_to_technician", {"reason": "après échec"})
    assert ctx.created_ticket_id is not None
    ticket = await ctx.session.get(Ticket, ctx.created_ticket_id)
    assert ticket.client_id == ctx.conversation.user_id


@pytest.mark.asyncio
async def test_unknown_tool_returns_message(tool_ctx):
    ctx, *_ = tool_ctx
    assert "inconnu" in (await execute_tool(ctx, "delete_database", {})).lower()


__all__: list[str] = []
