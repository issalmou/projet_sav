"""Schémas Pydantic pour les rôles applicatifs."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleBase(BaseModel):
    """Champs partagés par les schémas Role."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    is_system: bool = False


class RoleCreate(RoleBase):
    """Données attendues pour créer un rôle."""


class RoleUpdate(BaseModel):
    """Données autorisées pour la mise à jour partielle d'un rôle."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    is_system: bool | None = None


class RoleRead(RoleBase):
    """Représentation complète d'un rôle exposée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


__all__ = ["RoleBase", "RoleCreate", "RoleUpdate", "RoleRead"]
