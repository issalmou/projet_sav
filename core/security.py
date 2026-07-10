"""Utilitaires de sécurité applicative.

Ce module centralise le hachage des mots de passe et les opérations JWT
utilisées par la couche d'authentification.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare un mot de passe en clair avec son hash."""

    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Retourne le hash sécurisé d'un mot de passe."""

    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Crée un JWT d'accès signé avec la clé applicative."""

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Décode et valide un JWT d'accès."""

    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def get_token_subject(token: str) -> str | None:
    """Extrait le sujet d'un JWT s'il est valide."""

    try:
        payload = decode_access_token(token)
    except JWTError:
        return None

    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None


__all__ = [
    "create_access_token",
    "decode_access_token",
    "get_password_hash",
    "get_token_subject",
    "pwd_context",
    "verify_password",
]