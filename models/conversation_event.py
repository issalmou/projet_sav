"""Modèle ConversationEvent — journal du diagnostic d'une conversation.

Table append-only : chaque étape structurée du diagnostic mené par l'agent SAV
(recherche documentaire, hypothèse + étapes proposées, retour du client,
escalade, création de ticket) y est consignée. Elle sert à deux choses :

1. redonner à l'agent, au tour suivant, ce qui a déjà été tenté (l'état
   LangGraph est volatil — cf. `app.ai.agent.graph`) ;
2. générer automatiquement la description d'un ticket à partir du diagnostic
   réellement effectué (`app.ai.agent.ticket_summary`), jamais inventée.

Les compteurs de sécurité (nombre de tentatives, seuil d'escalade) restent des
colonnes de `Conversation`, jamais dérivés du texte du LLM.
"""
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation


# Types d'événements consignés. Volontairement fermé (CheckConstraint) :
# ajouter un type = une migration, pas une valeur libre venue du LLM.
#
# "new_issue" (audit, point 4 — multi-sujets) : marqueur de frontière posé
# par l'outil `start_new_issue` quand le client décrit, dans la MÊME
# conversation, un problème distinct du précédent (déjà résolu ou déjà
# ticketé-puis-fermé). Il délimite un nouveau CYCLE de diagnostic sans
# jamais effacer l'historique : `events_since_last_new_issue` ci-dessous
# scope la lecture (récapitulatif LLM, description de ticket) au cycle en
# cours, tandis que la table reste intégralement consultable pour l'audit.
EVENT_TYPES = ("search", "diagnosis", "feedback", "escalation", "ticket", "new_issue")


class ConversationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Un événement structuré du déroulé de diagnostic d'une conversation."""

    __tablename__ = "conversation_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('search', 'diagnosis', 'feedback', 'escalation', 'ticket', 'new_issue')",
            name="event_type_valid",
        ),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # Contenu libre selon le type (query + titres de docs, cause + étapes,
    # resolved + n° de tentative, raison d'escalade, id de ticket…).
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    conversation: Mapped["Conversation"] = relationship(back_populates="events")

    def __repr__(self) -> str:
        return f"<ConversationEvent id={self.id} type={self.event_type}>"


def events_since_last_new_issue(events: list["ConversationEvent"]) -> list["ConversationEvent"]:
    """Ne garde que les événements du cycle de diagnostic EN COURS.

    `events` doit être trié chronologiquement (comme le renvoie déjà
    `_load_events`/`_get_diagnostic_events`). S'il n'y a jamais eu de
    frontière `new_issue`, la conversation n'a qu'un seul cycle : tous les
    événements sont retournés tels quels (comportement inchangé pour toute
    conversation à sujet unique — aucune régression).
    """

    last_boundary = None
    for index, event in enumerate(events):
        if event.event_type == "new_issue":
            last_boundary = index
    if last_boundary is None:
        return events
    return events[last_boundary + 1 :]


__all__ = ["ConversationEvent", "EVENT_TYPES", "events_since_last_new_issue"]
