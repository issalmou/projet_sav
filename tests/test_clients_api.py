"""Tests HTTP de api/clients.py : affectation produit ↔ client (avec quantité) + RBAC.

« Client » = User de rôle « client ». Ces routes n'affectent que des produits
EXISTANTS ; aucune création de produit ici. Contrat POST :
`{"items": [{"product_id": "...", "qte": N}]}` (`qte` >= 1, défaut 1).
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.models.product import Product
from conftest import auth_headers as _auth_headers
from conftest import create_and_login

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


@pytest_asyncio.fixture
async def cleanup_products(db_session):
    yield
    await db_session.execute(delete(Product).where(Product.reference.like("REF-%")))
    await db_session.commit()


async def _make_product(client, staff_token: str, **overrides) -> str:
    payload = {"reference": f"REF-{uuid.uuid4().hex[:8]}", "name": "Imprimante"}
    payload.update(overrides)
    resp = await client.post("/api/v1/products/", json=payload, headers=_auth_headers(staff_token))
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _items(*pairs):
    """(product_id, qte) -> payload items ; qte omise si None."""
    out = []
    for pid, qte in pairs:
        item = {"product_id": pid}
        if qte is not None:
            item["qte"] = qte
        out.append(item)
    return {"items": out}


async def _assign(client, token, client_id, *pairs):
    return await client.post(
        f"/api/v1/clients/{client_id}/products", json=_items(*pairs), headers=_auth_headers(token)
    )


# --- 401 -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_client_products_without_token_is_401(client):
    resp = await client.get(f"/api/v1/clients/{uuid.uuid4()}/products")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_assign_client_products_without_token_is_401(client):
    resp = await client.post(
        f"/api/v1/clients/{uuid.uuid4()}/products", json=_items((str(uuid.uuid4()), 1))
    )
    assert resp.status_code == 401


# --- GET : self client / staff / 403 / 404 -------------------------------


@pytest.mark.asyncio
async def test_client_lists_own_products_empty(client, actors):
    client_user, client_token = actors["client"]
    resp = await client.get(f"/api/v1/clients/{client_user.id}/products", headers=_auth_headers(client_token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_staff_can_list_client_products_with_qte(client, actors, cleanup_products):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]
    product_id = await _make_product(client, responsable_token)
    await _assign(client, responsable_token, client_user.id, (product_id, 5))

    resp = await client.get(
        f"/api/v1/clients/{client_user.id}/products", headers=_auth_headers(responsable_token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [p["id"] for p in body] == [product_id]
    assert body[0]["qte"] == 5


@pytest.mark.asyncio
async def test_client_cannot_list_another_clients_products_is_403(client, actors, db_session, role_ids):
    _, client_token = actors["client"]
    other_client, _ = await create_and_login(client, db_session, role_id=role_ids["client"])

    resp = await client.get(
        f"/api/v1/clients/{other_client.id}/products", headers=_auth_headers(client_token)
    )
    assert resp.status_code == 403

    await db_session.delete(other_client)
    await db_session.commit()


@pytest.mark.asyncio
async def test_list_products_for_non_client_user_is_404(client, actors):
    technicien, _ = actors["technicien"]
    _, responsable_token = actors["responsable"]

    resp = await client.get(
        f"/api/v1/clients/{technicien.id}/products", headers=_auth_headers(responsable_token)
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_products_for_unknown_client_is_404(client, actors):
    _, responsable_token = actors["responsable"]
    resp = await client.get(f"/api/v1/clients/{UNKNOWN_ID}/products", headers=_auth_headers(responsable_token))
    assert resp.status_code == 404


# --- POST : RBAC -------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("actor_key", ["responsable", "admin", "super_admin"])
async def test_staff_can_assign_products(client, actors, cleanup_products, actor_key):
    client_user, _ = actors["client"]
    _, staff_token = actors[actor_key]
    p1 = await _make_product(client, staff_token)
    p2 = await _make_product(client, staff_token)

    resp = await _assign(client, staff_token, client_user.id, (p1, 2), (p2, None))
    assert resp.status_code == 200
    by_id = {p["id"]: p["qte"] for p in resp.json()}
    assert by_id == {p1: 2, p2: 1}  # p2 : qte par défaut


@pytest.mark.asyncio
@pytest.mark.parametrize("actor_key", ["client", "technicien"])
async def test_non_staff_cannot_assign_products(client, actors, cleanup_products, actor_key):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]
    _, token = actors[actor_key]
    product_id = await _make_product(client, responsable_token)

    resp = await _assign(client, token, client_user.id, (product_id, 1))
    assert resp.status_code == 403


# --- POST : cas métier -----------------------------------------------------


@pytest.mark.asyncio
async def test_assign_merges_duplicates_and_updates_qte_on_reassign(client, actors, cleanup_products):
    client_user, client_token = actors["client"]
    _, responsable_token = actors["responsable"]
    product_id = await _make_product(client, responsable_token)

    # doublons dans la requête : dernière quantité gagnante
    first = await _assign(client, responsable_token, client_user.id, (product_id, 3), (product_id, 8))
    assert first.status_code == 200
    assert [(p["id"], p["qte"]) for p in first.json()] == [(product_id, 8)]

    # réaffectation du même produit : la quantité est MISE À JOUR (upsert)
    second = await _assign(client, responsable_token, client_user.id, (product_id, 2))
    assert second.status_code == 200
    assert [(p["id"], p["qte"]) for p in second.json()] == [(product_id, 2)]

    listed = await client.get(
        f"/api/v1/clients/{client_user.id}/products", headers=_auth_headers(client_token)
    )
    assert [(p["id"], p["qte"]) for p in listed.json()] == [(product_id, 2)]


@pytest.mark.asyncio
async def test_assign_qte_zero_is_422(client, actors):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    resp = await _assign(client, responsable_token, client_user.id, (str(uuid.uuid4()), 0))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_assign_unknown_product_is_404_and_writes_nothing(client, actors, cleanup_products):
    client_user, client_token = actors["client"]
    _, responsable_token = actors["responsable"]
    real_product = await _make_product(client, responsable_token)

    resp = await _assign(client, responsable_token, client_user.id, (real_product, 1), (UNKNOWN_ID, 1))
    assert resp.status_code == 404

    listed = await client.get(
        f"/api/v1/clients/{client_user.id}/products", headers=_auth_headers(client_token)
    )
    assert listed.json() == []  # rien écrit : transaction annulée


@pytest.mark.asyncio
async def test_assign_to_unknown_client_is_404(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    product_id = await _make_product(client, responsable_token)

    resp = await _assign(client, responsable_token, UNKNOWN_ID, (product_id, 1))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_assign_to_non_client_user_is_404(client, actors, cleanup_products):
    technicien, _ = actors["technicien"]
    _, responsable_token = actors["responsable"]
    product_id = await _make_product(client, responsable_token)

    resp = await _assign(client, responsable_token, technicien.id, (product_id, 1))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_assign_empty_items_is_422(client, actors):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]

    resp = await client.post(
        f"/api/v1/clients/{client_user.id}/products",
        json={"items": []},
        headers=_auth_headers(responsable_token),
    )
    assert resp.status_code == 422


# --- DELETE --------------------------------------------------------------


@pytest.mark.asyncio
async def test_staff_can_unassign_product(client, actors, cleanup_products):
    client_user, client_token = actors["client"]
    _, responsable_token = actors["responsable"]
    product_id = await _make_product(client, responsable_token)
    await _assign(client, responsable_token, client_user.id, (product_id, 4))

    resp = await client.delete(
        f"/api/v1/clients/{client_user.id}/products/{product_id}",
        headers=_auth_headers(responsable_token),
    )
    assert resp.status_code == 204

    listed = await client.get(
        f"/api/v1/clients/{client_user.id}/products", headers=_auth_headers(client_token)
    )
    assert listed.json() == []


@pytest.mark.asyncio
async def test_unassign_not_assigned_product_is_404(client, actors, cleanup_products):
    client_user, _ = actors["client"]
    _, responsable_token = actors["responsable"]
    product_id = await _make_product(client, responsable_token)

    resp = await client.delete(
        f"/api/v1/clients/{client_user.id}/products/{product_id}",
        headers=_auth_headers(responsable_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_client_cannot_unassign_product_is_403(client, actors, cleanup_products):
    client_user, client_token = actors["client"]
    _, responsable_token = actors["responsable"]
    product_id = await _make_product(client, responsable_token)
    await _assign(client, responsable_token, client_user.id, (product_id, 1))

    resp = await client.delete(
        f"/api/v1/clients/{client_user.id}/products/{product_id}",
        headers=_auth_headers(client_token),
    )
    assert resp.status_code == 403


__all__: list[str] = []
