"""Tests de ChatService : création de conversation et gestion de l'historique (tâche 3.6)."""
import uuid

import pytest
import pytest_asyncio

from app.schemas.user import UserCreate
from app.services.chat_service import ChatService
from app.services.user_service import UserService
from conftest import NullRetriever


@pytest_asyncio.fixture
async def chat_user(db_session):
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
async def test_create_conversation(db_session, chat_user):
    service = ChatService(db_session, retriever=NullRetriever())

    conversation = await service.create_conversation(chat_user.id, title="Erreur E17")

    assert conversation.id is not None
    assert conversation.user_id == chat_user.id
    assert conversation.title == "Erreur E17"


@pytest.mark.asyncio
async def test_add_user_and_assistant_messages_builds_history(db_session, chat_user):
    service = ChatService(db_session, retriever=NullRetriever())
    conversation = await service.create_conversation(chat_user.id)

    user_message = await service.add_user_message(conversation.id, "Mon imprimante affiche E17")
    assistant_message = await service.add_assistant_message(
        conversation.id, "Vérifiez que le bac papier est bien inséré."
    )

    history = await service.get_history(conversation.id, chat_user.id)

    assert [message.id for message in history] == [user_message.id, assistant_message.id]
    assert [message.role for message in history] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_get_history_is_chronologically_ordered(db_session, chat_user):
    service = ChatService(db_session, retriever=NullRetriever())
    conversation = await service.create_conversation(chat_user.id)

    for content in ["premier", "deuxième", "troisième"]:
        await service.add_user_message(conversation.id, content)

    history = await service.get_history(conversation.id, chat_user.id)

    assert [message.content for message in history] == ["premier", "deuxième", "troisième"]


@pytest.mark.asyncio
async def test_list_conversations_returns_only_owner_conversations(db_session, chat_user):
    service = UserService(db_session)
    other_user = await service.create_user(
        UserCreate(email=f"other.{uuid.uuid4().hex[:10]}@example.com", password="ValidPass1")
    )

    chat_service = ChatService(db_session, retriever=NullRetriever())
    own_conversation = await chat_service.create_conversation(chat_user.id, title="À moi")
    await chat_service.create_conversation(other_user.id, title="Pas à moi")

    conversations = await chat_service.list_conversations(chat_user.id)

    assert [conversation.id for conversation in conversations] == [own_conversation.id]

    await db_session.delete(other_user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_history_for_another_users_conversation_raises_value_error(db_session, chat_user):
    service = UserService(db_session)
    other_user = await service.create_user(
        UserCreate(email=f"other.{uuid.uuid4().hex[:10]}@example.com", password="ValidPass1")
    )

    chat_service = ChatService(db_session, retriever=NullRetriever())
    conversation = await chat_service.create_conversation(other_user.id)

    with pytest.raises(ValueError):
        await chat_service.get_history(conversation.id, chat_user.id)

    await db_session.delete(other_user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_conversation_unknown_id_raises_value_error(db_session, chat_user):
    service = ChatService(db_session, retriever=NullRetriever())

    with pytest.raises(ValueError):
        await service.get_conversation(uuid.uuid4(), chat_user.id)


__all__: list[str] = []
