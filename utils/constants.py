"""Constantes métier partagées.

Ce module centralise les valeurs fixes issues du cahier des charges, afin
d'éviter toute divergence entre les différentes couches de l'application.
"""
from enum import Enum


class RoleName(str, Enum):
    """Rôles utilisateur authentifiables."""

    CLIENT = "client"
    TECHNICIEN = "technicien"
    RESPONSABLE_SAV = "responsable_sav"
    ADMINISTRATEUR = "administrateur"


class DocumentType(str, Enum):
    """Formats de fichier acceptés pour l'upload documentaire (CDC semaine 4, tâche 3)."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class DocumentCategory(str, Enum):
    """Catégories de la base de connaissances (CDC §13 ; cf. dossiers knowledge_base/)."""

    FAQ = "faq"
    MANUALS = "manuals"
    PROCEDURES = "procedures"
    PRODUCTS = "products"
    VIDEOS = "videos"


class DocumentStatus(str, Enum):
    """Cycle de vie d'un document de la base de connaissances."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class DiagnosticStatus(str, Enum):
    """Statut d'une réponse de diagnostic automatique (CDC semaine 5).

    Déterminé par le LLM lui-même via une instruction dédiée
    (cf. app.ai.prompts.DIAGNOSTIC_STATUS_INSTRUCTION), interprété par
    DiagnosticService.
    """

    RESOLVED = "resolved"
    IN_PROGRESS = "in_progress"
    ESCALATE = "escalate"


class TicketStatus(str, Enum):
    """Cycle de vie d'un ticket de support SAV (CDC semaine 5/6).

    Valeurs synchronisées avec le CheckConstraint `status_valid` du modèle
    `Ticket` (déjà migré) ; cet enum sert à la validation côté schémas
    Pydantic, sur le même principe que DocumentStatus.
    """

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketConfirmation(str, Enum):
    """Réponse du client à une proposition explicite de création de ticket.

    Déterminée par le LLM via une instruction dédiée
    (cf. app.ai.prompts.TICKET_CONFIRMATION_INSTRUCTION), interprétée par
    DiagnosticService uniquement lorsque Conversation.pending_ticket_confirmation
    est vrai (c'est-à-dire qu'un ticket a été proposé mais pas encore créé).
    """

    CONFIRMED = "confirmed"
    DECLINED = "declined"
    UNCLEAR = "unclear"


__all__ = [
    "DiagnosticStatus",
    "DocumentCategory",
    "DocumentStatus",
    "DocumentType",
    "RoleName",
    "TicketConfirmation",
    "TicketStatus",
]
