"""Routes de consultation des garanties produit (CDC semaine 6 : API Garanties).

Option A validée : la garantie est une propriété statique de
`Product.warranty_months`, pas une garantie par instance. Lecture ouverte à
tout utilisateur authentifié — même permission que la lecture des produits
(`api/products.py`), puisqu'aucune nouvelle donnée n'est introduite.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.schemas.product import ProductWarrantyRead
from app.services.warranty_service import WarrantyService


router = APIRouter(prefix="/warranties", tags=["Warranties"])


async def get_warranty_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> WarrantyService:
    """Fournit un WarrantyService lié à la session de la requête (même pattern que `get_product_service`)."""

    return WarrantyService(db)


@router.get("/status", status_code=status.HTTP_200_OK)
async def warranties_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "Warranty routes are ready"}


@router.get("/{product_id}", response_model=ProductWarrantyRead, status_code=status.HTTP_200_OK)
async def get_product_warranty(
    product_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    warranty_service: Annotated[WarrantyService, Depends(get_warranty_service)],
) -> ProductWarrantyRead:
    """Retourne la garantie d'un produit (lecture ouverte à tout utilisateur authentifié)."""

    try:
        return await warranty_service.get_warranty(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


__all__ = ["router", "get_warranty_service"]
