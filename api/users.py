"""Routes de gestion des utilisateurs.

Le module expose uniquement des points d'entrée HTTP préparatoires.
La logique métier et les services seront ajoutés dans une phase suivante.
"""
from fastapi import APIRouter, status


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/status", status_code=status.HTTP_200_OK)
async def users_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "User routes are ready"}


@router.get("/", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def list_users_placeholder() -> dict[str, str]:
    """Point d'entrée préparé pour lister les utilisateurs."""

    return {"detail": "Listing users will be implemented in a later phase"}


@router.get("/{user_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_user_placeholder(user_id: str) -> dict[str, str]:
    """Point d'entrée préparé pour récupérer un utilisateur par identifiant."""

    return {"detail": f"User {user_id} will be implemented in a later phase"}


@router.put("/{user_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def update_user_placeholder(user_id: str) -> dict[str, str]:
    """Point d'entrée préparé pour mettre à jour un utilisateur."""

    return {"detail": f"User {user_id} update will be implemented in a later phase"}


__all__ = ["router"]