"""Modèle Ticket.

Un ticket représente une demande de support SAV : créé par un client, à la
main ou automatiquement par l'agent SAV (outil create_ticket ->
Ticket, tâche 7), éventuellement rattaché à un produit et à la conversation
de diagnostic qui l'a généré, puis pris en charge par un technicien
(CDC "Fonctionnement d'un agent intelligent" : Diagnostic -> Résolution ou
ticket -> Escalade).
"""
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

    # RESTRICT : un ticket est un enregistrement d'activité SAV (historique de
    # réparation, traçabilité garantie) à valeur durable pour l'équipe, au
    # même titre que Document.created_by_id — la suppression d'un compte
    # client ne doit pas effacer silencieusement cet historique.
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # SET NULL : référence optionnelle à "qui traite le ticket actuellement" ;
    # elle doit pouvoir se vider proprement, comme User.role_id.
    assigned_technician_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # foreign_keys explicite requis : deux FK distinctes vers `users` sur ce
    # modèle (client_id, assigned_technician_id) rendent la relation
    # ambiguë pour SQLAlchemy sans cette précision.
    client: Mapped["User"] = relationship(foreign_keys=[client_id])
    assigned_technician: Mapped["User | None"] = relationship(foreign_keys=[assigned_technician_id])
    product: Mapped["Product | None"] = relationship()
    conversation: Mapped["Conversation | None"] = relationship()

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} status={self.status}>"


__all__ = ["Ticket"]
