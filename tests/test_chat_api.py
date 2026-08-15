"""Tests HTTP de api/chat.py : les 4 routes de chat protégées par JWT (tâche 3.9).

Le fournisseur LLM réel est remplacé par un fournisseur factice via
`app.dependency_overrides`, pour des tests rapides et déterministes. Un test
d'intégration réel avec Gemini est ajouté en complément, en bout de fichier.
"""
import uuid

import pytest
import pytest_asyncio
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMService
from app.ai.providers.base import LLMProvider, Message as LLMMessage
from app.api.chat import get_chat_service
from app.core.config import settings
from app.core.dependencies import get_db_session
from app.main import app
from app.schemas.user import UserCreate
from app.services.chat_service import ChatService
from app.services.user_service import UserService
from conftest import NullRetriever


class FakeProvider(LLMProvider):
    """Fournisseur factice : rejoue une réponse fixe, sans appel réseau."""

    def __init__(self, reply: str = "Réponse factice") -> None:
        self.reply = reply

    async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
        return self.reply


async def _override_get_chat_service(db: AsyncSession = Depends(get_db_session)) -> ChatService:
    return ChatService(db, llm_service=LLMService(provider=FakeProvider()), retriever=NullRetriever())


@pytest_asyncio.fixture(autouse=True)
async def use_fake_llm_provider():
    """Remplace, pour toute la durée du test, le ChatService de l'API par un ChatService factice."""

    app.dependency_overrides[get_chat_service] = _override_get_chat_service
    yield
    app.dependency_overrides.pop(get_chat_service, None)


@pytest_asyncio.fixture
async def chat_user(db_session):
    service = UserService(db_session)
    email = f"chatapi.{uuid.uuid4().hex[:10]}@example.com"
    user = await service.create_user(UserCreate(email=email, password="ValidPass1"))
    user_id = user.id  # capturé avant le test : un rollback() y expirerait `user`

    yield user, "ValidPass1"

    still_there = await service.get_user_by_id(user_id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


async def _auth_headers(client, email: str, password: str) -> dict[str, str]:
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_send_message_without_token_is_401(client):
    response = await client.post("/api/v1/chat/message", json={"content": "Bonjour"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_conversations_without_token_is_401(client):
    response = await client.get("/api/v1/chat/conversations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_conversation_without_token_is_401(client):
    response = await client.get(f"/api/v1/chat/conversations/{uuid.uuid4()}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_conversation_without_token_is_401(client):
    response = await client.delete(f"/api/v1/chat/conversations/{uuid.uuid4()}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_send_message_creates_conversation_and_returns_reply(client, chat_user):
    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)

    response = await client.post("/api/v1/chat/message", json={"content": "Bonjour"}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"]
    assert body["message"]["role"] == "assistant"
    assert body["message"]["content"] == "Réponse factice"


@pytest.mark.asyncio
async def test_send_message_reuses_existing_conversation(client, chat_user):
    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)

    first = await client.post("/api/v1/chat/message", json={"content": "premier"}, headers=headers)
    conversation_id = first.json()["conversation_id"]

    second = await client.post(
        "/api/v1/chat/message",
        json={"content": "deuxième", "conversation_id": conversation_id},
        headers=headers,
    )

    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id


@pytest.mark.asyncio
async def test_list_conversations_returns_only_own_conversations(client, chat_user, db_session):
    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)
    await client.post("/api/v1/chat/message", json={"content": "Bonjour"}, headers=headers)

    other_service = UserService(db_session)
    other_user = await other_service.create_user(
        UserCreate(email=f"other.{uuid.uuid4().hex[:10]}@example.com", password="ValidPass1")
    )
    other_headers = await _auth_headers(client, other_user.email, "ValidPass1")
    await client.post("/api/v1/chat/message", json={"content": "Une autre conversation"}, headers=other_headers)

    response = await client.get("/api/v1/chat/conversations", headers=headers)

    assert response.status_code == 200
    conversations = response.json()
    assert len(conversations) == 1

    await db_session.delete(other_user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_conversation_returns_full_history(client, chat_user):
    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)
    sent = await client.post("/api/v1/chat/message", json={"content": "Mon imprimante affiche E17"}, headers=headers)
    conversation_id = sent.json()["conversation_id"]

    response = await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [message["role"] for message in body["messages"]] == ["user", "assistant"]
    assert body["messages"][0]["content"] == "Mon imprimante affiche E17"


@pytest.mark.asyncio
async def test_get_unknown_conversation_is_404(client, chat_user):
    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)

    response = await client.get(f"/api/v1/chat/conversations/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_another_users_conversation_is_404(client, chat_user, db_session):
    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)

    other_service = UserService(db_session)
    other_user = await other_service.create_user(
        UserCreate(email=f"other.{uuid.uuid4().hex[:10]}@example.com", password="ValidPass1")
    )
    other_headers = await _auth_headers(client, other_user.email, "ValidPass1")
    created = await client.post("/api/v1/chat/message", json={"content": "Bonjour"}, headers=other_headers)
    conversation_id = created.json()["conversation_id"]

    response = await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=headers)

    assert response.status_code == 404

    await db_session.delete(other_user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_delete_conversation_removes_it(client, chat_user):
    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)
    sent = await client.post("/api/v1/chat/message", json={"content": "Bonjour"}, headers=headers)
    conversation_id = sent.json()["conversation_id"]

    delete_response = await client.delete(f"/api/v1/chat/conversations/{conversation_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_another_users_conversation_is_404(client, chat_user, db_session):
    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)

    other_service = UserService(db_session)
    other_user = await other_service.create_user(
        UserCreate(email=f"other.{uuid.uuid4().hex[:10]}@example.com", password="ValidPass1")
    )
    other_headers = await _auth_headers(client, other_user.email, "ValidPass1")
    created = await client.post("/api/v1/chat/message", json={"content": "Bonjour"}, headers=other_headers)
    conversation_id = created.json()["conversation_id"]

    response = await client.delete(f"/api/v1/chat/conversations/{conversation_id}", headers=headers)

    assert response.status_code == 404

    await db_session.delete(other_user)
    await db_session.commit()


@pytest.mark.external
@pytest.mark.asyncio
@pytest.mark.skipif(not settings.GEMINI_API_KEY, reason="GEMINI_API_KEY is not configured")
async def test_send_message_real_call_with_gemini_through_http(client, chat_user):
    """Test d'intégration réel : appelle réellement Gemini via la route HTTP (sans override)."""

    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)

    app.dependency_overrides.pop(get_chat_service, None)  # désactive le fournisseur factice pour ce test
    try:
        response = await client.post(
            "/api/v1/chat/message", json={"content": "Réponds uniquement par le mot OK."}, headers=headers
        )
    finally:
        app.dependency_overrides[get_chat_service] = _override_get_chat_service

    assert response.status_code == 200
    assert response.json()["message"]["content"].strip() != ""


__all__: list[str] = []
