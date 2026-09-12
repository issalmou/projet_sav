"""Routes de chat IA.

Deux endpoints distincts (séparation création / message) :
- `POST /chat/conversations` : ouvre une conversation sur un produit ;
- `POST /chat/message` : envoie un message dans une conversation existante.

Toutes les routes sont protégées par JWT. La logique métier (propriété de la
conversation, affectation client ↔ produit, agent LangGraph) vit dans
`ChatService` / `app.ai.agent`.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.exceptions import LLMError
from app.core.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationCreateRequest,
    ConversationDetail,
    ConversationPublic,
)
from app.services.chat_service import ChatService, ProductNotAssignedError


router = APIRouter(prefix="/chat", tags=["Chat"])


async def get_chat_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> ChatService:
    """Fournit un ChatService lié à la session de la requête.

    Dépendance dédiée pour permettre aux tests d'injecter un ChatService
    branché sur un agent / fournisseur LLM factice via `app.dependency_overrides`.
    """

    return ChatService(db)


@router.post(
    "/conversations",
    response_model=ConversationPublic,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Un client ne peut ouvrir une conversation que sur un produit qui lui est affecté."},
        404: {"description": "product_id inconnu."},
        422: {"description": "Payload invalide (product_id manquant ou mal formé)."},
    },
)
async def create_conversation(
    payload: ConversationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ConversationPublic:
    """Ouvre une conversation SAV dans le contexte d'un produit (obligatoire, immuable ensuite)."""

    try:
        return await chat_service.open_conversation(current_user, payload.product_id)
    except ProductNotAssignedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Ce compte utilisateur a été désactivé."},
        404: {"description": "conversation_id introuvable, ou n'appartenant pas à l'appelant."},
        422: {"description": "Payload invalide (conversation_id manquant, content vide/trop long)."},
        503: {"description": "Le fournisseur LLM configuré a échoué à générer une réponse."},
    },
)
async def send_message(
    payload: ChatMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatMessageResponse:
    """Envoie un message dans une conversation existante et retourne la réponse de l'agent.

    `conversation_id` est obligatoire ; la propriété de la conversation est
    vérifiée dans le service (un client ne peut jamais écrire dans la
    conversation d'un autre). Le produit utilisé (RAG, ticket) est celui de la
    conversation. L'agent peut créer un ticket (après confirmation explicite du
    client) : `ticket_id` est alors renseigné.
    """

    try:
        result = await chat_service.handle_message(
            current_user, payload.conversation_id, payload.content
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return ChatMessageResponse(
        conversation_id=result.conversation.id,
        message=result.message,
        ticket_id=result.ticket_id,
    )


@router.get(
    "/conversations",
    response_model=list[ConversationPublic],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Ce compte utilisateur a été désactivé."},
    },
)
async def list_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Liste les conversations de l'utilisateur courant, les plus récentes d'abord."""

    return await chat_service.list_conversations(current_user.id)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Ce compte utilisateur a été désactivé."},
        404: {"description": "Conversation introuvable, ou n'appartenant pas à l'appelant."},
    },
)
async def get_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ConversationDetail:
    """Retourne une conversation avec son historique complet de messages."""

    try:
        conversation = await chat_service.get_conversation(conversation_id, current_user.id)
        messages = await chat_service.get_history(conversation_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return ConversationDetail(
        id=conversation.id,
        product_id=conversation.product_id,
        title=conversation.title,
        pending_ticket_confirmation=conversation.pending_ticket_confirmation,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Ce compte utilisateur a été désactivé."},
        404: {"description": "Conversation introuvable, ou n'appartenant pas à l'appelant."},
    },
)
async def delete_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> None:
    """Supprime une conversation (et son historique, par cascade) appartenant à l'utilisateur courant."""

    try:
        await chat_service.delete_conversation(conversation_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


__all__ = ["router", "get_chat_service"]
