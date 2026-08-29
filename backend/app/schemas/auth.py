"""Schémas Pydantic pour l'authentification."""
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Identifiants attendus pour se connecter."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=255)


class Token(BaseModel):
    """Réponse renvoyée après une authentification réussie."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Jeton de renouvellement fourni pour obtenir un nouveau access token."""

    refresh_token: str


__all__ = ["LoginRequest", "RefreshRequest", "Token"]
