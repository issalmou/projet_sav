"""Routes de chat IA.

Toutes les routes sont protégées par JWT (`get_current_user`) et ne portent
que la responsabilité HTTP : la logique métier vit entièrement dans
`ChatService`.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.exceptions import LLMError
from app.core.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ConversationDetail, ConversationPublic
from app.services.chat_service import ChatService
from app.services.diagnostic_service import DiagnosticService


router = APIRouter(prefix="/chat", tags=["Chat"])


async def get_chat_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> ChatService:
    """Fournit un ChatService lié à la session de la requête.

    Utilisé par les routes de gestion des conversations (lecture/suppression),
    qui n'ont pas besoin de la logique de diagnostic. Dépendance dédiée
    (plutôt qu'une instanciation directe) pour permettre aux tests d'injecter
    un ChatService branché sur un fournisseur LLM factice via
    `app.dependency_overrides`.
    """

    return ChatService(db)


async def get_diagnostic_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> DiagnosticService:
    """Fournit un DiagnosticService lié à la session de la requête.

    Utilisé par `POST /chat/message` : chaque message client passe par le
    diagnostic (statut RESOLU/EN_COURS/A_ESCALADER, proposition puis
    confirmation avant création de ticket), sur le même principe que
    `get_chat_service` — dépendance dédiée pour permettre aux tests
    d'injecter un DiagnosticService branché sur un fournisseur LLM factice.
    """

    return DiagnosticService(db)


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Ce compte utilisateur a été désactivé."},
        404: {"description": "conversation_id fourni mais introuvable, ou n'appartenant pas à l'appelant."},
        422: {"description": "Payload invalide (content vide ou trop long)."},
        503: {"description": "Le fournisseur LLM configuré a échoué à générer une réponse."},
    },
)
async def send_message(
    payload: ChatMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    diagnostic_service: Annotated[DiagnosticService, Depends(get_diagnostic_service)],
) -> ChatMessageResponse:
    """Envoie un message à l'agent IA (crée une conversation si `conversation_id` est absent).

    Le message passe par le diagnostic automatique (statut RESOLU/EN_COURS/
    A_ESCALADER). Sur escalade, aucun ticket n'est créé immédiatement : le
    client est informé et invité à confirmer ; le ticket n'est réellement créé
    via TicketService qu'après une confirmation explicite sur un tour suivant.
    """

    try:
        result = await diagnostic_service.diagnose(
            current_user, payload.content, conversation_id=payload.conversation_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return ChatMessageResponse(
        conversation_id=result.conversation.id,
        message=result.message,
        ticket_id=result.ticket.id if result.ticket is not None else None,
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
        title=conversation.title,
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
