"""Tests HTTP de api/users.py : CRUD + RBAC (tâche 9)."""
import uuid

import pytest

from app.services.user_service import UserService
from conftest import auth_headers as _auth_headers
from conftest import unique_email as _unique_email


@pytest.mark.asyncio
async def test_responsable_sav_can_create_technicien_but_not_administrateur(client, role_ids, actors, db_session):
    _, responsable_token = actors["responsable"]

    ok = await client.post(
        "/api/v1/users/",
        headers=_auth_headers(responsable_token),
        json={"email": _unique_email("new"), "password": "ValidPass1", "role_id": str(role_ids["technicien"])},
    )
    assert ok.status_code == 201

    forbidden = await client.post(
        "/api/v1/users/",
        headers=_auth_headers(responsable_token),
        json={"email": _unique_email("new"), "password": "ValidPass1", "role_id": str(role_ids["administrateur"])},
    )
    assert forbidden.status_code == 403

    # nettoyage du compte technicien créé avec succès
    service = UserService(db_session)
    created = await service.get_user_by_id(uuid.UUID(ok.json()["id"]))
    if created is not None:
        await db_session.delete(created)
        await db_session.commit()


@pytest.mark.asyncio
async def test_normal_admin_cannot_create_another_admin(client, role_ids, actors):
    _, admin_token = actors["admin"]

    response = await client.post(
        "/api/v1/users/",
        headers=_auth_headers(admin_token),
        json={"email": _unique_email("new"), "password": "ValidPass1", "role_id": str(role_ids["administrateur"])},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_can_create_another_admin(client, role_ids, actors, db_session):
    _, super_token = actors["super_admin"]

    response = await client.post(
        "/api/v1/users/",
        headers=_auth_headers(super_token),
        json={"email": _unique_email("new"), "password": "ValidPass1", "role_id": str(role_ids["administrateur"])},
    )

    assert response.status_code == 201

    # nettoyage du compte admin créé par ce test
    service = UserService(db_session)
    created = await service.get_user_by_id(uuid.UUID(response.json()["id"]))
    if created is not None:
        await db_session.delete(created)
        await db_session.commit()


@pytest.mark.asyncio
async def test_client_cannot_create_users(client, role_ids, actors):
    _, client_token = actors["client"]

    response = await client.post(
        "/api/v1/users/",
        headers=_auth_headers(client_token),
        json={"email": _unique_email("new"), "password": "ValidPass1", "role_id": str(role_ids["client"])},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_user_duplicate_email_is_409(client, role_ids, actors):
    _, super_token = actors["super_admin"]
    client_user, _ = actors["client"]

    response = await client.post(
        "/api/v1/users/",
        headers=_auth_headers(super_token),
        json={"email": client_user.email, "password": "ValidPass1", "role_id": str(role_ids["client"])},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_responsable_sav_list_is_scoped_to_client_and_technicien(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.get("/api/v1/users/", headers=_auth_headers(responsable_token))

    assert response.status_code == 200
    roles_seen = {u["role"]["name"] for u in response.json() if u["role"]}
    assert roles_seen <= {"client", "technicien"}


@pytest.mark.asyncio
async def test_self_access_and_self_privilege_escalation_blocked(client, role_ids, actors):
    client_user, client_token = actors["client"]

    own_profile = await client.get(f"/api/v1/users/{client_user.id}", headers=_auth_headers(client_token))
    assert own_profile.status_code == 200

    escalation = await client.put(
        f"/api/v1/users/{client_user.id}",
        headers=_auth_headers(client_token),
        json={"role_id": str(role_ids["administrateur"])},
    )
    assert escalation.status_code == 403

    rename = await client.put(
        f"/api/v1/users/{client_user.id}",
        headers=_auth_headers(client_token),
        json={"full_name": "Nouveau nom"},
    )
    assert rename.status_code == 200


@pytest.mark.asyncio
async def test_responsable_sav_cannot_access_admin_account(client, actors):
    admin_user, _ = actors["admin"]
    _, responsable_token = actors["responsable"]

    response = await client.get(f"/api/v1/users/{admin_user.id}", headers=_auth_headers(responsable_token))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_missing_user_is_404(client, actors):
    _, super_token = actors["super_admin"]

    response = await client.get(
        f"/api/v1/users/{uuid.uuid4()}",
        headers=_auth_headers(super_token),
    )

    assert response.status_code == 404
