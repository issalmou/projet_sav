"""Routes de gestion des produits.

Le module expose uniquement des points d'entrée HTTP préparatoires.
La logique métier et les services seront ajoutés dans une phase suivante.
"""
from fastapi import APIRouter, status


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/status", status_code=status.HTTP_200_OK)
async def products_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "Product routes are ready"}


@router.get("/", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def list_products_placeholder() -> dict[str, str]:
    """Point d'entrée préparé pour lister les produits."""

    return {"detail": "Listing products will be implemented in a later phase"}


@router.get("/{product_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_product_placeholder(product_id: str) -> dict[str, str]:
    """Point d'entrée préparé pour récupérer un produit par identifiant."""

    return {"detail": f"Product {product_id} will be implemented in a later phase"}


@router.post("/", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_product_placeholder() -> dict[str, str]:
    """Point d'entrée préparé pour créer un produit."""

    return {"detail": "Creating products will be implemented in a later phase"}


__all__ = ["router"]