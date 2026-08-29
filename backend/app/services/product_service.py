"""Services CRUD pour les produits persistés."""
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product


class ProductService:
    """Orchestrateur métier pour les produits."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_products(self, *, limit: int = 50, offset: int = 0, category: str | None = None, search: str | None = None) -> list[Product]:
        query = select(Product).order_by(Product.created_at.desc()).limit(limit).offset(offset)
        if category:
            query = query.where(Product.category == category)
        if search:
            term = f"%{search}%"
            query = query.where(Product.name.ilike(term) | Product.reference.ilike(term) | Product.description.ilike(term))
        return list((await self.session.scalars(query)).all())

    async def get_product(self, product_id: UUID) -> Product | None:
        return await self.session.get(Product, product_id)

    async def create_product(self, payload: object) -> Product:
        product = Product(**payload.model_dump())
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def update_product(self, product_id: UUID, payload: object) -> Product | None:
        product = await self.get_product(product_id)
        if product is None:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(product, key, value)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def delete_product(self, product_id: UUID) -> None:
        await self.session.execute(delete(Product).where(Product.id == product_id))
        await self.session.commit()


__all__ = ["ProductService"]
