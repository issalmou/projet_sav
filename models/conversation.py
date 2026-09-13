"""Modèle Conversation.

Une conversation regroupe l'historique des échanges entre un utilisateur et
    l'agent IA.
"""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, false
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation_event import ConversationEvent
    from app.models.message import Message
    from app.models.product import Product


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Conversation entre un utilisateur et l'agent IA."""

    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Le produit est la source de vérité du filtrage RAG et des tickets.
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Attend la confirmation du client avant de créer un ticket.
    pending_ticket_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # État déterministe du diagnostic, piloté par le backend.
    diagnostic_attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    # Un diagnostic exige une recherche documentaire préalable.
    search_performed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    awaiting_step_feedback: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    problem_resolved: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    events: Mapped[list["ConversationEvent"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationEvent.created_at",
    )
    product: Mapped["Product"] = relationship()

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} user_id={self.user_id}>"


__all__ = ["Conversation"]
