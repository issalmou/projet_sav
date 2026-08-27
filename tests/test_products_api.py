"""Tests HTTP de api/products.py : CRUD produits + RBAC (CDC semaine 6, tâche 2)."""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.models.product import Product
from conftest import auth_headers as _auth_headers

UNKNOWN_PRODUCT_ID = "00000000-0000-0000-0000-000000000000"


def _payload(**overrides) -> dict:
    payload = {"reference": f"REF-{uuid.uuid4().hex[:8]}", "name": "Chaudière à condensation"}
    payload.update(overrides)
    return payload


@pytest_asyncio.fixture
async def cleanup_products(db_session):
    """Nettoie les produits créés par le test (aucune contrainte RESTRICT ne bloque leur suppression)."""

    yield
    await db_session.execute(delete(Product).where(Product.reference.like("REF-%")))
    await db_session.commit()


@pytest.mark.asyncio
async def test_status_route_requires_no_authentication(client):
    response = await client.get("/api/v1/products/status")

    assert response.status_code == 200


# --- 401 : aucune authentification ----------------------------------------


@pytest.mark.asyncio
async def test_list_products_without_token_is_401(client):
    response = await client.get("/api/v1/products/")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_product_without_token_is_401(client):
    response = await client.get(f"/api/v1/products/{uuid.uuid4()}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_product_without_token_is_401(client):
    response = await client.post("/api/v1/products/", json=_payload())

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_product_without_token_is_401(client):
    response = await client.patch(f"/api/v1/products/{uuid.uuid4()}", json={"name": "x"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_product_without_token_is_401(client):
    response = await client.delete(f"/api/v1/products/{uuid.uuid4()}")

    assert response.status_code == 401


# --- Lecture : ouverte à tout utilisateur authentifié -----------------------


@pytest.mark.asyncio
async def test_client_can_list_products(client, actors, cleanup_products):
    _, client_token = actors["client"]
    await client.post("/api/v1/products/", json=_payload(), headers=_auth_headers(actors["responsable"][1]))

    response = await client.get("/api/v1/products/", headers=_auth_headers(client_token))

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_client_can_get_existing_product(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    _, client_token = actors["client"]
    created = await client.post("/api/v1/products/", json=_payload(), headers=_auth_headers(responsable_token))
    product_id = created.json()["id"]

    response = await client.get(f"/api/v1/products/{product_id}", headers=_auth_headers(client_token))

    assert response.status_code == 200
    assert response.json()["id"] == product_id


@pytest.mark.asyncio
async def test_get_unknown_product_is_404(client, actors):
    _, client_token = actors["client"]

    response = await client.get(f"/api/v1/products/{UNKNOWN_PRODUCT_ID}", headers=_auth_headers(client_token))

    assert response.status_code == 404


# --- Création : réservée au staff ------------------------------------------


@pytest.mark.asyncio
async def test_responsable_sav_can_create_product(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]

    response = await client.post("/api/v1/products/", json=_payload(), headers=_auth_headers(responsable_token))

    assert response.status_code == 201
    assert response.json()["reference"].startswith("REF-")


@pytest.mark.asyncio
async def test_administrateur_can_create_product(client, actors, cleanup_products):
    _, admin_token = actors["admin"]

    response = await client.post("/api/v1/products/", json=_payload(), headers=_auth_headers(admin_token))

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_super_admin_can_create_product(client, actors, cleanup_products):
    _, super_token = actors["super_admin"]

    response = await client.post("/api/v1/products/", json=_payload(), headers=_auth_headers(super_token))

    assert response.status_code == 201


@pytest.mark.asyncio
@pytest.mark.parametrize("actor_key", ["client", "technicien"])
async def test_non_staff_cannot_create_product(client, actors, actor_key):
    _, token = actors[actor_key]

    response = await client.post("/api/v1/products/", json=_payload(), headers=_auth_headers(token))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_product_invalid_payload_is_422(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.post(
        "/api/v1/products/", json={"reference": "", "name": ""}, headers=_auth_headers(responsable_token)
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_product_duplicate_reference_is_409(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    payload = _payload()
    await client.post("/api/v1/products/", json=payload, headers=_auth_headers(responsable_token))

    response = await client.post("/api/v1/products/", json=payload, headers=_auth_headers(responsable_token))

    assert response.status_code == 409


# --- Modification : réservée au staff --------------------------------------


@pytest.mark.asyncio
async def test_responsable_sav_can_update_product(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    created = await client.post("/api/v1/products/", json=_payload(), headers=_auth_headers(responsable_token))
    product_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/products/{product_id}", json={"name": "Nom mis à jour"}, headers=_auth_headers(responsable_token)
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Nom mis à jour"


@pytest.mark.asyncio
async def test_client_cannot_update_product(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    _, client_token = actors["client"]
    created = await client.post("/api/v1/products/", json=_payload(), headers=_auth_headers(responsable_token))
    product_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/products/{product_id}", json={"name": "x"}, headers=_auth_headers(client_token)
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_unknown_product_as_staff_is_404(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.patch(
        f"/api/v1/products/{UNKNOWN_PRODUCT_ID}", json={"name": "x"}, headers=_auth_headers(responsable_token)
    )

    assert response.status_code == 404


# --- Suppression : réservée au staff ----------------------------------------


@pytest.mark.asyncio
async def test_responsable_sav_can_delete_product(client, actors):
    _, responsable_token = actors["responsable"]
    created = await client.post("/api/v1/products/", json=_payload(), headers=_auth_headers(responsable_token))
    product_id = created.json()["id"]

    response = await client.delete(f"/api/v1/products/{product_id}", headers=_auth_headers(responsable_token))

    assert response.status_code == 204

    get_response = await client.get(f"/api/v1/products/{product_id}", headers=_auth_headers(responsable_token))
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_client_cannot_delete_product(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    _, client_token = actors["client"]
    created = await client.post("/api/v1/products/", json=_payload(), headers=_auth_headers(responsable_token))
    product_id = created.json()["id"]

    response = await client.delete(f"/api/v1/products/{product_id}", headers=_auth_headers(client_token))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_unknown_product_as_staff_is_404(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.delete(f"/api/v1/products/{UNKNOWN_PRODUCT_ID}", headers=_auth_headers(responsable_token))

    assert response.status_code == 404


# --- Pagination : GET /products (Semaine 7, Tâche 2) -------------------------
#
# Le catalogue produit est global (pas de scope par utilisateur, contrairement
# aux tickets) : la base de dev peut déjà contenir des produits avant le test.
# Les assertions ci-dessous utilisent donc un delta par rapport à un compte de
# référence (`_count_products`) plutôt qu'un total absolu, pour rester
# correctes quel que soit l'état préexistant du catalogue.


async def _count_products(client, headers: dict) -> int:
    response = await client.get("/api/v1/products/?limit=10000", headers=headers)
    return len(response.json())


@pytest.mark.asyncio
async def test_list_products_without_params_includes_created_products(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    headers = _auth_headers(responsable_token)
    created_ids = []
    for _ in range(3):
        response = await client.post("/api/v1/products/", json=_payload(), headers=headers)
        created_ids.append(response.json()["id"])

    response = await client.get("/api/v1/products/", headers=headers)

    assert response.status_code == 200
    listed_ids = [item["id"] for item in response.json()]
    assert set(created_ids).issubset(set(listed_ids))


@pytest.mark.asyncio
async def test_list_products_with_limit(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    headers = _auth_headers(responsable_token)
    for _ in range(3):
        await client.post("/api/v1/products/", json=_payload(), headers=headers)

    response = await client.get("/api/v1/products/?limit=2", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_list_products_with_offset(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    headers = _auth_headers(responsable_token)
    baseline = await _count_products(client, headers)
    for _ in range(3):
        await client.post("/api/v1/products/", json=_payload(), headers=headers)

    response = await client.get(f"/api/v1/products/?offset={baseline}&limit=10000", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_list_products_with_limit_and_offset(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    headers = _auth_headers(responsable_token)
    baseline = await _count_products(client, headers)
    for _ in range(5):
        await client.post("/api/v1/products/", json=_payload(), headers=headers)

    response = await client.get(f"/api/v1/products/?offset={baseline + 1}&limit=2", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_list_products_offset_beyond_total_is_empty_list(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    headers = _auth_headers(responsable_token)
    baseline = await _count_products(client, headers)

    response = await client.get(f"/api/v1/products/?offset={baseline + 1000}", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


__all__: list[str] = []
