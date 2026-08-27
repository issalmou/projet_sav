"""Tests de TicketService : règles d'accès CDC semaine 5 (tâche 5).

Les tests appellent TicketService directement (aucune route FastAPI, aucun
`require_roles`) : un test qui passe ici prouve que la règle d'accès est
appliquée dans le service, pas seulement dans une dépendance de route.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.models.conversation import Conversation
from app.models.ticket import Ticket
from app.schemas.ticket import TicketAutoCreate, TicketCreate, TicketUpdate
from app.schemas.user import UserCreate
from app.services.ticket_service import (
    InvalidClientRoleError,
    InvalidTechnicianRoleError,
    TicketPermissionError,
    TicketService,
)
from app.services.user_service import UserService
from conftest import unique_email


@pytest_asyncio.fixture
async def ticket_actors(db_session, role_ids):
    """Un utilisateur par rôle pertinent pour les tickets, + un superuser non-staff."""

    service = UserService(db_session)

    async def _make(role_key: str, *, is_superuser: bool = False):
        return await service.create_user(
            UserCreate(
                email=unique_email(f"ticket.{role_key}"),
                password="ValidPass1",
                role_id=role_ids[role_key],
                is_superuser=is_superuser,
            )
        )

    users = {
        "client_a": await _make("client"),
        "client_b": await _make("client"),
        "technicien": await _make("technicien"),
        "other_technicien": await _make("technicien"),
        "responsable": await _make("responsable_sav"),
        "administrateur": await _make("administrateur"),
        # Superuser avec le rôle "client" : prouve que le bypass vient bien
        # de `is_superuser`, pas du rôle.
        "superuser_client": await _make("client", is_superuser=True),
    }

    yield users

    # client_id est en RESTRICT (tâche 3) : on doit supprimer les tickets de
    # ces utilisateurs avant de pouvoir les supprimer eux-mêmes.
    user_ids = [user.id for user in users.values()]
    await db_session.execute(delete(Ticket).where(Ticket.client_id.in_(user_ids)))
    await db_session.commit()

    for user in users.values():
        still_there = await service.get_user_by_id(user.id)
        if still_there is not None:
            await db_session.delete(still_there)
    await db_session.commit()


@pytest_asyncio.fixture
def ticket_service(db_session):
    return TicketService(db_session)


async def _create(ticket_service, user, *, title="Panne four", description="Le four ne s'allume plus."):
    return await ticket_service.create_ticket(user, TicketAutoCreate(title=title, description=description))


# --- Création automatique (self-service, DiagnosticService) -------------


@pytest.mark.asyncio
async def test_create_ticket_owner_is_always_the_requesting_user(ticket_service, ticket_actors):
    # create_ticket (self-service) reste utilisable par n'importe quel rôle :
    # c'est le chemin qu'emprunte DiagnosticService, jamais affecté par la
    # restriction de la route publique (cf. create_ticket_for_client).
    for key in ("client_a", "technicien", "responsable", "administrateur"):
        user = ticket_actors[key]
        ticket = await _create(ticket_service, user)
        assert ticket.client_id == user.id


@pytest.mark.asyncio
async def test_ticket_auto_create_schema_has_no_client_id_field():
    # Ceinture et bretelles vis-à-vis du schéma : impossible de fournir un
    # client_id sur TicketAutoCreate, donc impossible de créer un ticket
    # "au nom de" via le workflow automatique.
    assert "client_id" not in TicketAutoCreate.model_fields


# --- Création manuelle par le staff, au nom d'un client précis (semaine 6) -


@pytest.mark.asyncio
async def test_staff_creates_ticket_for_specific_client(ticket_service, ticket_actors):
    ticket = await ticket_service.create_ticket_for_client(
        ticket_actors["responsable"],
        TicketCreate(title="Panne four", description="Description.", client_id=ticket_actors["client_a"].id),
    )

    assert ticket.client_id == ticket_actors["client_a"].id


@pytest.mark.asyncio
async def test_administrateur_creates_ticket_for_specific_client(ticket_service, ticket_actors):
    ticket = await ticket_service.create_ticket_for_client(
        ticket_actors["administrateur"],
        TicketCreate(title="Panne", description="Description.", client_id=ticket_actors["client_b"].id),
    )

    assert ticket.client_id == ticket_actors["client_b"].id


@pytest.mark.asyncio
async def test_superuser_creates_ticket_for_specific_client(ticket_service, ticket_actors):
    ticket = await ticket_service.create_ticket_for_client(
        ticket_actors["superuser_client"],
        TicketCreate(title="Panne", description="Description.", client_id=ticket_actors["client_a"].id),
    )

    assert ticket.client_id == ticket_actors["client_a"].id


@pytest.mark.asyncio
@pytest.mark.parametrize("actor_key", ["client_a", "technicien"])
async def test_non_staff_cannot_create_ticket_for_client(ticket_service, ticket_actors, actor_key):
    with pytest.raises(TicketPermissionError):
        await ticket_service.create_ticket_for_client(
            ticket_actors[actor_key],
            TicketCreate(title="Panne", description="Description.", client_id=ticket_actors["client_b"].id),
        )


@pytest.mark.asyncio
async def test_create_ticket_for_unknown_client_raises_value_error(ticket_service, ticket_actors):
    with pytest.raises(ValueError):
        await ticket_service.create_ticket_for_client(
            ticket_actors["responsable"],
            TicketCreate(title="Panne", description="Description.", client_id=uuid.uuid4()),
        )


@pytest.mark.asyncio
async def test_create_ticket_for_non_client_user_raises_invalid_role_error(ticket_service, ticket_actors):
    with pytest.raises(InvalidClientRoleError):
        await ticket_service.create_ticket_for_client(
            ticket_actors["responsable"],
            TicketCreate(title="Panne", description="Description.", client_id=ticket_actors["technicien"].id),
        )


# --- Client : visibilité et modification ---------------------------------


@pytest.mark.asyncio
async def test_client_lists_only_their_own_tickets(ticket_service, ticket_actors):
    own = await _create(ticket_service, ticket_actors["client_a"])
    await _create(ticket_service, ticket_actors["client_b"])

    tickets = await ticket_service.list_tickets(ticket_actors["client_a"])

    assert [t.id for t in tickets] == [own.id]


@pytest.mark.asyncio
async def test_client_can_get_own_ticket(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    fetched = await ticket_service.get_ticket(ticket.id, ticket_actors["client_a"])

    assert fetched.id == ticket.id


@pytest.mark.asyncio
async def test_client_cannot_get_another_clients_ticket_raises_404_style_error(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_b"])

    with pytest.raises(ValueError):
        await ticket_service.get_ticket(ticket.id, ticket_actors["client_a"])


@pytest.mark.asyncio
async def test_client_cannot_modify_own_ticket_raises_403_style_error(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    with pytest.raises(TicketPermissionError):
        await ticket_service.update_ticket(
            ticket.id, ticket_actors["client_a"], TicketUpdate(title="Nouveau titre")
        )


@pytest.mark.asyncio
async def test_client_cannot_modify_another_clients_ticket_raises_404_style_error(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_b"])

    with pytest.raises(ValueError):
        await ticket_service.update_ticket(
            ticket.id, ticket_actors["client_a"], TicketUpdate(title="Nouveau titre")
        )


# --- Technicien : uniquement les tickets assignés -------------------------


@pytest.mark.asyncio
async def test_technicien_lists_only_assigned_tickets(ticket_service, ticket_actors, db_session):
    assigned = await _create(ticket_service, ticket_actors["client_a"])
    assigned.assigned_technician_id = ticket_actors["technicien"].id
    await db_session.commit()

    await _create(ticket_service, ticket_actors["client_b"])  # non assigné

    tickets = await ticket_service.list_tickets(ticket_actors["technicien"])

    assert [t.id for t in tickets] == [assigned.id]


@pytest.mark.asyncio
async def test_technicien_can_get_assigned_ticket(ticket_service, ticket_actors, db_session):
    ticket = await _create(ticket_service, ticket_actors["client_a"])
    ticket.assigned_technician_id = ticket_actors["technicien"].id
    await db_session.commit()

    fetched = await ticket_service.get_ticket(ticket.id, ticket_actors["technicien"])

    assert fetched.id == ticket.id


@pytest.mark.asyncio
async def test_technicien_cannot_get_unassigned_ticket_raises_404_style_error(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    with pytest.raises(ValueError):
        await ticket_service.get_ticket(ticket.id, ticket_actors["technicien"])


@pytest.mark.asyncio
async def test_technicien_can_update_assigned_ticket(ticket_service, ticket_actors, db_session):
    ticket = await _create(ticket_service, ticket_actors["client_a"])
    ticket.assigned_technician_id = ticket_actors["technicien"].id
    await db_session.commit()

    updated = await ticket_service.update_ticket(
        ticket.id, ticket_actors["technicien"], TicketUpdate(status="in_progress")
    )

    assert updated.status == "in_progress"
    assert isinstance(updated.status, str)  # jamais un membre d'enum brut persisté


@pytest.mark.asyncio
async def test_technicien_cannot_update_unassigned_ticket_raises_404_style_error(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    with pytest.raises(ValueError):
        await ticket_service.update_ticket(
            ticket.id, ticket_actors["other_technicien"], TicketUpdate(status="in_progress")
        )


# --- Réassignation (assigned_technician_id) : réservée au staff (tâche 8) -


@pytest.mark.asyncio
async def test_technicien_assigned_cannot_reassign_ticket(ticket_service, ticket_actors, db_session):
    ticket = await _create(ticket_service, ticket_actors["client_a"])
    ticket.assigned_technician_id = ticket_actors["technicien"].id
    await db_session.commit()

    with pytest.raises(TicketPermissionError):
        await ticket_service.update_ticket(
            ticket.id,
            ticket_actors["technicien"],
            TicketUpdate(assigned_technician_id=ticket_actors["other_technicien"].id),
        )


@pytest.mark.asyncio
async def test_technicien_assigned_can_still_update_other_fields(ticket_service, ticket_actors, db_session):
    # Non-régression explicite du point 3 demandé : les autres champs restent modifiables.
    ticket = await _create(ticket_service, ticket_actors["client_a"])
    ticket.assigned_technician_id = ticket_actors["technicien"].id
    await db_session.commit()

    updated = await ticket_service.update_ticket(
        ticket.id,
        ticket_actors["technicien"],
        TicketUpdate(status="resolved", description="Pièce remplacée."),
    )

    assert updated.status == "resolved"
    assert updated.description == "Pièce remplacée."


@pytest.mark.asyncio
async def test_responsable_sav_can_reassign_ticket(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    updated = await ticket_service.update_ticket(
        ticket.id, ticket_actors["responsable"], TicketUpdate(assigned_technician_id=ticket_actors["technicien"].id)
    )

    assert updated.assigned_technician_id == ticket_actors["technicien"].id


@pytest.mark.asyncio
async def test_administrateur_can_reassign_ticket(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    updated = await ticket_service.update_ticket(
        ticket.id,
        ticket_actors["administrateur"],
        TicketUpdate(assigned_technician_id=ticket_actors["technicien"].id),
    )

    assert updated.assigned_technician_id == ticket_actors["technicien"].id


@pytest.mark.asyncio
async def test_superuser_can_reassign_ticket(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    updated = await ticket_service.update_ticket(
        ticket.id,
        ticket_actors["superuser_client"],
        TicketUpdate(assigned_technician_id=ticket_actors["technicien"].id),
    )

    assert updated.assigned_technician_id == ticket_actors["technicien"].id


@pytest.mark.asyncio
async def test_client_cannot_reassign_own_ticket(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    # Le client est déjà bloqué en amont (_can_modify), avant même d'atteindre
    # la vérification de réassignation : même exception que toute autre
    # tentative de modification par le client (403).
    with pytest.raises(TicketPermissionError):
        await ticket_service.update_ticket(
            ticket.id,
            ticket_actors["client_a"],
            TicketUpdate(assigned_technician_id=ticket_actors["technicien"].id),
        )


# --- Validation de rôle sur assigned_technician_id ------------------------


@pytest.mark.asyncio
async def test_reassign_to_nonexistent_user_raises_value_error(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    with pytest.raises(ValueError):
        await ticket_service.update_ticket(
            ticket.id, ticket_actors["responsable"], TicketUpdate(assigned_technician_id=uuid.uuid4())
        )


@pytest.mark.asyncio
async def test_reassign_to_non_technician_raises_invalid_role_error(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    with pytest.raises(InvalidTechnicianRoleError):
        await ticket_service.update_ticket(
            ticket.id,
            ticket_actors["responsable"],
            TicketUpdate(assigned_technician_id=ticket_actors["client_b"].id),
        )


@pytest.mark.asyncio
async def test_reassign_to_valid_technician_succeeds(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    updated = await ticket_service.update_ticket(
        ticket.id, ticket_actors["administrateur"], TicketUpdate(assigned_technician_id=ticket_actors["technicien"].id)
    )

    assert updated.assigned_technician_id == ticket_actors["technicien"].id


@pytest.mark.asyncio
async def test_staff_can_unassign_ticket_with_explicit_null(ticket_service, ticket_actors, db_session):
    ticket = await _create(ticket_service, ticket_actors["client_a"])
    ticket.assigned_technician_id = ticket_actors["technicien"].id
    await db_session.commit()

    updated = await ticket_service.update_ticket(
        ticket.id, ticket_actors["responsable"], TicketUpdate(assigned_technician_id=None)
    )

    assert updated.assigned_technician_id is None


@pytest.mark.asyncio
async def test_technicien_cannot_unassign_own_ticket_with_null(ticket_service, ticket_actors, db_session):
    ticket = await _create(ticket_service, ticket_actors["client_a"])
    ticket.assigned_technician_id = ticket_actors["technicien"].id
    await db_session.commit()

    with pytest.raises(TicketPermissionError):
        await ticket_service.update_ticket(
            ticket.id, ticket_actors["technicien"], TicketUpdate(assigned_technician_id=None)
        )


# --- Staff (Responsable SAV / Administrateur) : accès total --------------


@pytest.mark.asyncio
async def test_responsable_sav_lists_all_tickets(ticket_service, ticket_actors):
    a = await _create(ticket_service, ticket_actors["client_a"])
    b = await _create(ticket_service, ticket_actors["client_b"])

    tickets = await ticket_service.list_tickets(ticket_actors["responsable"])

    assert {t.id for t in tickets} == {a.id, b.id}


@pytest.mark.asyncio
async def test_responsable_sav_can_get_and_update_any_ticket(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_a"])

    fetched = await ticket_service.get_ticket(ticket.id, ticket_actors["responsable"])
    assert fetched.id == ticket.id

    updated = await ticket_service.update_ticket(
        ticket.id, ticket_actors["responsable"], TicketUpdate(assigned_technician_id=ticket_actors["technicien"].id)
    )
    assert updated.assigned_technician_id == ticket_actors["technicien"].id


@pytest.mark.asyncio
async def test_administrateur_lists_all_tickets_and_can_update(ticket_service, ticket_actors):
    a = await _create(ticket_service, ticket_actors["client_a"])
    await _create(ticket_service, ticket_actors["client_b"])

    tickets = await ticket_service.list_tickets(ticket_actors["administrateur"])
    assert len(tickets) == 2

    updated = await ticket_service.update_ticket(
        a.id, ticket_actors["administrateur"], TicketUpdate(status="closed")
    )
    assert updated.status == "closed"


# --- Superuser : bypass total, indépendant du rôle ------------------------


@pytest.mark.asyncio
async def test_superuser_with_client_role_lists_all_tickets(ticket_service, ticket_actors):
    a = await _create(ticket_service, ticket_actors["client_a"])
    b = await _create(ticket_service, ticket_actors["client_b"])

    tickets = await ticket_service.list_tickets(ticket_actors["superuser_client"])

    assert {t.id for t in tickets} == {a.id, b.id}


@pytest.mark.asyncio
async def test_superuser_with_client_role_can_get_and_update_others_ticket(ticket_service, ticket_actors):
    ticket = await _create(ticket_service, ticket_actors["client_b"])

    fetched = await ticket_service.get_ticket(ticket.id, ticket_actors["superuser_client"])
    assert fetched.id == ticket.id

    updated = await ticket_service.update_ticket(
        ticket.id, ticket_actors["superuser_client"], TicketUpdate(status="resolved")
    )
    assert updated.status == "resolved"


# --- conversation_id / dédoublonnage (tâche 7) ----------------------------


@pytest_asyncio.fixture
async def diagnostic_conversation(db_session, ticket_actors):
    conversation = Conversation(user_id=ticket_actors["client_a"].id, title="Panne four")
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    yield conversation

    still_there = await db_session.get(Conversation, conversation.id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


@pytest.mark.asyncio
async def test_create_ticket_accepts_conversation_id(ticket_service, ticket_actors, diagnostic_conversation):
    ticket = await ticket_service.create_ticket(
        ticket_actors["client_a"],
        TicketAutoCreate(title="Panne", description="Description."),
        conversation_id=diagnostic_conversation.id,
    )

    assert ticket.conversation_id == diagnostic_conversation.id


@pytest.mark.asyncio
async def test_get_active_ticket_by_conversation_returns_none_when_no_ticket(
    ticket_service, diagnostic_conversation
):
    result = await ticket_service.get_active_ticket_by_conversation(diagnostic_conversation.id)

    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["open", "in_progress", "resolved"])
async def test_get_active_ticket_by_conversation_finds_non_closed_ticket(
    ticket_service, ticket_actors, diagnostic_conversation, status
):
    ticket = await ticket_service.create_ticket(
        ticket_actors["client_a"],
        TicketAutoCreate(title="Panne", description="Description."),
        conversation_id=diagnostic_conversation.id,
    )
    await ticket_service.update_ticket(ticket.id, ticket_actors["responsable"], TicketUpdate(status=status))

    result = await ticket_service.get_active_ticket_by_conversation(diagnostic_conversation.id)

    assert result is not None
    assert result.id == ticket.id


@pytest.mark.asyncio
async def test_get_active_ticket_by_conversation_ignores_closed_ticket(
    ticket_service, ticket_actors, diagnostic_conversation
):
    ticket = await ticket_service.create_ticket(
        ticket_actors["client_a"],
        TicketAutoCreate(title="Panne", description="Description."),
        conversation_id=diagnostic_conversation.id,
    )
    await ticket_service.update_ticket(ticket.id, ticket_actors["responsable"], TicketUpdate(status="closed"))

    result = await ticket_service.get_active_ticket_by_conversation(diagnostic_conversation.id)

    assert result is None
