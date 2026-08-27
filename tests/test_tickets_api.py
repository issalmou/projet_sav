"""Tests HTTP de api/tickets.py : CRUD tickets + RBAC (CDC semaine 5/6).

Correction RBAC (semaine 6) : la création manuelle d'un ticket est réservée
au staff (Responsable SAV / Administrateur / superuser), toujours au nom
d'un client précis. Client et Technicien ne peuvent plus créer de ticket du
tout via l'API — seul le workflow de diagnostic automatique
(DiagnosticService, non exercé ici) crée des tickets en leur nom.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.models.ticket import Ticket
from conftest import auth_headers as _auth_headers
from conftest import create_and_login


UNKNOWN_TICKET_ID = "00000000-0000-0000-0000-000000000000"


@pytest_asyncio.fixture
async def cleanup_tickets(actors, db_session):
    """Supprime tous les tickets créés par le test avant que `actors` ne supprime les utilisateurs.

    `client_id` est en RESTRICT (tâche 3) : la suppression d'un utilisateur
    de test échouerait si un ticket lui appartient encore. Dépend
    explicitement de `actors` pour être instanciée après elle et donc
    finalisée avant elle (ordre LIFO des fixtures pytest).
    """

    yield
    await db_session.execute(delete(Ticket))
    await db_session.commit()


def _ticket_payload(**overrides) -> dict:
    payload = {
        "title": "Four ne s'allume plus",
        "description": "Le four ne réagit plus du tout.",
        "client_id": str(uuid.uuid4()),
    }
    payload.update(overrides)
    return payload


async def _create_ticket_for(client, staff_token: str, client_id, **overrides) -> dict:
    """Crée un ticket via le staff (seule voie manuelle désormais) au nom de `client_id`."""

    response = await client.post(
        "/api/v1/tickets/", json=_ticket_payload(client_id=str(client_id), **overrides), headers=_auth_headers(staff_token)
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_status_route_requires_no_authentication(client):
    response = await client.get("/api/v1/tickets/status")

    assert response.status_code == 200


# --- 401 : aucune authentification ----------------------------------------


@pytest.mark.asyncio
async def test_create_ticket_without_token_is_401(client):
    response = await client.post("/api/v1/tickets/", json=_ticket_payload())

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_tickets_without_token_is_401(client):
    response = await client.get("/api/v1/tickets/")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_ticket_without_token_is_401(client):
    response = await client.get(f"/api/v1/tickets/{uuid.uuid4()}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_ticket_without_token_is_401(client):
    response = await client.patch(f"/api/v1/tickets/{uuid.uuid4()}", json={"title": "x"})

    assert response.status_code == 401


# --- Création : réservée au staff (correction RBAC, semaine 6) -----------


@pytest.mark.asyncio
async def test_responsable_sav_creates_ticket_for_specific_client(client, actors, cleanup_tickets):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    body = await _create_ticket_for(client, responsable_token, client_user.id)

    assert body["client"]["id"] == str(client_user.id)
    assert body["status"] == "open"


@pytest.mark.asyncio
async def test_administrateur_creates_ticket_for_specific_client(client, actors, cleanup_tickets):
    client_user, _ = actors["client"]
    _, admin_token = actors["admin"]

    body = await _create_ticket_for(client, admin_token, client_user.id)

    assert body["client"]["id"] == str(client_user.id)


@pytest.mark.asyncio
async def test_super_admin_creates_ticket_for_specific_client(client, actors, cleanup_tickets):
    client_user, _ = actors["client"]
    _, super_token = actors["super_admin"]

    body = await _create_ticket_for(client, super_token, client_user.id)

    assert body["client"]["id"] == str(client_user.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("actor_key", ["client", "technicien"])
async def test_non_staff_cannot_create_ticket(client, actors, actor_key):
    target_client, _ = actors["client"]
    _, token = actors[actor_key]

    response = await client.post(
        "/api/v1/tickets/", json=_ticket_payload(client_id=str(target_client.id)), headers=_auth_headers(token)
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_ticket_for_unknown_client_is_404(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.post(
        "/api/v1/tickets/", json=_ticket_payload(client_id=UNKNOWN_TICKET_ID), headers=_auth_headers(responsable_token)
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_ticket_for_non_client_user_is_400(client, actors):
    technicien, _ = actors["technicien"]
    _, responsable_token = actors["responsable"]

    response = await client.post(
        "/api/v1/tickets/", json=_ticket_payload(client_id=str(technicien.id)), headers=_auth_headers(responsable_token)
    )

    assert response.status_code == 400


# --- 422 : payload invalide -------------------------------------------------


@pytest.mark.asyncio
async def test_create_ticket_with_empty_title_is_422(client, actors):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(title="", client_id=str(client_user.id)),
        headers=_auth_headers(responsable_token),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_ticket_missing_description_is_422(client, actors):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    response = await client.post(
        "/api/v1/tickets/",
        json={"title": "Panne", "client_id": str(client_user.id)},
        headers=_auth_headers(responsable_token),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_ticket_missing_client_id_is_422(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.post(
        "/api/v1/tickets/",
        json={"title": "Panne", "description": "Description."},
        headers=_auth_headers(responsable_token),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_ticket_with_invalid_status_is_422(client, actors, cleanup_tickets):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    created = await _create_ticket_for(client, responsable_token, client_user.id)

    response = await client.patch(
        f"/api/v1/tickets/{created['id']}",
        json={"status": "not_a_real_status"},
        headers=_auth_headers(responsable_token),
    )

    assert response.status_code == 422


# --- Visibilité : client -----------------------------------------------------


@pytest.mark.asyncio
async def test_client_lists_only_own_tickets(client, actors, db_session, role_ids, cleanup_tickets):
    client_user, token = actors["client"]
    _, responsable_token = actors["responsable"]
    await _create_ticket_for(client, responsable_token, client_user.id)

    other_client, _ = await create_and_login(client, db_session, role_id=role_ids["client"])
    await _create_ticket_for(client, responsable_token, other_client.id, title="Autre panne")

    response = await client.get("/api/v1/tickets/", headers=_auth_headers(token))

    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) == 1
    assert tickets[0]["client"]["id"] == str(client_user.id)

    # cleanup_tickets supprime les tickets avant le teardown de `actors`, mais
    # other_client n'est pas géré par `actors` : on le nettoie nous-mêmes,
    # après avoir supprimé son ticket (RESTRICT).
    await db_session.execute(delete(Ticket).where(Ticket.client_id == other_client.id))
    await db_session.commit()
    await db_session.delete(other_client)
    await db_session.commit()


@pytest.mark.asyncio
async def test_client_can_get_own_ticket(client, actors, cleanup_tickets):
    client_user, token = actors["client"]
    _, responsable_token = actors["responsable"]
    created = await _create_ticket_for(client, responsable_token, client_user.id)

    response = await client.get(f"/api/v1/tickets/{created['id']}", headers=_auth_headers(token))

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_unknown_ticket_is_404(client, actors):
    _, token = actors["client"]

    response = await client.get(f"/api/v1/tickets/{UNKNOWN_TICKET_ID}", headers=_auth_headers(token))

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_client_cannot_get_another_clients_ticket_is_404(client, actors, db_session, role_ids):
    _, responsable_token = actors["responsable"]
    other_client, _ = await create_and_login(client, db_session, role_id=role_ids["client"])
    created = await _create_ticket_for(client, responsable_token, other_client.id)

    _, token = actors["client"]
    response = await client.get(f"/api/v1/tickets/{created['id']}", headers=_auth_headers(token))

    assert response.status_code == 404

    await db_session.execute(delete(Ticket).where(Ticket.id == created["id"]))
    await db_session.commit()
    await db_session.delete(other_client)
    await db_session.commit()


# --- Modification : 403 client, staff/technicien assigné autorisés --------


@pytest.mark.asyncio
async def test_client_cannot_update_own_ticket_is_403(client, actors, cleanup_tickets):
    client_user, token = actors["client"]
    _, responsable_token = actors["responsable"]
    created = await _create_ticket_for(client, responsable_token, client_user.id)

    response = await client.patch(
        f"/api/v1/tickets/{created['id']}", json={"title": "Nouveau titre"}, headers=_auth_headers(token)
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_client_cannot_update_another_clients_ticket_is_404(client, actors, db_session, role_ids):
    _, responsable_token = actors["responsable"]
    other_client, _ = await create_and_login(client, db_session, role_id=role_ids["client"])
    created = await _create_ticket_for(client, responsable_token, other_client.id)

    _, token = actors["client"]
    response = await client.patch(
        f"/api/v1/tickets/{created['id']}", json={"title": "Nouveau titre"}, headers=_auth_headers(token)
    )

    assert response.status_code == 404

    await db_session.execute(delete(Ticket).where(Ticket.id == created["id"]))
    await db_session.commit()
    await db_session.delete(other_client)
    await db_session.commit()


@pytest.mark.asyncio
async def test_update_unknown_ticket_as_staff_is_404(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.patch(
        f"/api/v1/tickets/{UNKNOWN_TICKET_ID}", json={"status": "closed"}, headers=_auth_headers(responsable_token)
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_responsable_sav_can_list_get_and_update_any_ticket(client, actors, cleanup_tickets):
    client_user, _ = actors["client"]
    technicien, _ = actors["technicien"]
    _, responsable_token = actors["responsable"]

    created = await _create_ticket_for(client, responsable_token, client_user.id)

    listed = await client.get("/api/v1/tickets/", headers=_auth_headers(responsable_token))
    assert listed.status_code == 200
    assert any(t["id"] == created["id"] for t in listed.json())

    fetched = await client.get(f"/api/v1/tickets/{created['id']}", headers=_auth_headers(responsable_token))
    assert fetched.status_code == 200

    updated = await client.patch(
        f"/api/v1/tickets/{created['id']}",
        json={"assigned_technician_id": str(technicien.id), "status": "in_progress"},
        headers=_auth_headers(responsable_token),
    )
    assert updated.status_code == 200
    assert updated.json()["assigned_technician"]["id"] == str(technicien.id)
    assert updated.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_technicien_sees_only_assigned_tickets(client, actors, cleanup_tickets):
    client_user, _ = actors["client"]
    technicien, technicien_token = actors["technicien"]
    _, responsable_token = actors["responsable"]

    created = await _create_ticket_for(client, responsable_token, client_user.id)

    before = await client.get("/api/v1/tickets/", headers=_auth_headers(technicien_token))
    assert before.status_code == 200
    assert before.json() == []

    await client.patch(
        f"/api/v1/tickets/{created['id']}",
        json={"assigned_technician_id": str(technicien.id)},
        headers=_auth_headers(responsable_token),
    )

    after = await client.get("/api/v1/tickets/", headers=_auth_headers(technicien_token))
    assert after.status_code == 200
    assert [t["id"] for t in after.json()] == [created["id"]]

    updated = await client.patch(
        f"/api/v1/tickets/{created['id']}", json={"status": "resolved"}, headers=_auth_headers(technicien_token)
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_technicien_assigned_cannot_reassign_ticket_via_api(client, actors, cleanup_tickets):
    """Confirme (tâche 8) que la route respecte la nouvelle restriction du service."""

    client_user, _ = actors["client"]
    technicien, technicien_token = actors["technicien"]
    _, responsable_token = actors["responsable"]

    created = await _create_ticket_for(client, responsable_token, client_user.id)

    await client.patch(
        f"/api/v1/tickets/{created['id']}",
        json={"assigned_technician_id": str(technicien.id)},
        headers=_auth_headers(responsable_token),
    )

    response = await client.patch(
        f"/api/v1/tickets/{created['id']}",
        json={"assigned_technician_id": str(technicien.id)},
        headers=_auth_headers(technicien_token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_assign_non_technician_user_is_400(client, actors, cleanup_tickets):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    created = await _create_ticket_for(client, responsable_token, client_user.id)

    response = await client.patch(
        f"/api/v1/tickets/{created['id']}",
        json={"assigned_technician_id": str(client_user.id)},  # un client, pas un technicien
        headers=_auth_headers(responsable_token),
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_assign_unknown_user_id_is_404(client, actors, cleanup_tickets):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    created = await _create_ticket_for(client, responsable_token, client_user.id)

    response = await client.patch(
        f"/api/v1/tickets/{created['id']}",
        json={"assigned_technician_id": UNKNOWN_TICKET_ID},
        headers=_auth_headers(responsable_token),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_super_admin_lists_all_tickets(client, actors, cleanup_tickets):
    client_user, _ = actors["client"]
    _, super_token = actors["super_admin"]

    await _create_ticket_for(client, super_token, client_user.id)

    response = await client.get("/api/v1/tickets/", headers=_auth_headers(super_token))

    assert response.status_code == 200
    assert len(response.json()) >= 1


# --- Sécurité : conversation_id non injectable, client_id non modifiable ---


@pytest.mark.asyncio
async def test_create_ticket_payload_cannot_inject_conversation_id(client, actors, cleanup_tickets):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(client_id=str(client_user.id), conversation_id=str(uuid.uuid4())),
        headers=_auth_headers(responsable_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["client"]["id"] == str(client_user.id)  # celui légitimement fourni
    assert "conversation_id" in body and body["conversation_id"] is None  # jamais injectable


@pytest.mark.asyncio
async def test_update_ticket_payload_cannot_change_client_id(client, actors, db_session, cleanup_tickets):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    created = await _create_ticket_for(client, responsable_token, client_user.id)

    response = await client.patch(
        f"/api/v1/tickets/{created['id']}",
        json={"status": "in_progress", "client_id": str(uuid.uuid4())},
        headers=_auth_headers(responsable_token),
    )

    assert response.status_code == 200
    assert response.json()["client"]["id"] == str(client_user.id)  # inchangé malgré l'injection (TicketUpdate n'a pas ce champ)


# --- Pagination : GET /tickets (Semaine 7, Tâche 2) --------------------------
#
# Les tickets sont scopés au client authentifié (_scope_to_visible_tickets) :
# un client fraîchement créé par `actors` n'a par construction aucun ticket
# avant que le test n'en crée — les comptes ci-dessous sont donc exacts, sans
# dépendre de l'état global de la base (contrairement au catalogue produits,
# cf. test_products_api.py).


@pytest.mark.asyncio
async def test_list_tickets_without_params_returns_all_visible(client, actors, cleanup_tickets):
    client_user, client_token = actors["client"]
    _, responsable_token = actors["responsable"]
    for i in range(3):
        await _create_ticket_for(client, responsable_token, client_user.id, title=f"Panne {i}")

    response = await client.get("/api/v1/tickets/", headers=_auth_headers(client_token))

    assert response.status_code == 200
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_list_tickets_with_limit(client, actors, cleanup_tickets):
    client_user, client_token = actors["client"]
    _, responsable_token = actors["responsable"]
    for i in range(3):
        await _create_ticket_for(client, responsable_token, client_user.id, title=f"Panne {i}")

    response = await client.get("/api/v1/tickets/?limit=2", headers=_auth_headers(client_token))

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_list_tickets_with_offset(client, actors, cleanup_tickets):
    client_user, client_token = actors["client"]
    _, responsable_token = actors["responsable"]
    for i in range(3):
        await _create_ticket_for(client, responsable_token, client_user.id, title=f"Panne {i}")

    response = await client.get("/api/v1/tickets/?offset=2", headers=_auth_headers(client_token))

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_list_tickets_with_limit_and_offset(client, actors, cleanup_tickets):
    client_user, client_token = actors["client"]
    _, responsable_token = actors["responsable"]
    for i in range(5):
        await _create_ticket_for(client, responsable_token, client_user.id, title=f"Panne {i}")

    response = await client.get("/api/v1/tickets/?limit=2&offset=1", headers=_auth_headers(client_token))

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_list_tickets_empty_is_empty_list(client, actors):
    _, client_token = actors["client"]

    response = await client.get("/api/v1/tickets/", headers=_auth_headers(client_token))

    assert response.status_code == 200
    assert response.json() == []


__all__: list[str] = []
