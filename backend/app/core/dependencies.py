"""Dépendances FastAPI partagées.

Ce module centralise les providers communs (settings, base de données,
authentification bearer) pour garder les routeurs fins et maintenables.
"""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_token_issued_at, get_token_subject, get_token_type
from app.database.session import get_db
from app.models.user import User
from app.services.user_service import UserService


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)


async def get_db_session(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncSession:
    """Alias explicite de la dépendance session SQLAlchemy."""

    return db


async def get_current_subject(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> str:
    """Retourne le sujet JWT courant ou lève une erreur 401."""

    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    subject = get_token_subject(token)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        )

    if get_token_type(token) != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A refresh token cannot be used to access this route",
        )

    return subject


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    subject: Annotated[str, Depends(get_current_subject)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Charge l'utilisateur courant à partir du token JWT et vérifie qu'il est actif."""

    try:
        user_id = UUID(subject)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token does not reference a valid user id",
        )

    user = await UserService(db).get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The user associated with this token no longer exists",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account has been deactivated",
        )

    if user.tokens_revoked_at is not None:
        issued_at = get_token_issued_at(token) if token else None
        if issued_at is None or issued_at < user.tokens_revoked_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="This token has been revoked, please log in again",
            )

    return user


__all__ = ["get_current_subject", "get_current_user", "get_db_session", "oauth2_scheme"]
