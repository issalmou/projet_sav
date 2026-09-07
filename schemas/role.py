"""Schémas Pydantic pour les rôles applicatifs."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.utils.constants import RoleName


class RoleBase(BaseModel):
    """Champs partagés par les schémas Role.

    `name` est un `str` ici (pas `RoleName`) : la colonne `roles.name` n'est
    pas contrainte par un enum en base, et `RoleRead` (qui hérite de cette
    base) doit pouvoir représenter n'importe quelle ligne réellement stockée.
    La contrainte aux 4 valeurs officielles du CDC s'applique uniquement en
    entrée, via `RoleCreate.name: RoleName` ci-dessous.
    """

    name: str
    description: str | None = Field(default=None, max_length=2000)


class RoleCreate(RoleBase):
    """Données attendues pour créer un rôle."""

    name: RoleName


class RoleUpdate(BaseModel):
    """Données autorisées pour la mise à jour d'un rôle.

    `name` n'est volontairement pas modifiable : les 4 valeurs de `RoleName`
    sont référencées en dur ailleurs dans l'application (permissions, seed),
    un renommage casserait ces références sans que rien ne le détecte.
    """

    description: str | None = Field(default=None, max_length=2000)


class RoleRead(RoleBase):
    """Représentation complète d'un rôle exposée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


__all__ = ["RoleBase", "RoleCreate", "RoleRead", "RoleUpdate"]
