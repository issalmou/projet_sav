"""Services liés aux produits (CDC semaine 6 : API Produits)."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    """Orchestrateur métier pour les produits."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_products(self) -> list[Product]:
        """Liste tous les produits (catalogue partagé, pas de filtrage par utilisateur)."""

        result = await self.session.execute(select(Product).order_by(Product.name))
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
