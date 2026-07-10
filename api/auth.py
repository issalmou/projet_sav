"""Routes d'authentification.

Ce module expose uniquement le routeur et des points d'entrée HTTP
préparatoires. La logique métier JWT sera ajoutée dans une phase suivante.
"""
from fastapi import APIRouter, status


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/status", status_code=status.HTTP_200_OK)
async def auth_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "Auth routes are ready"}


@router.post("/login", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def login_placeholder() -> dict[str, str]:
    """Point d'entrée préparé pour l'authentification JWT."""

    return {"detail": "Login will be implemented in a later phase"}


@router.post("/refresh", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def refresh_placeholder() -> dict[str, str]:
    """Point d'entrée préparé pour le renouvellement de jeton."""

    return {"detail": "Token refresh will be implemented in a later phase"}


__all__ = ["router"]