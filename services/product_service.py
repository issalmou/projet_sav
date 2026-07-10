"""Services liés aux produits.

Ce module prépare la couche métier produit sans implémenter les opérations
CRUD complètes à ce stade de fondation.
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class ProductService:
    """Orchestrateur métier pour les produits."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_products(self) -> list[object]:
        """Prévu pour retourner la liste des produits."""

        raise NotImplementedError("Product listing will be implemented later")

    async def get_product(self, product_id: UUID) -> object:
        """Prévu pour retourner un produit par identifiant."""

        raise NotImplementedError("Product retrieval will be implemented later")

    async def create_product(self, payload: object) -> object:
        """Prévu pour créer un produit."""

        raise NotImplementedError("Product creation will be implemented later")

    async def update_product(self, product_id: UUID, payload: object) -> object:
        """Prévu pour mettre à jour un produit."""

        raise NotImplementedError("Product update will be implemented later")

    async def delete_product(self, product_id: UUID) -> None:
        """Prévu pour supprimer un produit."""

        raise NotImplementedError("Product deletion will be implemented later")


__all__ = ["ProductService"]