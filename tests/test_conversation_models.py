"""Tests des modèles Conversation et Message (tâche 3.5)."""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.user import UserCreate
from app.services.user_service import UserService


@pytest_asyncio.fixture
async def chat_user(db_session):
    """Utilisateur de test ; sa suppression entraîne (cascade DB) celle de ses conversations/messages."""

    service = UserService(db_session)
    email = f"chat.{uuid.uuid4().hex[:10]}@example.com"
    user = await service.create_user(UserCreate(email=email, password="ValidPass1"))
    user_id = user.id  # capturé avant le test : un rollback() y expirerait `user`

    yield user

    still_there = await service.get_user_by_id(user_id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


@pytest.mark.asyncio
async def test_create_conversation_with_messages(db_session, chat_user, product_id):
    conversation = Conversation(user_id=chat_user.id, product_id=product_id, title="Erreur E17")
    db_session.add(conversation)
    await db_session.flush()

    db_session.add_all(
        [
            Message(conversation_id=conversation.id, role="user", content="Mon imprimante affiche E17"),
            Message(conversation_id=conversation.id, role="assistant", content="Vérifiez le capteur papier."),
        ]
    )
    await db_session.commit()

    result = await db_session.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    messages = result.scalars().all()

    assert [message.role for message in messages] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_deleting_conversation_cascades_to_messages(db_session, chat_user, product_id):
    conversation = Conversation(user_id=chat_user.id, product_id=product_id)
    db_session.add(conversation)
    await db_session.flush()

    db_session.add(Message(conversation_id=conversation.id, role="user", content="Bonjour"))
    await db_session.commit()

    conversation_id = conversation.id

    await db_session.delete(conversation)
    await db_session.commit()

    result = await db_session.execute(select(Message).where(Message.conversation_id == conversation_id))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_conversation_pending_ticket_confirmation_defaults_to_false(db_session, chat_user, product_id):
    conversation = Conversation(user_id=chat_user.id, product_id=product_id)
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    assert conversation.pending_ticket_confirmation is False


@pytest.mark.asyncio
async def test_invalid_message_role_is_rejected_by_db(db_session, chat_user, product_id):
    conversation = Conversation(user_id=chat_user.id, product_id=product_id)
    db_session.add(conversation)
    await db_session.flush()

    db_session.add(Message(conversation_id=conversation.id, role="bot", content="Rôle invalide"))

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


__all__: list[str] = []
