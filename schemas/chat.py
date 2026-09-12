"""Schémas Pydantic pour le chat IA (conversations et messages).

Contrat en deux temps :
- `POST /chat/conversations`  {"product_id": "..."}   → crée la conversation ;
- `POST /chat/message`        {"conversation_id": "...", "content": "..."} → un message.

`product_id` n'apparaît QUE dans la création de conversation ; il est ensuite
immuable et sert de source de vérité (RAG, agent, ticket).
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


MessageRole = Literal["user", "assistant"]


class MessagePublic(BaseModel):
    """Représentation d'un message exposée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    content: str
    created_at: datetime


class ConversationPublic(BaseModel):
    """Vue liste d'une conversation (sans ses messages)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    title: str | None = None
    pending_ticket_confirmation: bool = False
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationPublic):
    """Vue détaillée d'une conversation avec son historique complet."""

    messages: list[MessagePublic] = Field(default_factory=list)


class ConversationCreateRequest(BaseModel):
    """Corps de `POST /chat/conversations` : ouvre une conversation sur un produit."""

    product_id: UUID


class ChatMessageRequest(BaseModel):
    """Corps de `POST /chat/message` : un message dans une conversation EXISTANTE.

    `conversation_id` est obligatoire — il n'est plus possible de créer une
    conversation implicitement en envoyant un message. Aucun `product_id` ici :
    le produit vient de la conversation.
    """

    conversation_id: UUID
    content: str = Field(min_length=1, max_length=8000)


class ChatMessageResponse(BaseModel):
    """Réponse de l'agent IA à un message utilisateur.

    `ticket_id` n'est renseigné que si ce tour a réellement créé un ticket
    (l'agent a appelé l'outil `create_ticket` après confirmation du client).
    `None` dans tous les autres cas.
    """

    conversation_id: UUID
    message: MessagePublic
    ticket_id: UUID | None = None


__all__ = [
    "ChatMessageRequest",
    "ChatMessageResponse",
    "ConversationCreateRequest",
    "ConversationDetail",
    "ConversationPublic",
    "MessagePublic",
    "MessageRole",
]
