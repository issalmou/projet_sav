"""Schémas Pydantic pour les rôles applicatifs."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.utils.constants import RoleName


class RoleBase(BaseModel):
    """Champs partagés par les schémas Role."""

    name: RoleName
    description: str | None = Field(default=None, max_length=2000)


class RoleCreate(RoleBase):
    """Données attendues pour créer un rôle."""


class RoleRead(RoleBase):
    """Représentation complète d'un rôle exposée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


__all__ = ["RoleBase", "RoleCreate", "RoleRead"]
