"""Service de garantie catalogue et de garantie client."""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.client_product import ClientProduct
from app.services.product_service import ProductService


@dataclass(frozen=True)
class WarrantyResult:
    product: Product
    purchase_date: date | None
    warranty_months: int | None
    warranty_end_date: date | None
    status: str


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(start.day, monthrange(year, month)[1]))


class WarrantyService:
    """Orchestrateur pour la consultation de la garantie d'un produit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._product_service = ProductService(session)

    async def get_warranty(self, product_id: UUID) -> Product:
        """Retourne le produit (dont `warranty_months`) ou lève `ValueError` (404)."""

        return await self._product_service.get_product(product_id)

    async def get_client_warranty(self, client_id: UUID, product_id: UUID, *, today: date | None = None) -> WarrantyResult:
        product = await self._product_service.get_product(product_id)
        result = await self._session.execute(
            select(ClientProduct).where(
                ClientProduct.user_id == client_id,
                ClientProduct.product_id == product_id,
            )
        )
        link = result.scalar_one_or_none()
        if link is None:
            raise ValueError("This product is not assigned to the client")
        purchase_date = link.purchase_date
        if purchase_date is None:
            return WarrantyResult(product, None, product.warranty_months, None, "UNKNOWN")
        if product.warranty_months is None:
            return WarrantyResult(product, purchase_date, None, None, "UNKNOWN")

        warranty_end_date = _add_months(purchase_date, product.warranty_months)
        return WarrantyResult(
            product,
            purchase_date,
            product.warranty_months,
            warranty_end_date,
            "ACTIVE" if (today or date.today()) < warranty_end_date else "EXPIRED",
        )

    async def update_warranty(self, product_id: UUID, warranty_months: int) -> Product:
        """Met à jour `warranty_months` du produit. Lève `ValueError` (404) s'il n'existe pas."""

        return await self._set_warranty_months(product_id, warranty_months)

    async def delete_warranty(self, product_id: UUID) -> Product:
        """Supprime la garantie d'un produit (remet `warranty_months` à `None`).

        Le produit lui-même n'est pas supprimé (Option A : la garantie n'est
        pas une entité séparée, cf. en-tête de module).
        """

        return await self._set_warranty_months(product_id, None)

    async def _set_warranty_months(self, product_id: UUID, warranty_months: int | None) -> Product:
        product = await self._product_service.get_product(product_id)
        product.warranty_months = warranty_months
        await self._session.commit()
        await self._session.refresh(product)
        return product


__all__ = ["WarrantyResult", "WarrantyService", "_add_months"]
