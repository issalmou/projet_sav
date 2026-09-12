"""Service d'affectation de produits (existants) à un client — table client_products.

Ni achat, ni commande, ni facture : ce service ne fait qu'associer des
produits DÉJÀ présents au catalogue à un utilisateur ayant le rôle
« client », avec une quantité (`qte >= 1`). La création / modification /
suppression d'un produit reste du ressort de `ProductService` (`/products`).

Règles d'accès (appliquées dans `api/clients.py`, RBAC existant) :
- affecter / retirer  : administrateur, responsable_sav, superuser ;
- consulter           : le client lui-même, ou le staff.
"""
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utcnow
from app.models.client_product import ClientProduct
from app.models.product import Product
from app.models.user import User
from app.schemas.client_product import ClientProductItem, ClientProductRead
from app.schemas.product import ProductRead
from app.utils.constants import RoleName


class ClientNotFoundError(ValueError):
    """`client_id` ne référence aucun utilisateur, ou un utilisateur sans le rôle « client ».

    Sous-classe de `ValueError` (comme les « introuvable » du reste du projet)
    → mappée sur 404 : la ressource `/clients/{id}` n'existe pas si `id` n'est
    pas un client.
    """


class ProductsNotFoundError(ValueError):
    """Au moins un `product_id` fourni ne correspond à aucun produit existant.

    Même convention que `DocumentService.ProductNotFoundError` → 404.
    """


class ClientProductService:
    """Orchestrateur métier pour l'affectation produit ↔ client."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_products(self, client_id: UUID) -> list[ClientProductRead]:
        """Liste les produits affectés à `client_id` (avec leur quantité, triés par nom)."""

        await self._get_client_or_raise(client_id)

        result = await self.session.execute(
            select(Product, ClientProduct.qte)
            .join(ClientProduct, ClientProduct.product_id == Product.id)
            .where(ClientProduct.user_id == client_id)
            .order_by(Product.name)
        )
        return [_to_read(product, qte) for product, qte in result.all()]

    async def assign_products(
        self, client_id: UUID, items: list[ClientProductItem]
    ) -> list[ClientProductRead]:
        """Affecte des produits EXISTANTS à `client_id` (upsert de la quantité).

        - `client_id` doit référencer un utilisateur ayant le rôle « client » ;
        - chaque `product_id` doit exister (sinon `ProductsNotFoundError`, rien n'est écrit) ;
        - les doublons de `product_id` dans la requête sont fusionnés (dernière quantité) ;
        - un produit déjà affecté voit sa `qte` **mise à jour** via
          `ON CONFLICT (user_id, product_id) DO UPDATE` — pas d'erreur, pas de
          course sur `uq_client_product`.
        Le tout dans une seule transaction (un seul `commit`).
        """

        await self._get_client_or_raise(client_id)

        # dédup par product_id, dernière quantité gagnante, ordre conservé
        merged: dict[UUID, int] = {}
        for item in items:
            merged[item.product_id] = item.qte
        product_ids = list(merged.keys())

        found = await self.session.execute(select(Product.id).where(Product.id.in_(product_ids)))
        found_ids = set(found.scalars().all())
        missing = [pid for pid in product_ids if pid not in found_ids]
        if missing:
            raise ProductsNotFoundError(
                "Unknown product id(s): " + ", ".join(str(pid) for pid in missing)
            )

        now = utcnow()
        rows = [
            {
                "id": uuid.uuid4(),
                "user_id": client_id,
                "product_id": pid,
                "qte": qte,
                "created_at": now,
                "updated_at": now,
            }
            for pid, qte in merged.items()
        ]
        stmt = pg_insert(ClientProduct.__table__).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "product_id"],
            set_={"qte": stmt.excluded.qte, "updated_at": stmt.excluded.updated_at},
        )
        await self.session.execute(stmt)
        await self.session.commit()

        return await self.list_products(client_id)

    async def unassign_product(self, client_id: UUID, product_id: UUID) -> None:
        """Retire l'affectation d'un produit à `client_id`.

        `ClientNotFoundError` (404) si `client_id` n'est pas un client,
        `ValueError` (404) si le produit n'est pas rattaché à ce client.
        """

        await self._get_client_or_raise(client_id)

        result = await self.session.execute(
            select(ClientProduct).where(
                ClientProduct.user_id == client_id, ClientProduct.product_id == product_id
            )
        )
        link = result.scalar_one_or_none()
        if link is None:
            raise ValueError("This product is not assigned to this client")

        await self.session.delete(link)
        await self.session.commit()

    async def is_assigned(self, client_id: UUID, product_id: UUID) -> bool:
        """Vrai si `product_id` est rattaché à `client_id` (utilisé par le workflow chat)."""

        result = await self.session.execute(
            select(ClientProduct.id).where(
                ClientProduct.user_id == client_id, ClientProduct.product_id == product_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def _get_client_or_raise(self, client_id: UUID) -> User:
        user = await self.session.get(User, client_id)
        if user is None or _role_name(user) != RoleName.CLIENT.value:
            raise ClientNotFoundError("Client not found")
        return user


def _to_read(product: Product, qte: int) -> ClientProductRead:
    return ClientProductRead(**ProductRead.model_validate(product).model_dump(), qte=qte)


def _role_name(user: User) -> str | None:
    return user.role.name if user.role else None


__all__ = ["ClientNotFoundError", "ClientProductService", "ProductsNotFoundError"]
