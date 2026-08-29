"""Utilitaires de sécurité applicative.

Ce module centralise le hachage des mots de passe et les opérations JWT
utilisées par la couche d'authentification.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


# bcrypt n'accepte que 72 octets : au-delà, le surplus est ignoré (comportement
# standard de bcrypt, déjà appliqué silencieusement par les anciennes versions).
_BCRYPT_MAX_BYTES = 72


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare un mot de passe en clair avec son hash."""

    plain_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(plain_bytes, hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Retourne le hash sécurisé d'un mot de passe."""

    password_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def create_access_token(subject: str, expires_delta: timedelta | None = None, token_type: str = "access") -> str:
    """Crée un JWT signé avec la clé applicative (type "access" ou "refresh")."""

    issued_at = datetime.now(timezone.utc)
    expire = issued_at + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    # "iat" est passé en timestamp flottant (et non en datetime) pour conserver
    # la précision à la microseconde : jose tronque les datetime à la seconde
    # via utctimetuple(), ce qui suffit pour "exp" mais casse la comparaison
    # fine avec User.tokens_revoked_at utilisée par la révocation au logout.
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "iat": issued_at.timestamp(), "type": token_type}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Crée un JWT de renouvellement, valide plus longtemps qu'un access token."""

    expires_delta = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    return create_access_token(subject, expires_delta=expires_delta, token_type="refresh")


def decode_access_token(token: str) -> dict[str, Any]:
    """Décode et valide un JWT."""

    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def get_token_subject(token: str) -> str | None:
    """Extrait le sujet d'un JWT s'il est valide."""

    try:
        payload = decode_access_token(token)
    except JWTError:
        return None

    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None


def get_token_type(token: str) -> str | None:
    """Extrait le type ("access" ou "refresh") d'un JWT s'il est valide."""

    try:
        payload = decode_access_token(token)
    except JWTError:
        return None

    token_type = payload.get("type")
    return token_type if isinstance(token_type, str) else None


def get_token_issued_at(token: str) -> datetime | None:
    """Extrait la date d'émission ("iat") d'un JWT s'il est valide."""

    try:
        payload = decode_access_token(token)
    except JWTError:
        return None

    issued_at = payload.get("iat")
    if issued_at is None:
        return None

    return datetime.fromtimestamp(issued_at, tz=timezone.utc)


__all__ = [
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "get_password_hash",
    "get_token_issued_at",
    "get_token_subject",
    "get_token_type",
    "verify_password",
]