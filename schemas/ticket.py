"""Schémas Pydantic pour les tickets SAV (CDC semaine 5/6)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductRead
from app.schemas.user import UserPublic
from app.utils.constants import TicketStatus


class TicketBase(BaseModel):
    """Champs partagés par les schémas Ticket."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    product_id: UUID | None = None


class TicketCreate(TicketBase):
    """Données attendues pour créer un ticket.

    `client_id` n'apparaît pas ici : le propriétaire d'un ticket est
    toujours l'utilisateur authentifié à l'origine de la requête (résolu
    dans TicketService/la route), jamais une valeur fournie dans le corps
    de la requête. `conversation_id` n'apparaît pas non plus : renseigné
    uniquement par le workflow de diagnostic automatique (tâche 7), jamais
    à la création manuelle d'un ticket.
    """


class TicketUpdate(BaseModel):
    """Données autorisées pour la mise à jour partielle d'un ticket."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    status: TicketStatus | None = None
    assigned_technician_id: UUID | None = None
    product_id: UUID | None = None


class TicketRead(TicketBase):
    """Représentation complète d'un ticket exposée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: TicketStatus
    client: UserPublic
    assigned_technician: UserPublic | None = None
    product: ProductRead | None = None
    conversation_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


__all__ = ["TicketBase", "TicketCreate", "TicketRead", "TicketUpdate"]
