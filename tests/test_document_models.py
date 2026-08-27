"""Tests du modèle Document et de l'association DocumentProduct (semaine 4, tâche 1)."""
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.document import Document, DocumentProduct
from app.models.product import Product


def _new_document(created_by_id: uuid.UUID, **overrides) -> Document:
    defaults = dict(
        title="Guide erreur E17",
        file_type="pdf",
        category="manuals",
        file_name="guide-e17.pdf",
        file_path="uploads/guide-e17.pdf",
        file_size=1024,
        created_by_id=created_by_id,
    )
    defaults.update(overrides)
    return Document(**defaults)


@pytest.mark.asyncio
async def test_create_general_document_without_product(db_session, sav_user):
    """Un document sans ligne DocumentProduct associée est considéré comme général."""

    document = _new_document(sav_user.id)
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document, attribute_names=["products"])

    assert document.products == []
    assert document.status == "draft"
    assert document.created_by_id == sav_user.id

    # `created_by_id` est protégé en RESTRICT : nettoyer le document avant que
    # la fixture `sav_user` ne supprime son créateur.
    await db_session.delete(document)
    await db_session.commit()


@pytest.mark.asyncio
async def test_document_can_be_linked_to_multiple_products(db_session, sav_user, product):
    """Un document peut concerner plusieurs produits (relation plusieurs-à-plusieurs)."""

    second_product = Product(reference=f"REF-{uuid.uuid4().hex[:8]}", name="Scanner Test")
    db_session.add(second_product)
    await db_session.flush()

    document = _new_document(sav_user.id, title="Notice multi-produits")
    document.products = [product, second_product]
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document, attribute_names=["products"])

    assert {p.id for p in document.products} == {product.id, second_product.id}

    await db_session.delete(document)
    await db_session.delete(second_product)
    await db_session.commit()


@pytest.mark.asyncio
async def test_deleting_document_cascades_to_document_products_but_not_product(db_session, sav_user, product):
    """La suppression d'un document supprime son association, sans supprimer le produit."""

    document = _new_document(sav_user.id, title="Notice liée")
    document.products = [product]
    db_session.add(document)
    await db_session.commit()

    document_id = document.id
    await db_session.delete(document)
    await db_session.commit()

    links = await db_session.execute(select(DocumentProduct).where(DocumentProduct.document_id == document_id))
    assert links.scalars().all() == []

    still_there = await db_session.get(Product, product.id)
    assert still_there is not None


@pytest.mark.asyncio
async def test_duplicate_document_product_link_is_rejected_by_db(db_session, sav_user, product):
    """La même paire (document, produit) ne peut pas être liée deux fois."""

    document = _new_document(sav_user.id, title="Notice dupliquée")
    db_session.add(document)
    await db_session.flush()

    db_session.add(DocumentProduct(document_id=document.id, product_id=product.id))
    await db_session.commit()

    db_session.add(DocumentProduct(document_id=document.id, product_id=product.id))
    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()
    await db_session.delete(document)
    await db_session.commit()


@pytest.mark.parametrize(
    "field,value",
    [("file_type", "exe"), ("category", "unknown"), ("status", "deleted")],
)
@pytest.mark.asyncio
async def test_invalid_enum_like_fields_are_rejected_by_db(db_session, sav_user, field, value):
    """file_type / category / status sont contraints par des CHECK constraints en base."""

    document = _new_document(sav_user.id, title="Document invalide", **{field: value})
    db_session.add(document)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


__all__: list[str] = []
