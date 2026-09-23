"""Routes de gestion des garanties produit (CDC semaine 6 : API Garanties).

La garantie est une propriété statique de `Product.warranty_months`.

Accès :
- Lecture (`GET /{product_id}`) : tout utilisateur authentifié, mais un
  client ne peut consulter que la garantie d'un produit qui lui est affecté
  (présent dans un de ses tickets).
- Modification (`PATCH /{product_id}`) et suppression (`DELETE /{product_id}`) :
  réservées à l'administrateur.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.core.permissions import get_role_name, require_roles
from app.models.user import User
from app.schemas.product import ProductWarrantyRead, WarrantyUpdate
from app.services.warranty_service import WarrantyService
from app.utils.constants import RoleName


router = APIRouter(prefix="/warranties", tags=["Warranties"])


def _is_client(user: User) -> bool:
    return get_role_name(user) == RoleName.CLIENT.value


async def get_warranty_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> WarrantyService:
    """Fournit un WarrantyService lié à la session de la requête (même pattern que `get_product_service`)."""

    return WarrantyService(db)


@router.get(
    "/{product_id}",
    response_model=ProductWarrantyRead,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Ce compte utilisateur a été désactivé."},
        404: {"description": "Produit introuvable ou non affecté au client."},
    },
)
async def get_product_warranty(
    product_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    warranty_service: Annotated[WarrantyService, Depends(get_warranty_service)],
) -> ProductWarrantyRead:
    """Retourne la garantie d'un produit. Un client ne voit que les produits qui lui sont affectés."""

    if _is_client(current_user) and not await warranty_service.is_assigned_to_client(product_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product warranty not found")

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
        403: {"description": "Rôle insuffisant (réservé à l'administrateur)."},
        404: {"description": "Produit introuvable."},
        422: {"description": "warranty_months manquant ou négatif."},
    },
)
async def update_product_warranty(
    product_id: UUID,
    payload: WarrantyUpdate,
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMINISTRATEUR.value))],
    warranty_service: Annotated[WarrantyService, Depends(get_warranty_service)],
) -> ProductWarrantyRead:
    """Met à jour la garantie d'un produit (réservé à l'administrateur)."""

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
        403: {"description": "Rôle insuffisant (réservé à l'administrateur)."},
        404: {"description": "Produit introuvable."},
    },
)
async def delete_product_warranty(
    product_id: UUID,
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMINISTRATEUR.value))],
    warranty_service: Annotated[WarrantyService, Depends(get_warranty_service)],
) -> ProductWarrantyRead:
    """Supprime la garantie d'un produit, c'est-à-dire remet `warranty_months` à `None`.

    Le produit n'est pas supprimé (réservé à l'administrateur).
    """

    try:
        return await warranty_service.delete_warranty(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


__all__ = ["router", "get_warranty_service"]