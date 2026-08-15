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
        self._product_service = ProductService(session)

    async def get_warranty(self, product_id: UUID) -> Product:
        """Retourne le produit (dont `warranty_months`) ou lève `ValueError` (404)."""

        return await self._product_service.get_product(product_id)


__all__ = ["WarrantyService"]
