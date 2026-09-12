"""Routes d'affectation et de consultation des produits d'un client.

« Client » n'est pas une entité distincte : c'est un `User` de rôle
« client » (cf. `models/client_product.py`). Ces routes ne gèrent QUE
l'affectation de produits EXISTANTS à un client — jamais la création,
la modification ou la suppression d'un produit (réservées à `/products`).

Accès (RBAC existant, `core/permissions.py`) :
- `POST` / `DELETE` : administrateur, responsable_sav, superuser ;
- `GET`             : le client lui-même, ou le staff (administrateur /
  responsable_sav / superuser).
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.core.permissions import STAFF_ROLES, get_role_name, require_roles
from app.models.user import User
from app.schemas.client_product import ClientProductAssign, ClientProductRead
from app.services.client_product_service import (
    ClientNotFoundError,
    ClientProductService,
    ProductsNotFoundError,
)


router = APIRouter(prefix="/clients", tags=["Clients"])


async def get_client_product_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClientProductService:
    """Fournit un ClientProductService lié à la session de la requête (même pattern que les autres)."""

    return ClientProductService(db)


def _ensure_can_read_client(current_user: User, client_id: UUID) -> None:
    """Autorise le client lui-même, ou un membre du staff / superuser."""

    if current_user.id == client_id:
        return
    if current_user.is_superuser or get_role_name(current_user) in STAFF_ROLES:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You cannot access this client's products",
    )


@router.get(
    "/{client_id}/products",
    response_model=list[ClientProductRead],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Un client ne peut consulter que ses propres produits."},
        404: {"description": "client_id introuvable ou n'ayant pas le rôle client."},
    },
)
async def list_client_products(
    client_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ClientProductService, Depends(get_client_product_service)],
) -> list[ClientProductRead]:
    """Liste les produits affectés à un client (le client lui-même, ou le staff)."""

    _ensure_can_read_client(current_user, client_id)

    try:
        return await service.list_products(client_id)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/{client_id}/products",
    response_model=list[ClientProductRead],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé à administrateur / responsable_sav)."},
        404: {"description": "client_id introuvable / sans le rôle client, ou product_id inconnu."},
        422: {"description": "Payload invalide (items vide, qte < 1, ou mal formé)."},
    },
)
async def assign_client_products(
    client_id: UUID,
    payload: ClientProductAssign,
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    service: Annotated[ClientProductService, Depends(get_client_product_service)],
) -> list[ClientProductRead]:
    """Affecte un ou plusieurs produits EXISTANTS à un client existant (réservé au staff).

    Corps : `{"items": [{"product_id": "...", "qte": N}]}` (`qte` >= 1, défaut 1).
    Doublons de `product_id` fusionnés ; produit déjà affecté → quantité mise à
    jour (upsert) ; transaction unique. Retourne la liste complète des produits
    du client (avec leur quantité) après affectation.
    """

    try:
        return await service.assign_products(client_id, payload.items)
    except (ClientNotFoundError, ProductsNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/{client_id}/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé à administrateur / responsable_sav)."},
        404: {"description": "client_id introuvable / sans le rôle client, ou produit non affecté."},
    },
)
async def unassign_client_product(
    client_id: UUID,
    product_id: UUID,
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    service: Annotated[ClientProductService, Depends(get_client_product_service)],
) -> None:
    """Retire l'affectation d'un produit à un client (réservé au staff)."""

    try:
        await service.unassign_product(client_id, product_id)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


__all__ = ["router", "get_client_product_service"]
