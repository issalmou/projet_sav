"""Service de garantie produit (CDC semaine 6 : API Garanties).

Option A validée : la garantie est une propriété statique du produit
(`Product.warranty_months`), pas une instance liée à un achat (pas de date
d'achat/expiration, pas de relation client-produit). Réutilise
`ProductService` pour la recherche du produit, sans dupliquer sa logique.
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.services.product_service import ProductService


class WarrantyService:
    """Orchestrateur pour la consultation de la garantie d'un produit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._product_service = ProductService(session)

    async def get_warranty(self, product_id: UUID) -> Product:
        """Retourne le produit (dont `warranty_months`) ou lève `ValueError` (404)."""

        return await self._product_service.get_product(product_id)

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


__all__ = ["WarrantyService"]
