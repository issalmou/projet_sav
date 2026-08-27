"""Tests de validation Pydantic des schémas Ticket (tâche 4, semaine 5)."""
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.ticket import TicketAutoCreate, TicketCreate, TicketRead, TicketUpdate


def test_ticket_create_accepts_valid_payload():
    client_id = uuid.uuid4()
    ticket = TicketCreate(
        title="Four ne s'allume plus", description="Le four ne réagit plus du tout.", client_id=client_id
    )

    assert ticket.title == "Four ne s'allume plus"
    assert ticket.client_id == client_id
    assert ticket.product_id is None


def test_ticket_create_accepts_optional_product_id():
    product_id = uuid.uuid4()
    ticket = TicketCreate(
        title="Panne", description="Description détaillée.", client_id=uuid.uuid4(), product_id=product_id
    )

    assert ticket.product_id == product_id


def test_ticket_create_rejects_empty_title():
    with pytest.raises(ValidationError):
        TicketCreate(title="", description="Description détaillée.", client_id=uuid.uuid4())


def test_ticket_create_rejects_empty_description():
    with pytest.raises(ValidationError):
        TicketCreate(title="Panne", description="", client_id=uuid.uuid4())


def test_ticket_create_rejects_missing_required_fields():
    with pytest.raises(ValidationError):
        TicketCreate()


def test_ticket_create_requires_client_id():
    # client_id est obligatoire (correction RBAC semaine 6) : TicketCreate
    # est désormais réservé au staff, qui crée toujours au nom d'un client précis.
    with pytest.raises(ValidationError):
        TicketCreate(title="Panne", description="Description détaillée.")


def test_ticket_auto_create_has_no_client_id_field():
    # TicketAutoCreate (workflow de diagnostic automatique) n'a jamais de
    # client_id : le propriétaire est toujours l'utilisateur pour lequel le
    # service agit, jamais une valeur fournie dans un payload.
    ticket = TicketAutoCreate.model_validate(
        {"title": "Panne", "description": "Description détaillée.", "client_id": str(uuid.uuid4())}
    )

    assert not hasattr(ticket, "client_id")


def test_ticket_update_allows_partial_payload():
    update = TicketUpdate(status="in_progress")

    assert update.status.value == "in_progress"
    assert update.title is None
    assert update.assigned_technician_id is None


def test_ticket_update_rejects_invalid_status():
    with pytest.raises(ValidationError):
        TicketUpdate(status="not_a_real_status")


def test_ticket_update_rejects_empty_title_when_provided():
    with pytest.raises(ValidationError):
        TicketUpdate(title="")


def test_ticket_update_accepts_empty_payload():
    update = TicketUpdate()

    assert update.model_dump(exclude_unset=True) == {}


def test_ticket_read_builds_from_nested_data():
    client_id = uuid.uuid4()
    ticket_id = uuid.uuid4()
    payload = {
        "id": ticket_id,
        "title": "Four ne s'allume plus",
        "description": "Le four ne réagit plus du tout.",
        "status": "open",
        "product_id": None,
        "conversation_id": None,
        "created_at": "2026-08-14T10:00:00Z",
        "updated_at": "2026-08-14T10:00:00Z",
        "client": {"id": client_id, "email": "client@example.com", "preferred_language": "fr"},
        "assigned_technician": None,
        "product": None,
    }

    ticket = TicketRead.model_validate(payload)

    assert ticket.id == ticket_id
    assert ticket.status.value == "open"
    assert ticket.client.email == "client@example.com"
    assert ticket.assigned_technician is None


def test_ticket_read_rejects_invalid_status():
    payload = {
        "id": uuid.uuid4(),
        "title": "Panne",
        "description": "Description.",
        "status": "not_a_real_status",
        "product_id": None,
        "conversation_id": None,
        "created_at": "2026-08-14T10:00:00Z",
        "updated_at": "2026-08-14T10:00:00Z",
        "client": {"id": uuid.uuid4(), "email": "client@example.com", "preferred_language": "fr"},
        "assigned_technician": None,
        "product": None,
    }

    with pytest.raises(ValidationError):
        TicketRead.model_validate(payload)
