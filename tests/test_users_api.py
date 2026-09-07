"""Tests HTTP de api/users.py : CRUD + RBAC (tâche 9)."""
import uuid

import pytest

from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user_service import UserService
from conftest import auth_headers as _auth_headers
from conftest import unique_email as _unique_email


async def _is_superuser_in_db(user_id) -> bool:
    """Relit `is_superuser` depuis une session fraîche (jamais la map d'identité d'un autre test)."""

    async with AsyncSessionLocal() as fresh:
        user = await fresh.get(User, user_id)
        return user is not None and user.is_superuser


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


# --- Réinitialisation du mot de passe (via le champ `password` de PUT /users/{id}) ---
# Trois flux distincts : (1) un utilisateur change son propre mot de passe (self-service),
# (2) un membre du staff dans son périmètre réinitialise celui d'un tiers, (3) le staff
# hors périmètre (ou non-staff) en est empêché. Matrice attendue : SuperAdmin/Administrateur/
# Responsable SAV (dans son périmètre) autorisés, Technicien/Client jamais autorisés sur un tiers.


@pytest.mark.asyncio
async def test_user_can_change_own_password(client, actors):
    client_user, client_token = actors["client"]

    response = await client.put(
        f"/api/v1/users/{client_user.id}",
        headers=_auth_headers(client_token),
        json={"password": "NewValidPass1"},
    )
    assert response.status_code == 200

    login = await client.post(
        "/api/v1/auth/login", json={"email": client_user.email, "password": "NewValidPass1"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_responsable_sav_can_reset_password_within_scope(client, actors):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    response = await client.put(
        f"/api/v1/users/{client_user.id}",
        headers=_auth_headers(responsable_token),
        json={"password": "ResetByStaff1"},
    )
    assert response.status_code == 200

    login = await client.post(
        "/api/v1/auth/login", json={"email": client_user.email, "password": "ResetByStaff1"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_responsable_sav_cannot_reset_admin_password(client, actors):
    admin_user, _ = actors["admin"]
    _, responsable_token = actors["responsable"]

    response = await client.put(
        f"/api/v1/users/{admin_user.id}",
        headers=_auth_headers(responsable_token),
        json={"password": "ShouldNotWork1"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_administrateur_can_reset_password_of_non_admin(client, actors):
    technicien_user, _ = actors["technicien"]
    _, admin_token = actors["admin"]

    response = await client.put(
        f"/api/v1/users/{technicien_user.id}",
        headers=_auth_headers(admin_token),
        json={"password": "ResetByAdmin1"},
    )
    assert response.status_code == 200

    login = await client.post(
        "/api/v1/auth/login", json={"email": technicien_user.email, "password": "ResetByAdmin1"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_super_admin_can_reset_admin_password(client, actors):
    admin_user, _ = actors["admin"]
    _, super_token = actors["super_admin"]

    response = await client.put(
        f"/api/v1/users/{admin_user.id}",
        headers=_auth_headers(super_token),
        json={"password": "ResetBySuper1"},
    )
    assert response.status_code == 200

    login = await client.post(
        "/api/v1/auth/login", json={"email": admin_user.email, "password": "ResetBySuper1"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_technicien_cannot_reset_anyone_elses_password(client, actors):
    client_user, _ = actors["client"]
    _, technicien_token = actors["technicien"]

    response = await client.put(
        f"/api/v1/users/{client_user.id}",
        headers=_auth_headers(technicien_token),
        json={"password": "ShouldNotWork1"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_client_cannot_reset_anyone_elses_password(client, actors):
    technicien_user, _ = actors["technicien"]
    _, client_token = actors["client"]

    response = await client.put(
        f"/api/v1/users/{technicien_user.id}",
        headers=_auth_headers(client_token),
        json={"password": "ShouldNotWork1"},
    )
    assert response.status_code == 403


# --- D1 : protection du statut `is_superuser` (élévation de privilèges) ---
# Deux règles, orthogonales au périmètre par rôle (`can_manage_role`), qui ne
# doivent JAMAIS être contournables via l'API Users :
#   (a) seul un super admin peut accorder ou retirer `is_superuser` ;
#   (b) seul un super admin peut gérer un compte qui est déjà super admin.
# Les autres règles RBAC (périmètre par rôle, self-service, reset password)
# restent strictement inchangées — tests de non-régression `is_active` inclus.


@pytest.mark.asyncio
async def test_responsable_sav_cannot_create_superuser(client, role_ids, actors, db_session):
    _, responsable_token = actors["responsable"]
    email = _unique_email("esc")

    response = await client.post(
        "/api/v1/users/",
        headers=_auth_headers(responsable_token),
        json={
            "email": email,
            "password": "ValidPass1",
            "role_id": str(role_ids["client"]),
            "is_superuser": True,
        },
    )

    assert response.status_code == 403
    assert await UserService(db_session).get_user_by_email(email) is None


@pytest.mark.asyncio
async def test_normal_admin_cannot_create_superuser(client, role_ids, actors, db_session):
    _, admin_token = actors["admin"]
    email = _unique_email("esc")

    response = await client.post(
        "/api/v1/users/",
        headers=_auth_headers(admin_token),
        json={
            "email": email,
            "password": "ValidPass1",
            "role_id": str(role_ids["client"]),
            "is_superuser": True,
        },
    )

    assert response.status_code == 403
    assert await UserService(db_session).get_user_by_email(email) is None


@pytest.mark.asyncio
async def test_super_admin_can_create_superuser(client, role_ids, actors, db_session):
    _, super_token = actors["super_admin"]
    email = _unique_email("esc")

    response = await client.post(
        "/api/v1/users/",
        headers=_auth_headers(super_token),
        json={
            "email": email,
            "password": "ValidPass1",
            "role_id": str(role_ids["client"]),
            "is_superuser": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["is_superuser"] is True

    service = UserService(db_session)
    created = await service.get_user_by_email(email)
    if created is not None:
        await db_session.delete(created)
        await db_session.commit()


@pytest.mark.asyncio
async def test_responsable_sav_cannot_grant_superuser_via_update(client, actors):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    response = await client.put(
        f"/api/v1/users/{client_user.id}",
        headers=_auth_headers(responsable_token),
        json={"is_superuser": True},
    )

    assert response.status_code == 403
    assert await _is_superuser_in_db(client_user.id) is False


@pytest.mark.asyncio
async def test_normal_admin_cannot_grant_superuser_via_update(client, actors):
    technicien_user, _ = actors["technicien"]
    _, admin_token = actors["admin"]

    response = await client.put(
        f"/api/v1/users/{technicien_user.id}",
        headers=_auth_headers(admin_token),
        json={"is_superuser": True},
    )

    assert response.status_code == 403
    assert await _is_superuser_in_db(technicien_user.id) is False


@pytest.mark.asyncio
async def test_super_admin_can_toggle_superuser_via_update(client, actors):
    technicien_user, _ = actors["technicien"]
    _, super_token = actors["super_admin"]

    granted = await client.put(
        f"/api/v1/users/{technicien_user.id}",
        headers=_auth_headers(super_token),
        json={"is_superuser": True},
    )
    assert granted.status_code == 200
    assert granted.json()["is_superuser"] is True
    assert await _is_superuser_in_db(technicien_user.id) is True

    revoked = await client.put(
        f"/api/v1/users/{technicien_user.id}",
        headers=_auth_headers(super_token),
        json={"is_superuser": False},
    )
    assert revoked.status_code == 200
    assert revoked.json()["is_superuser"] is False
    assert await _is_superuser_in_db(technicien_user.id) is False


@pytest.mark.asyncio
async def test_normal_admin_cannot_manage_a_superuser_account(client, role_ids, db_session, actors):
    """Un compte super admin portant un rôle dans le périmètre d'un admin normal reste intouchable."""

    _, admin_token = actors["admin"]

    service = UserService(db_session)
    email = _unique_email("suacct")
    target = await service.create_user(
        UserCreate(
            email=email,
            password="ValidPass1",
            role_id=role_ids["responsable_sav"],
            is_superuser=True,
        )
    )
    target_id = target.id

    response = await client.put(
        f"/api/v1/users/{target_id}",
        headers=_auth_headers(admin_token),
        json={"full_name": "Tentative interdite"},
    )
    assert response.status_code == 403

    async with AsyncSessionLocal() as fresh:
        obj = await fresh.get(User, target_id)
        if obj is not None:
            await fresh.delete(obj)
            await fresh.commit()


@pytest.mark.asyncio
async def test_staff_cannot_deactivate_account_outside_perimeter(client, actors):
    """Non-régression `is_active` : le périmètre par rôle borne déjà cette écriture."""

    admin_user, _ = actors["admin"]
    _, responsable_token = actors["responsable"]

    response = await client.put(
        f"/api/v1/users/{admin_user.id}",
        headers=_auth_headers(responsable_token),
        json={"is_active": False},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_deactivate_account_within_perimeter(client, actors):
    """Non-régression `is_active` : le staff garde le droit de (dé)activer dans son périmètre."""

    technicien_user, _ = actors["technicien"]
    _, admin_token = actors["admin"]

    response = await client.put(
        f"/api/v1/users/{technicien_user.id}",
        headers=_auth_headers(admin_token),
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
