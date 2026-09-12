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
    """Données attendues pour créer un ticket manuellement, via l'API publique.

    Réservé au staff (Responsable SAV / Administrateur / superuser,
    correction RBAC semaine 6) : le staff crée toujours un ticket au nom
    d'un client précis, jamais pour lui-même — `client_id` est donc
    obligatoire ici. `conversation_id` n'apparaît volontairement pas :
    renseigné uniquement par le workflow de diagnostic automatique
    (tâche 7), jamais à la création manuelle.
    """

    client_id: UUID


class TicketAutoCreate(TicketBase):
    """Données utilisées uniquement par le workflow de diagnostic automatique.

    Jamais exposé via l'API publique (agent SAV uniquement,
    tâche 7) : le propriétaire est toujours l'utilisateur pour lequel le
    service agit (le client en train de discuter), jamais une valeur
    fournie dans un payload — c'est pourquoi `client_id` n'existe pas ici,
    contrairement à `TicketCreate`.
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


__all__ = ["TicketAutoCreate", "TicketBase", "TicketCreate", "TicketRead", "TicketUpdate"]
