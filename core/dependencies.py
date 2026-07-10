"""Dépendances FastAPI partagées.

Ce module centralise les providers communs (settings, base de données,
authentification bearer) pour garder les routeurs fins et maintenables.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.security import get_token_subject
from app.database.session import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)


def get_settings() -> Settings:
	"""Expose les paramètres globaux via l'injection FastAPI."""

	return settings


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
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

	return subject


__all__ = ["get_current_subject", "get_db_session", "get_settings", "oauth2_scheme"]
