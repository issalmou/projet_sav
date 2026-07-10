"""Schémas Pydantic pour les utilisateurs."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.role import RoleRead


class UserBase(BaseModel):
    """Champs partagés par les schémas User."""

    email: EmailStr
    full_name: str | None = Field(default=None, max_length=150)
    phone_number: str | None = Field(default=None, max_length=30)
    is_active: bool = True
    is_superuser: bool = False
    preferred_language: str = Field(default="fr", min_length=2, max_length=5)
    consent_given_at: datetime | None = None
    role_id: UUID | None = None


class UserCreate(UserBase):
    """Données attendues pour créer un utilisateur."""

    hashed_password: str = Field(min_length=8, max_length=255)


class UserUpdate(BaseModel):
    """Données autorisées pour la mise à jour partielle d'un utilisateur."""

    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=150)
    phone_number: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None
    is_superuser: bool | None = None
    preferred_language: str | None = Field(default=None, min_length=2, max_length=5)
    consent_given_at: datetime | None = None
    role_id: UUID | None = None
    hashed_password: str | None = Field(default=None, min_length=8, max_length=255)


class UserRead(UserBase):
    """Représentation complète d'un utilisateur exposée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    role: RoleRead | None = None


class UserPublic(BaseModel):
    """Vue publique légère d'un utilisateur."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None = None
    preferred_language: str = "fr"
    role: RoleRead | None = None


__all__ = ["UserBase", "UserCreate", "UserUpdate", "UserRead", "UserPublic"]
