"""Modèle Conversation.

Une conversation regroupe l'historique des échanges entre un utilisateur et
l'agent IA (CDC §7 "Modèle de données" : Conversations ; §9 : "mémoire
conversationnelle").
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
    # Produit concerné par la conversation. Obligatoire : une conversation SAV
    # existe toujours dans le contexte d'un produit précis, fourni au tout
    # premier message (`ChatService.create_conversation`) et jamais modifiable
    # ensuite. C'est la source de vérité pour le filtrage RAG et pour
    # `Ticket.product_id` — le texte du client / le LLM ne le déterminent jamais.
    # CASCADE, comme `user_id` : la conversation est un historique dérivé de ses
    # deux parents (utilisateur + produit).
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Vrai si l'agent SAV a proposé de créer un ticket (outil request_ticket_creation) et attend
    # encore une confirmation explicite du client (oui/non) avant de le créer via
    # TicketService. Remis à faux dès que la confirmation est tranchée (oui ou non).
    pending_ticket_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- État déterministe du diagnostic (jamais manipulé par le LLM) --------
    # Les outils de l'agent (`app.ai.agent.tools`) font évoluer ces champs ;
    # les règles d'escalade (`escalate_to_technician`) les lisent. Le LLM ne
    # fournit que du texte / des booléens d'interprétation, jamais ces valeurs.

    # Nombre de cycles « étapes proposées → le client rapporte que ça n'a pas
    # fonctionné ». C'est le compteur qui pilote l'escalade automatique
    # (seuil : settings.AGENT_ESCALATION_MAX_FAILED_ATTEMPTS).
    diagnostic_attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    # Vrai dès qu'une recherche documentaire a réellement été exécutée pour
    # cette conversation. `submit_diagnosis` la vérifie : pas de diagnostic
    # sans avoir consulté la documentation.
    search_performed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    # Vrai entre le moment où l'agent a proposé des étapes et le moment où le
    # client a rapporté le résultat.
    awaiting_step_feedback: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    # Vrai si le client a confirmé que le problème est résolu (→ pas de ticket).
    problem_resolved: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    # Journal structuré du diagnostic (recherche / hypothèses / retours client /
    # escalade). Chargé explicitement par le service quand l'agent en a besoin.
    events: Mapped[list["ConversationEvent"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationEvent.created_at",
    )
    # Chargée explicitement par les requêtes qui en ont besoin (selectinload /
    # refresh) ; jamais en eager par défaut.
    product: Mapped["Product"] = relationship()

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} user_id={self.user_id}>"


__all__ = ["Conversation"]
