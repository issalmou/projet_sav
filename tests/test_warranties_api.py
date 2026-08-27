"""Tests HTTP de api/warranties.py : API Garanties (CDC semaine 6, Option A validée).

Option A : la garantie est une propriété statique de `Product.warranty_months`
— pas de garantie par instance, pas de date d'achat/expiration.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.models.product import Product
from conftest import auth_headers as _auth_headers

UNKNOWN_PRODUCT_ID = "00000000-0000-0000-0000-000000000000"


def _product_payload(**overrides) -> dict:
    payload = {"reference": f"REF-WAR-{uuid.uuid4().hex[:8]}", "name": "Pompe à chaleur", "warranty_months": 24}
    payload.update(overrides)
    return payload


@pytest_asyncio.fixture
async def cleanup_products(db_session):
    yield
    await db_session.execute(delete(Product).where(Product.reference.like("REF-WAR-%")))
    await db_session.commit()


@pytest.mark.asyncio
async def test_status_route_requires_no_authentication(client):
    response = await client.get("/api/v1/warranties/status")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_warranty_without_token_is_401(client):
    response = await client.get(f"/api/v1/warranties/{uuid.uuid4()}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_client_can_read_warranty_of_existing_product(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    _, client_token = actors["client"]
    created = await client.post(
        "/api/v1/products/", json=_product_payload(), headers=_auth_headers(responsable_token)
    )
    product_id = created.json()["id"]

    response = await client.get(f"/api/v1/warranties/{product_id}", headers=_auth_headers(client_token))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == product_id
    assert body["warranty_months"] == 24


@pytest.mark.asyncio
async def test_warranty_reflects_null_warranty_months(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    created = await client.post(
        "/api/v1/products/",
        json=_product_payload(warranty_months=None),
        headers=_auth_headers(responsable_token),
    )
    product_id = created.json()["id"]

    response = await client.get(f"/api/v1/warranties/{product_id}", headers=_auth_headers(responsable_token))

    assert response.status_code == 200
    assert response.json()["warranty_months"] is None


@pytest.mark.asyncio
async def test_get_warranty_of_unknown_product_is_404(client, actors):
    _, client_token = actors["client"]

    response = await client.get(f"/api/v1/warranties/{UNKNOWN_PRODUCT_ID}", headers=_auth_headers(client_token))

    assert response.status_code == 404


# --- Modification : réservée à ADMIN/RESPONSABLE_SAV ------------------------


@pytest.mark.asyncio
async def test_update_warranty_without_token_is_401(client):
    response = await client.patch(f"/api/v1/warranties/{uuid.uuid4()}", json={"warranty_months": 12})

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("actor_key", ["admin", "responsable"])
async def test_staff_can_update_warranty(client, actors, actor_key, cleanup_products):
    _, responsable_token = actors["responsable"]
    _, actor_token = actors[actor_key]
    created = await client.post(
        "/api/v1/products/", json=_product_payload(), headers=_auth_headers(responsable_token)
    )
    product_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/warranties/{product_id}", json={"warranty_months": 36}, headers=_auth_headers(actor_token)
    )

    assert response.status_code == 200
    assert response.json()["warranty_months"] == 36


@pytest.mark.asyncio
@pytest.mark.parametrize("actor_key", ["client", "technicien"])
async def test_non_staff_cannot_update_warranty(client, actors, actor_key, cleanup_products):
    _, responsable_token = actors["responsable"]
    _, actor_token = actors[actor_key]
    created = await client.post(
        "/api/v1/products/", json=_product_payload(), headers=_auth_headers(responsable_token)
    )
    product_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/warranties/{product_id}", json={"warranty_months": 36}, headers=_auth_headers(actor_token)
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_unknown_product_warranty_as_staff_is_404(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.patch(
        f"/api/v1/warranties/{UNKNOWN_PRODUCT_ID}",
        json={"warranty_months": 12},
        headers=_auth_headers(responsable_token),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_warranty_with_negative_value_is_422(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    created = await client.post(
        "/api/v1/products/", json=_product_payload(), headers=_auth_headers(responsable_token)
    )
    product_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/warranties/{product_id}", json={"warranty_months": -1}, headers=_auth_headers(responsable_token)
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_warranty_with_missing_field_is_422(client, actors, cleanup_products):
    _, responsable_token = actors["responsable"]
    created = await client.post(
        "/api/v1/products/", json=_product_payload(), headers=_auth_headers(responsable_token)
    )
    product_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/warranties/{product_id}", json={}, headers=_auth_headers(responsable_token)
    )

    assert response.status_code == 422


# --- Suppression : réservée à ADMIN/RESPONSABLE_SAV --------------------------


@pytest.mark.asyncio
async def test_delete_warranty_without_token_is_401(client):
    response = await client.delete(f"/api/v1/warranties/{uuid.uuid4()}")

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("actor_key", ["admin", "responsable"])
async def test_staff_can_delete_warranty(client, actors, actor_key, cleanup_products):
    _, responsable_token = actors["responsable"]
    _, actor_token = actors[actor_key]
    created = await client.post(
        "/api/v1/products/", json=_product_payload(), headers=_auth_headers(responsable_token)
    )
    product_id = created.json()["id"]

    response = await client.delete(f"/api/v1/warranties/{product_id}", headers=_auth_headers(actor_token))

    assert response.status_code == 200
    assert response.json()["warranty_months"] is None

    get_response = await client.get(f"/api/v1/warranties/{product_id}", headers=_auth_headers(actor_token))
    assert get_response.json()["warranty_months"] is None

    product_response = await client.get(f"/api/v1/products/{product_id}", headers=_auth_headers(actor_token))
    assert product_response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("actor_key", ["client", "technicien"])
async def test_non_staff_cannot_delete_warranty(client, actors, actor_key, cleanup_products):
    _, responsable_token = actors["responsable"]
    _, actor_token = actors[actor_key]
    created = await client.post(
        "/api/v1/products/", json=_product_payload(), headers=_auth_headers(responsable_token)
    )
    product_id = created.json()["id"]

    response = await client.delete(f"/api/v1/warranties/{product_id}", headers=_auth_headers(actor_token))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_unknown_product_warranty_as_staff_is_404(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.delete(
        f"/api/v1/warranties/{UNKNOWN_PRODUCT_ID}", headers=_auth_headers(responsable_token)
    )

    assert response.status_code == 404


__all__: list[str] = []
