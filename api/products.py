"""Routes de gestion des produits (CDC semaine 6 : API Produits).

Lecture ouverte à tout utilisateur authentifié (un client doit pouvoir
identifier son produit pour créer un ticket/diagnostic). Gestion
(création/modification/suppression) réservée au staff (`STAFF_ROLES`),
comme pour les autres ressources de gestion de l'application
(`api/users.py`) — décision de conception validée (tâche 2, semaine 6),
pas une exigence explicite du CDC.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.core.permissions import STAFF_ROLES, require_roles
from app.models.user import User
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product_service import ProductService


router = APIRouter(prefix="/products", tags=["Products"])


async def get_product_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> ProductService:
    """Fournit un ProductService lié à la session de la requête (même pattern que `get_ticket_service`)."""

    return ProductService(db)


@router.get("/status", status_code=status.HTTP_200_OK)
async def products_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "Product routes are ready"}


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
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


@router.get("/", response_model=list[ProductRead], status_code=status.HTTP_200_OK)
async def list_products(
    current_user: Annotated[User, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> list[ProductRead]:
    """Liste tous les produits (lecture ouverte à tout utilisateur authentifié)."""

    return await product_service.list_products()


@router.get("/{product_id}", response_model=ProductRead, status_code=status.HTTP_200_OK)
async def get_product(
    product_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    """Retourne un produit par identifiant (lecture ouverte à tout utilisateur authentifié)."""

    try:
        return await product_service.get_product(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{product_id}", response_model=ProductRead, status_code=status.HTTP_200_OK)
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


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
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
