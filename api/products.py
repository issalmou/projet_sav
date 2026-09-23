"""Routes de gestion des produits.

Lecture ouverte à tout utilisateur authentifié (un client doit pouvoir
identifier son produit pour créer un ticket/diagnostic). Gestion
(création/modification/suppression) réservée au staff (`STAFF_ROLES`),
comme pour les autres ressources de gestion de l'application
(`api/users.py`).
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.core.permissions import STAFF_ROLES, get_role_name, require_roles
from app.models.user import User
from app.schemas.client_product import ClientProductRead
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.client_product_service import ClientProductService
from app.services.product_service import ProductService
from app.utils.constants import RoleName


router = APIRouter(prefix="/products", tags=["Products"])


async def get_product_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> ProductService:
    """Fournit un ProductService lié à la session de la requête (même pattern que `get_ticket_service`)."""

    return ProductService(db)


@router.get("/status", status_code=status.HTTP_200_OK)
async def products_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "Product routes are ready"}


@router.post(
    "/",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé à administrateur/responsable_sav)."},
        409: {"description": "Un produit avec cette référence existe déjà."},
        422: {"description": "Payload invalide."},
    },
)
async def create_product(
    payload: ProductCreate,
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    """Crée un produit (réservé au staff)."""

    try:
        return await product_service.create_product(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _is_plain_client(user: User) -> bool:
    """Vrai si `user` est un client, sans le bypass staff/superuser."""

    return not user.is_superuser and get_role_name(user) == RoleName.CLIENT.value


@router.get(
    "/",
    response_model=list[ClientProductRead | ProductRead],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Ce compte utilisateur a été désactivé."},
    },
)
async def list_products(
    current_user: Annotated[User, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 50,
    offset: int = 0,
) -> list[ProductRead]:
    """Liste les produits.

    Un client ne voit que les produits qui lui sont affectés (ses achats) ;
    le staff et le technicien voient le catalogue complet (pagination
    `limit`/`offset`, même pattern que `GET /users`, `api/users.py`).
    """

    if _is_plain_client(current_user):
        return await ClientProductService(db).list_products(current_user.id)

    return await product_service.list_products(limit=limit, offset=offset)


@router.get(
    "/{product_id}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Ce compte utilisateur a été désactivé, ou (client) produit non affecté."},
        404: {"description": "Produit introuvable."},
    },
)
async def get_product(
    product_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductRead:
    """Retourne un produit par identifiant.

    Un client ne peut consulter qu'un produit qui lui est affecté."""

    try:
        product = await product_service.get_product(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if _is_plain_client(current_user) and not await ClientProductService(db).is_assigned(current_user.id, product_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This product is not assigned to you")

    return product


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé à administrateur/responsable_sav)."},
        404: {"description": "Produit introuvable."},
        422: {"description": "Payload invalide."},
    },
)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    """Met à jour un produit (réservé au staff)."""

    try:
        return await product_service.update_product(product_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé à administrateur/responsable_sav)."},
        404: {"description": "Produit introuvable."},
    },
)
async def delete_product(
    product_id: UUID,
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> None:
    """Supprime un produit (réservé au staff)."""

    try:
        await product_service.delete_product(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


__all__ = ["router", "get_product_service"]
