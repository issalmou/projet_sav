"""Services liés aux produits (CDC semaine 6 : API Produits)."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    """Orchestrateur métier pour les produits."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_products(self, limit: int = 50, offset: int = 0) -> list[Product]:
        """Liste les produits (catalogue partagé, pas de filtrage par utilisateur).

        Pagination simple (`limit`/`offset`), même pattern que `UserService.list_users`.
        """

        query = select(Product).order_by(Product.name).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_product(self, product_id: UUID) -> Product:
        """Retourne un produit par identifiant, sinon lève `ValueError` (404)."""

        product = await self.session.get(Product, product_id)
        if product is None:
            raise ValueError("Product not found")
        return product

    async def get_product_by_reference(self, reference: str) -> Product | None:
        """Retourne un produit par référence, ou `None` (utilisé pour la contrainte d'unicité)."""

        result = await self.session.execute(select(Product).where(Product.reference == reference))
        return result.scalar_one_or_none()

    async def get_product_by_name(self, name: str) -> Product | None:
        """Retourne un produit par nom (correspondance exacte, insensible à la casse).

        Utilisé par DiagnosticService pour résoudre un produit identifié par le
        LLM (RAG) sans jamais deviner : retourne `None` si aucun produit ne
        correspond, ou si plusieurs produits partagent le même nom (`name`
        n'est pas contraint à l'unicité, contrairement à `reference`) — mieux
        vaut ne pas trancher que de risquer une correspondance incorrecte.
        """

        result = await self.session.execute(select(Product).where(func.lower(Product.name) == name.strip().lower()))
        matches = list(result.scalars().all())
        return matches[0] if len(matches) == 1 else None

    async def create_product(self, data: ProductCreate) -> Product:
        """Crée un produit. Lève `ValueError` si la référence existe déjà (même principe que UserService.create_user)."""

        if await self.get_product_by_reference(data.reference) is not None:
            raise ValueError("A product with this reference already exists")

        product = Product(**data.model_dump())
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def update_product(self, product_id: UUID, data: ProductUpdate) -> Product:
        """Met à jour partiellement un produit. Lève `ValueError` (404) s'il n'existe pas."""

        product = await self.get_product(product_id)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def delete_product(self, product_id: UUID) -> None:
        """Supprime un produit. Lève `ValueError` (404) s'il n'existe pas.

        Sans risque référentiel : `DocumentProduct` est en CASCADE et
        `Ticket.product_id` en SET NULL (aucune contrainte RESTRICT).
        """

        product = await self.get_product(product_id)
        await self.session.delete(product)
        await self.session.commit()


__all__ = ["ProductService"]
