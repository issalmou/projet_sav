"""Modèle Conversation.

Une conversation regroupe l'historique des échanges entre un utilisateur et
l'agent IA (CDC §7 "Modèle de données" : Conversations ; §9 : "mémoire
conversationnelle").
"""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.message import Message


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Conversation entre un utilisateur et l'agent IA."""

    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Vrai si DiagnosticService a proposé un ticket (statut A_ESCALADER) et attend
    # encore une confirmation explicite du client (oui/non) avant de le créer via
    # TicketService. Remis à faux dès que la confirmation est tranchée (oui ou non).
    pending_ticket_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} user_id={self.user_id}>"


__all__ = ["Conversation"]
