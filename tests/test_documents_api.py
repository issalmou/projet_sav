"""Tests HTTP de api/documents.py : RBAC documentaire (semaine 4, tâche 2)."""
import pytest

from conftest import auth_headers as _auth_headers


@pytest.mark.asyncio
async def test_status_route_requires_no_authentication(client):
    response = await client.get("/api/v1/documents/status")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_responsable_sav_passes_the_permission_check_on_list(client, actors):
    """Le Responsable SAV est autorisé à lister ses documents (200, pas 403)."""

    _, responsable_token = actors["responsable"]

    response = await client.get("/api/v1/documents/", headers=_auth_headers(responsable_token))

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_administrateur_passes_the_permission_check_on_list(client, actors):
    """L'administrateur a désormais le même accès documentaire que le Responsable SAV."""

    _, admin_token = actors["admin"]

    response = await client.get("/api/v1/documents/", headers=_auth_headers(admin_token))

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_super_admin_bypasses_the_permission_check(client, actors):
    """Comportement conservé de require_roles() : is_superuser=True passe toujours."""

    _, super_token = actors["super_admin"]

    response = await client.get("/api/v1/documents/", headers=_auth_headers(super_token))

    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("actor_key", ["client", "technicien"])
async def test_other_roles_are_forbidden(client, actors, actor_key):
    """CLIENT et TECHNICIEN sont refusés (gestion RAG réservée au staff : Responsable SAV / Administrateur)."""

    _, token = actors[actor_key]

    response = await client.get("/api/v1/documents/", headers=_auth_headers(token))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_route_is_also_protected(client, actors):
    _, client_token = actors["client"]

    response = await client.delete("/api/v1/documents/00000000-0000-0000-0000-000000000000", headers=_auth_headers(client_token))

    assert response.status_code == 403


__all__: list[str] = []
