"""Modèle des tickets de support SAV."""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.product import Product
    from app.models.user import User


class Ticket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Ticket de support SAV."""

    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'in_progress', 'resolved', 'closed')", name="status_valid"),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)

    # L’historique SAV doit survivre à la suppression du client.
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_technician_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Les deux FK vers users rendent la relation ambiguë sans cette précision.
    client: Mapped["User"] = relationship(foreign_keys=[client_id])
    assigned_technician: Mapped["User | None"] = relationship(foreign_keys=[assigned_technician_id])
    product: Mapped["Product | None"] = relationship()
    conversation: Mapped["Conversation | None"] = relationship()

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} status={self.status}>"


__all__ = ["Ticket"]
