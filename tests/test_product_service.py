"""Tests de ProductService (CDC semaine 6 : API Produits)."""
import uuid

import pytest
import pytest_asyncio

from app.schemas.product import ProductCreate, ProductUpdate
from app.services.product_service import ProductService


@pytest_asyncio.fixture
async def product_service(db_session):
    return ProductService(db_session)


def _payload(**overrides) -> ProductCreate:
    data = {"reference": f"REF-{uuid.uuid4().hex[:8]}", "name": "Four encastrable"}
    data.update(overrides)
    return ProductCreate(**data)


@pytest_asyncio.fixture
async def created_product(product_service):
    product = await product_service.create_product(_payload())

    yield product

    still_there = await product_service.session.get(type(product), product.id)
    if still_there is not None:
        await product_service.session.delete(still_there)
        await product_service.session.commit()


@pytest.mark.asyncio
async def test_create_product_succeeds(product_service):
    product = await product_service.create_product(_payload(reference="REF-CREATE-1", name="Pompe à chaleur"))

    assert product.reference == "REF-CREATE-1"
    assert product.name == "Pompe à chaleur"

    await product_service.session.delete(product)
    await product_service.session.commit()


@pytest.mark.asyncio
async def test_create_product_duplicate_reference_raises_value_error(product_service, created_product):
    with pytest.raises(ValueError):
        await product_service.create_product(_payload(reference=created_product.reference))


@pytest.mark.asyncio
async def test_list_products_returns_created_product(product_service, created_product):
    products = await product_service.list_products()

    assert any(p.id == created_product.id for p in products)


@pytest.mark.asyncio
async def test_get_product_returns_existing(product_service, created_product):
    fetched = await product_service.get_product(created_product.id)

    assert fetched.id == created_product.id


@pytest.mark.asyncio
async def test_get_unknown_product_raises_value_error(product_service):
    with pytest.raises(ValueError):
        await product_service.get_product(uuid.uuid4())


@pytest.mark.asyncio
async def test_update_product_modifies_fields(product_service, created_product):
    updated = await product_service.update_product(
        created_product.id, ProductUpdate(name="Nouveau nom", warranty_months=24)
    )

    assert updated.name == "Nouveau nom"
    assert updated.warranty_months == 24
    assert updated.reference == created_product.reference  # champ non fourni : inchangé


@pytest.mark.asyncio
async def test_update_unknown_product_raises_value_error(product_service):
    with pytest.raises(ValueError):
        await product_service.update_product(uuid.uuid4(), ProductUpdate(name="x"))


@pytest.mark.asyncio
async def test_delete_product_removes_it(product_service):
    product = await product_service.create_product(_payload(reference="REF-DELETE-1"))

    await product_service.delete_product(product.id)

    with pytest.raises(ValueError):
        await product_service.get_product(product.id)


@pytest.mark.asyncio
async def test_delete_unknown_product_raises_value_error(product_service):
    with pytest.raises(ValueError):
        await product_service.delete_product(uuid.uuid4())
