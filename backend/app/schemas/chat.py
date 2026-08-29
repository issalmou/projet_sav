"""Schémas Pydantic pour le chat IA (conversations et messages)."""
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
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationPublic):
    """Vue détaillée d'une conversation avec son historique complet."""

    messages: list[MessagePublic] = Field(default_factory=list)


class ChatMessageRequest(BaseModel):
    """Message envoyé par l'utilisateur à l'agent IA."""

    conversation_id: UUID | None = None
    content: str = Field(min_length=1, max_length=8000)


class ChatMessageResponse(BaseModel):
    """Réponse de l'agent IA à un message utilisateur."""

    conversation_id: UUID
    message: MessagePublic


__all__ = [
    "MessageRole",
    "MessagePublic",
    "ConversationPublic",
    "ConversationDetail",
    "ChatMessageRequest",
    "ChatMessageResponse",
]
