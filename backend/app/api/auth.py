"""Routes d'authentification.

Ce module expose la connexion, le profil courant et le renouvellement de
jeton JWT.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, Token
from app.schemas.user import UserPublic
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/status", status_code=status.HTTP_200_OK)
async def auth_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "Auth routes are ready"}


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Token:
    """Authentifie un utilisateur (email + mot de passe) et retourne un JWT."""

    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(credentials.email, credentials.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = await auth_service.create_access_token(str(user.id))
    refresh_token = await auth_service.create_refresh_token(str(user.id))
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.get("/me", response_model=UserPublic, status_code=status.HTTP_200_OK)
async def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Retourne le profil de l'utilisateur actuellement authentifié."""

    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """Déconnecte l'utilisateur en révoquant immédiatement tous ses tokens (access et refresh)."""

    await AuthService(db).logout_user(current_user)
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token, status_code=status.HTTP_200_OK)
async def refresh(
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Token:
    """Génère un nouveau access token à partir d'un refresh token valide."""

    auth_service = AuthService(db)
    try:
        access_token = await auth_service.refresh_access_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    return Token(access_token=access_token, token_type="bearer")


__all__ = ["router"]