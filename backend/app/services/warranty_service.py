"""Service de garantie produit (CDC semaine 6 : API Garanties).

La garantie est une propriété statique du produit (`Product.warranty_months`),
pas une garantie par instance. Un produit est « affecté » à un client lorsqu'il
apparaît dans un de ses tickets (`Ticket.created_by_id` + `Ticket.product_id`).
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.ticket import Ticket
from app.services.product_service import ProductService


class WarrantyService:
    """Orchestrateur pour la consultation et la gestion de la garantie d'un produit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._product_service = ProductService(session)

    async def get_warranty(self, product_id: UUID) -> Product:
        """Retourne le produit (dont `warranty_months`) ou lève `ValueError` (404)."""

        product = await self._product_service.get_product(product_id)
        if product is None:
            raise ValueError("Product not found")
        return product

    async def is_assigned_to_client(self, product_id: UUID, client_id: UUID) -> bool:
        """Vrai si le produit est affecté au client, c'est-à-dire présent dans un de ses tickets."""

        ticket_id = await self._session.scalar(
            select(Ticket.id)
            .where(Ticket.created_by_id == client_id, Ticket.product_id == product_id)
            .limit(1)
        )
        return ticket_id is not None

    async def update_warranty(self, product_id: UUID, warranty_months: int) -> Product:
        """Met à jour `warranty_months` du produit. Lève `ValueError` (404) s'il n'existe pas."""

        return await self._set_warranty_months(product_id, warranty_months)

    async def delete_warranty(self, product_id: UUID) -> Product:
        """Supprime la garantie d'un produit (remet `warranty_months` à `None`).

        Le produit lui-même n'est pas supprimé.
        """

        return await self._set_warranty_months(product_id, None)

    async def _set_warranty_months(self, product_id: UUID, warranty_months: int | None) -> Product:
        product = await self.get_warranty(product_id)
        product.warranty_months = warranty_months
        await self._session.commit()
        await self._session.refresh(product)
        return product


__all__ = ["WarrantyService"]