"""Tests de ChatService : cycle de vie des conversations et historique.

L'orchestration de l'agent (`handle_message`) est testée dans
`test_chat_handle_message.py` ; l'agent lui-même dans `test_agent.py`.
"""
import uuid

import pytest
import pytest_asyncio

from app.ai.llm import LLMService
from app.schemas.client_product import ClientProductItem
from app.schemas.user import UserCreate
from app.services.chat_service import ChatService, ProductNotAssignedError
from app.services.client_product_service import ClientProductService
from app.services.user_service import UserService
from conftest import NullRetriever, ScriptedLLMProvider, unique_email


def _svc(db_session) -> ChatService:
    return ChatService(
        db_session,
        llm_service=LLMService(provider=ScriptedLLMProvider([])),
        retriever=NullRetriever(),
    )


@pytest_asyncio.fixture
async def chat_user(db_session):
    service = UserService(db_session)
    user = await service.create_user(UserCreate(email=unique_email("chat"), password="ValidPass1"))
    user_id = user.id
    yield user
    still_there = await service.get_user_by_id(user_id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


@pytest.mark.asyncio
async def test_open_conversation_sets_user_and_product(db_session, chat_user, product_id):
    conversation = await _svc(db_session).open_conversation(chat_user, product_id)

    assert conversation.id is not None
    assert conversation.user_id == chat_user.id
    assert conversation.product_id == product_id
    assert conversation.pending_ticket_confirmation is False


@pytest.mark.asyncio
async def test_open_conversation_unknown_product_raises_value_error(db_session, chat_user):
    with pytest.raises(ValueError):
        await _svc(db_session).open_conversation(chat_user, uuid.uuid4())


@pytest.mark.asyncio
async def test_client_role_cannot_open_conversation_on_unassigned_product(db_session, role_ids, product_id):
    us = UserService(db_session)
    client = await us.create_user(
        UserCreate(email=unique_email("chatclient"), password="ValidPass1", role_id=role_ids["client"])
    )

    with pytest.raises(ProductNotAssignedError):
        await _svc(db_session).open_conversation(client, product_id)

    await db_session.delete(await us.get_user_by_id(client.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_client_role_can_open_conversation_on_assigned_product(db_session, role_ids, product_id):
    us = UserService(db_session)
    client = await us.create_user(
        UserCreate(email=unique_email("chatclient2"), password="ValidPass1", role_id=role_ids["client"])
    )
    await ClientProductService(db_session).assign_products(
        client.id, [ClientProductItem(product_id=product_id, qte=1)]
    )

    conversation = await _svc(db_session).open_conversation(client, product_id)
    assert conversation.product_id == product_id

    # supprimer le client purge en cascade sa conversation + son client_products
    await db_session.delete(await us.get_user_by_id(client.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_history_is_chronologically_ordered(db_session, chat_user, product_id):
    service = _svc(db_session)
    conversation = await service.open_conversation(chat_user, product_id)

    for content in ["premier", "deuxième", "troisième"]:
        await service.add_user_message(conversation.id, content)

    history = await service.get_history(conversation.id, chat_user.id)
    assert [m.content for m in history] == ["premier", "deuxième", "troisième"]


@pytest.mark.asyncio
async def test_list_conversations_returns_only_owner_conversations(db_session, chat_user, product_id):
    us = UserService(db_session)
    other_user = await us.create_user(UserCreate(email=unique_email("other"), password="ValidPass1"))

    service = _svc(db_session)
    own = await service.open_conversation(chat_user, product_id)
    await service.open_conversation(other_user, product_id)

    conversations = await service.list_conversations(chat_user.id)
    assert [c.id for c in conversations] == [own.id]

    await db_session.delete(other_user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_conversation_of_another_user_raises_value_error(db_session, chat_user, product_id):
    us = UserService(db_session)
    other_user = await us.create_user(UserCreate(email=unique_email("other2"), password="ValidPass1"))

    service = _svc(db_session)
    conversation = await service.open_conversation(other_user, product_id)

    with pytest.raises(ValueError):
        await service.get_conversation(conversation.id, chat_user.id)
    with pytest.raises(ValueError):
        await service.get_history(conversation.id, chat_user.id)

    await db_session.delete(other_user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_conversation_unknown_id_raises_value_error(db_session, chat_user):
    with pytest.raises(ValueError):
        await _svc(db_session).get_conversation(uuid.uuid4(), chat_user.id)


__all__: list[str] = []
