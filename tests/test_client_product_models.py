"""Tests du modèle ClientProduct et de l'association client_products (Client ↔ Product).

Mêmes conventions que test_document_models.py : base PostgreSQL de dev, données
créées puis nettoyées, `client_id`/`user_id` en CASCADE donc la suppression du
User purge ses lignes client_products.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.client_product import ClientProduct
from app.models.product import Product
from app.models.user import User
from conftest import unique_email


def _new_product(**overrides) -> Product:
    defaults = dict(reference=f"REF-{uuid.uuid4().hex[:8]}", name="Imprimante Test")
    defaults.update(overrides)
    return Product(**defaults)


@pytest_asyncio.fixture
async def client_user(db_session):
    """Un utilisateur destiné à jouer le rôle de client dans l'association."""

    user = User(email=unique_email("clientprod"), hashed_password="x")
    db_session.add(user)
    await db_session.commit()
    user_id = user.id  # capturé avant le test : un rollback() y expirerait `user`

    yield user

    existing = await db_session.get(User, user_id)
    if existing is not None:
        await db_session.delete(existing)
        await db_session.commit()


@pytest.mark.asyncio
async def test_assign_existing_product_to_client(db_session, client_user, product):
    """Une ligne client_products rattache un produit existant à un client existant."""

    db_session.add(ClientProduct(user_id=client_user.id, product_id=product.id))
    await db_session.commit()

    await db_session.refresh(client_user, attribute_names=["assigned_products"])
    await db_session.refresh(product, attribute_names=["clients"])

    assert [p.id for p in client_user.assigned_products] == [product.id]
    assert [u.id for u in product.clients] == [client_user.id]


@pytest.mark.asyncio
async def test_qte_defaults_to_one(db_session, client_user, product):
    link = ClientProduct(user_id=client_user.id, product_id=product.id)
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)

    assert link.qte == 1

    await db_session.execute(ClientProduct.__table__.delete().where(ClientProduct.id == link.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_qte_can_be_set_explicitly(db_session, client_user, product):
    link = ClientProduct(user_id=client_user.id, product_id=product.id, qte=7)
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)

    assert link.qte == 7

    await db_session.execute(ClientProduct.__table__.delete().where(ClientProduct.id == link.id))
    await db_session.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_qte", [0, -3])
async def test_qte_below_one_is_rejected_by_db(db_session, client_user, product, bad_qte):
    """Contrainte CHECK `qte >= 1` : une affectation à 0 (ou négative) n'a pas de sens métier."""

    user_id, product_id = client_user.id, product.id
    db_session.add(ClientProduct(user_id=user_id, product_id=product_id, qte=bad_qte))
    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()
    await db_session.execute(
        ClientProduct.__table__.delete().where(
            ClientProduct.user_id == user_id, ClientProduct.product_id == product_id
        )
    )
    await db_session.commit()
    await db_session.refresh(client_user)
    await db_session.refresh(product)


@pytest.mark.asyncio
async def test_client_can_have_multiple_products(db_session, client_user, product):
    """Un même client peut être rattaché à plusieurs produits."""

    second_product = _new_product(name="Scanner Test")
    db_session.add(second_product)
    await db_session.flush()

    db_session.add_all(
        [
            ClientProduct(user_id=client_user.id, product_id=product.id),
            ClientProduct(user_id=client_user.id, product_id=second_product.id),
        ]
    )
    await db_session.commit()

    await db_session.refresh(client_user, attribute_names=["assigned_products"])
    assert {p.id for p in client_user.assigned_products} == {product.id, second_product.id}

    await db_session.execute(
        ClientProduct.__table__.delete().where(ClientProduct.product_id == second_product.id)
    )
    await db_session.delete(second_product)
    await db_session.commit()


@pytest.mark.asyncio
async def test_product_can_be_assigned_to_multiple_clients(db_session, client_user, product):
    """Un même produit peut être rattaché à plusieurs clients."""

    other_user = User(email=unique_email("clientprod2"), hashed_password="x")
    db_session.add(other_user)
    await db_session.flush()
    other_user_id = other_user.id

    db_session.add_all(
        [
            ClientProduct(user_id=client_user.id, product_id=product.id),
            ClientProduct(user_id=other_user_id, product_id=product.id),
        ]
    )
    await db_session.commit()

    await db_session.refresh(product, attribute_names=["clients"])
    assert {u.id for u in product.clients} == {client_user.id, other_user_id}

    # other_user n'est pas géré par une fixture : le supprimer purge sa ligne
    # client_products (CASCADE) sans toucher au produit ni à client_user.
    await db_session.delete(await db_session.get(User, other_user_id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_duplicate_client_product_pair_is_rejected_by_db(db_session, client_user, product):
    """La même paire (user, produit) ne peut pas être liée deux fois (uq_client_product)."""

    user_id, product_id = client_user.id, product.id

    db_session.add(ClientProduct(user_id=user_id, product_id=product_id))
    await db_session.commit()

    db_session.add(ClientProduct(user_id=user_id, product_id=product_id))
    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()

    # `rollback()` expire les instances ORM des fixtures (product/client_user),
    # dont les teardowns lisent `.id` de façon synchrone : on nettoie la ligne
    # créée, on termine sur un commit et on rafraîchit ces instances.
    await db_session.execute(
        ClientProduct.__table__.delete().where(
            ClientProduct.user_id == user_id, ClientProduct.product_id == product_id
        )
    )
    await db_session.commit()
    await db_session.refresh(client_user)
    await db_session.refresh(product)


@pytest.mark.asyncio
async def test_deleting_client_cascades_to_association_but_not_product(db_session, client_user, product):
    """Supprimer le client supprime la ligne client_products, jamais le produit."""

    db_session.add(ClientProduct(user_id=client_user.id, product_id=product.id))
    await db_session.commit()

    user_id = client_user.id
    await db_session.delete(client_user)
    await db_session.commit()

    links = await db_session.execute(select(ClientProduct).where(ClientProduct.user_id == user_id))
    assert links.scalars().all() == []

    assert await db_session.get(Product, product.id) is not None


@pytest.mark.asyncio
async def test_deleting_product_cascades_to_association_but_not_client(db_session, client_user):
    """Supprimer le produit supprime la ligne client_products, jamais le client."""

    disposable_product = _new_product(name="Produit jetable")
    db_session.add(disposable_product)
    await db_session.flush()
    product_id = disposable_product.id

    db_session.add(ClientProduct(user_id=client_user.id, product_id=product_id))
    await db_session.commit()

    await db_session.delete(await db_session.get(Product, product_id))
    await db_session.commit()

    links = await db_session.execute(select(ClientProduct).where(ClientProduct.product_id == product_id))
    assert links.scalars().all() == []

    assert await db_session.get(User, client_user.id) is not None


__all__: list[str] = []
