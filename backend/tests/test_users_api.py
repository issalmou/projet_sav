"""Tests HTTP de api/users.py : CRUD + RBAC (tâche 9)."""
import uuid

import pytest
import pytest_asyncio

from app.schemas.user import UserCreate
from app.services.user_service import UserService


def _unique_email(prefix: str) -> str:
    return f"{prefix}.{uuid.uuid4().hex[:10]}@example.com"


async def _create_and_login(client, db_session, role_id=None, is_superuser=False):
    """Crée un utilisateur directement via le service (hors API) et retourne (user, access_token)."""

    service = UserService(db_session)
    email = _unique_email("rbac")
    user = await service.create_user(
        UserCreate(email=email, password="ValidPass1", role_id=role_id, is_superuser=is_superuser)
    )

    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPass1"})
    token = login.json()["access_token"]

    return user, token


@pytest_asyncio.fixture
async def actors(client, db_session, role_ids):
    """Un utilisateur de chaque rôle (+ un super admin), nettoyés après le test."""

    super_admin, super_token = await _create_and_login(
        client, db_session, role_id=role_ids["administrateur"], is_superuser=True
    )
    admin, admin_token = await _create_and_login(client, db_session, role_id=role_ids["administrateur"])
    responsable, responsable_token = await _create_and_login(client, db_session, role_id=role_ids["responsable_sav"])
    technicien, technicien_token = await _create_and_login(client, db_session, role_id=role_ids["technicien"])
    client_user, client_token = await _create_and_login(client, db_session, role_id=role_ids["client"])

    yield {
        "super_admin": (super_admin, super_token),
        "admin": (admin, admin_token),
        "responsable": (responsable, responsable_token),
        "technicien": (technicien, technicien_token),
        "client": (client_user, client_token),
    }

    service = UserService(db_session)
    for user, _ in [
        (super_admin, None),
        (admin, None),
        (responsable, None),
        (technicien, None),
        (client_user, None),
    ]:
        still_there = await service.get_user_by_id(user.id)
        if still_there is not None:
            await db_session.delete(still_there)
    await db_session.commit()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


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
