"""Routes de gestion des garanties produit (CDC semaine 6 : API Garanties).

Option A validée : la garantie est une propriété statique de
`Product.warranty_months`, pas une garantie par instance. Lecture ouverte à
tout utilisateur authentifié — même permission que la lecture des produits
(`api/products.py`), puisqu'aucune nouvelle donnée n'est introduite.
Modification et suppression réservées au staff (`STAFF_ROLES`), même
principe que `api/products.py`.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.core.permissions import STAFF_ROLES, require_roles
from app.models.user import User
from app.schemas.product import ProductWarrantyRead, WarrantyUpdate
from app.services.warranty_service import WarrantyService


router = APIRouter(prefix="/warranties", tags=["Warranties"])


async def get_warranty_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> WarrantyService:
    """Fournit un WarrantyService lié à la session de la requête (même pattern que `get_product_service`)."""

    return WarrantyService(db)


@router.get("/status", status_code=status.HTTP_200_OK)
async def warranties_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "Warranty routes are ready"}


@router.get(
    "/{product_id}",
    response_model=ProductWarrantyRead,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Ce compte utilisateur a été désactivé."},
        404: {"description": "Produit introuvable."},
    },
)
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


@router.patch(
    "/{product_id}",
    response_model=ProductWarrantyRead,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé à administrateur/responsable_sav)."},
        404: {"description": "Produit introuvable."},
        422: {"description": "warranty_months manquant ou négatif."},
    },
)
async def update_product_warranty(
    product_id: UUID,
    payload: WarrantyUpdate,
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    warranty_service: Annotated[WarrantyService, Depends(get_warranty_service)],
) -> ProductWarrantyRead:
    """Met à jour la garantie d'un produit (réservé à ADMINISTRATEUR/RESPONSABLE_SAV)."""

    try:
        return await warranty_service.update_warranty(product_id, payload.warranty_months)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/{product_id}",
    response_model=ProductWarrantyRead,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé à administrateur/responsable_sav)."},
        404: {"description": "Produit introuvable."},
    },
)
async def delete_product_warranty(
    product_id: UUID,
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    warranty_service: Annotated[WarrantyService, Depends(get_warranty_service)],
) -> ProductWarrantyRead:
    """Supprime la garantie d'un produit, c'est-à-dire remet `warranty_months` à `None`.

    Le produit n'est pas supprimé (réservé à ADMINISTRATEUR/RESPONSABLE_SAV).
    """

    try:
        return await warranty_service.delete_warranty(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


__all__ = ["router", "get_warranty_service"]
