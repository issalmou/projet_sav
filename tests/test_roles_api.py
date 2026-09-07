"""Tests HTTP de api/roles.py : CRUD + RBAC (gestion des rôles).

Matrice attendue (cf. cadrage) :
- Lecture (GET) : staff (administrateur, responsable SAV) + superuser ;
  le responsable SAV ne voit jamais le rôle `administrateur`.
- Écriture (POST/PUT/DELETE) : administrateur + superuser uniquement, le
  responsable SAV en est exclu (contrairement à la gestion des utilisateurs).
- Technicien et client n'ont accès à aucune route de ce module.

`RoleCreate.name` est typé `RoleName` : les 4 valeurs existent déjà via le
seed, donc une création "autorisée" (administrateur/superuser) aboutit
toujours à un 409 (nom déjà pris) — ce qui suffit à distinguer le refus
d'autorisation (403) du refus métier (409) et donc à valider la garde RBAC.
"""
import uuid

import pytest

from app.database.session import AsyncSessionLocal
from app.schemas.user import UserCreate
from app.services.role_service import RoleService
from app.services.user_service import UserService
from conftest import auth_headers as _auth_headers


@pytest.mark.asyncio
async def test_client_and_technicien_cannot_create_role(client, role_ids, actors):
    _, client_token = actors["client"]
    _, technicien_token = actors["technicien"]

    for token in (client_token, technicien_token):
        response = await client.post(
            "/api/v1/roles/",
            headers=_auth_headers(token),
            json={"name": "client", "description": "x"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_responsable_sav_cannot_create_role(client, role_ids, actors):
    _, responsable_token = actors["responsable"]

    response = await client.post(
        "/api/v1/roles/",
        headers=_auth_headers(responsable_token),
        json={"name": "technicien", "description": "x"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_and_super_admin_create_role_hits_conflict_not_permission_denial(client, role_ids, actors):
    _, admin_token = actors["admin"]
    _, super_token = actors["super_admin"]

    for token in (admin_token, super_token):
        response = await client.post(
            "/api/v1/roles/",
            headers=_auth_headers(token),
            json={"name": "client", "description": "x"},
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_client_and_technicien_cannot_list_roles(client, actors):
    _, client_token = actors["client"]
    _, technicien_token = actors["technicien"]

    for token in (client_token, technicien_token):
        response = await client.get("/api/v1/roles/", headers=_auth_headers(token))
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_responsable_sav_list_hides_administrateur(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.get("/api/v1/roles/", headers=_auth_headers(responsable_token))

    assert response.status_code == 200
    names = {role["name"] for role in response.json()}
    assert "administrateur" not in names
    assert {"client", "technicien", "responsable_sav"} <= names


@pytest.mark.asyncio
async def test_admin_and_super_admin_list_includes_administrateur(client, actors):
    _, admin_token = actors["admin"]
    _, super_token = actors["super_admin"]

    for token in (admin_token, super_token):
        response = await client.get("/api/v1/roles/", headers=_auth_headers(token))
        assert response.status_code == 200
        names = {role["name"] for role in response.json()}
        assert "administrateur" in names


@pytest.mark.asyncio
async def test_responsable_sav_cannot_get_administrateur_role_directly(client, role_ids, actors):
    _, responsable_token = actors["responsable"]

    response = await client.get(
        f"/api/v1/roles/{role_ids['administrateur']}", headers=_auth_headers(responsable_token)
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_get_administrateur_role_directly(client, role_ids, actors):
    _, admin_token = actors["admin"]

    response = await client.get(f"/api/v1/roles/{role_ids['administrateur']}", headers=_auth_headers(admin_token))
    assert response.status_code == 200
    assert response.json()["name"] == "administrateur"


@pytest.mark.asyncio
async def test_get_missing_role_is_404(client, actors):
    _, super_token = actors["super_admin"]

    response = await client.get(f"/api/v1/roles/{uuid.uuid4()}", headers=_auth_headers(super_token))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_client_technicien_and_responsable_sav_cannot_update_role(client, actors, extra_role):
    _, client_token = actors["client"]
    _, technicien_token = actors["technicien"]
    _, responsable_token = actors["responsable"]

    for token in (client_token, technicien_token, responsable_token):
        response = await client.put(
            f"/api/v1/roles/{extra_role.id}",
            headers=_auth_headers(token),
            json={"description": "tentative non autorisée"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_update_role_description(client, actors, extra_role):
    _, admin_token = actors["admin"]

    response = await client.put(
        f"/api/v1/roles/{extra_role.id}",
        headers=_auth_headers(admin_token),
        json={"description": "Description mise à jour"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Description mise à jour"
    assert response.json()["name"] == extra_role.name


@pytest.mark.asyncio
async def test_client_technicien_and_responsable_sav_cannot_delete_role(
    client, db_session, actors, extra_role
):
    _, client_token = actors["client"]
    _, technicien_token = actors["technicien"]
    _, responsable_token = actors["responsable"]

    for token in (client_token, technicien_token, responsable_token):
        response = await client.delete(f"/api/v1/roles/{extra_role.id}", headers=_auth_headers(token))
        assert response.status_code == 403

    service = RoleService(db_session)
    assert await service.get_role_by_id(extra_role.id) is not None


@pytest.mark.asyncio
async def test_admin_delete_role_blocked_while_in_use(client, db_session, actors, extra_role):
    _, admin_token = actors["admin"]

    user_service = UserService(db_session)
    email = f"role-in-use-api.{uuid.uuid4().hex[:10]}@example.com"
    created = await user_service.create_user(
        UserCreate(email=email, password="ValidPass1", role_id=extra_role.id)
    )

    response = await client.delete(f"/api/v1/roles/{extra_role.id}", headers=_auth_headers(admin_token))
    assert response.status_code == 409

    await db_session.delete(await user_service.get_user_by_id(created.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_super_admin_can_delete_unused_role(client, actors, extra_role):
    _, super_token = actors["super_admin"]

    response = await client.delete(f"/api/v1/roles/{extra_role.id}", headers=_auth_headers(super_token))
    assert response.status_code == 204

    # Session fraîche (pas `db_session`) : la suppression a eu lieu sur la
    # session de la requête HTTP (dépendance `get_db_session`), distincte de
    # `db_session`, qui a déjà mis `extra_role` dans sa map d'identité (créé
    # via cette même session dans la fixture) et le renverrait tel quel.
    async with AsyncSessionLocal() as fresh_session:
        service = RoleService(fresh_session)
        assert await service.get_role_by_id(extra_role.id) is None
