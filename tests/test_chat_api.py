"""Tests HTTP de api/chat.py : les 4 routes de chat protégées par JWT (tâche 3.9).

Le fournisseur LLM réel est remplacé par un fournisseur factice via
`app.dependency_overrides`, pour des tests rapides et déterministes. Un test
d'intégration réel avec Gemini est ajouté en complément, en bout de fichier.
"""
import uuid

import pytest
import pytest_asyncio
from fastapi import Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMService
from app.ai.providers.base import LLMProvider, Message as LLMMessage
from app.ai.rag.retriever import RetrievedChunk
from app.api.chat import get_chat_service, get_diagnostic_service
from app.core.config import settings
from app.core.dependencies import get_db_session
from app.main import app
from app.models.ticket import Ticket
from app.schemas.user import UserCreate
from app.services.chat_service import ChatService
from app.services.diagnostic_service import DiagnosticService
from app.services.user_service import UserService
from conftest import NullRetriever, StubRetriever


class FakeProvider(LLMProvider):
    """Fournisseur factice : rejoue une réponse fixe, sans appel réseau."""

    def __init__(self, reply: str = "Réponse factice") -> None:
        self.reply = reply

    async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
        return self.reply


async def _override_get_chat_service(db: AsyncSession = Depends(get_db_session)) -> ChatService:
    return ChatService(db, llm_service=LLMService(provider=FakeProvider()), retriever=NullRetriever())


async def _override_get_diagnostic_service(db: AsyncSession = Depends(get_db_session)) -> DiagnosticService:
    """Fournit un DiagnosticService factice pour `POST /chat/message` (utilisé par `send_message`).

    Réponse factice sans marqueur `[STATUT: ...]` : `_extract_status` retombe
    alors sur EN_COURS (comportement de repli déjà couvert par
    `test_diagnostic_service.py`), donc aucun ticket n'est proposé/créé dans
    les tests HTTP existants qui ne testent pas explicitement le diagnostic.
    """

    return DiagnosticService(db, llm_service=LLMService(provider=FakeProvider()), retriever=NullRetriever())


@pytest_asyncio.fixture(autouse=True)
async def use_fake_llm_provider():
    """Remplace, pour toute la durée du test, les services de l'API par des doubles factices."""

    app.dependency_overrides[get_chat_service] = _override_get_chat_service
    app.dependency_overrides[get_diagnostic_service] = _override_get_diagnostic_service
    yield
    app.dependency_overrides.pop(get_chat_service, None)
    app.dependency_overrides.pop(get_diagnostic_service, None)


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
    assert body["ticket_id"] is None  # pas d'escalade sur ce tour


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


class SequencedProvider(LLMProvider):
    """Fournisseur factice qui rejoue une réponse différente à chaque appel (mêmes conventions que test_diagnostic_service.py)."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self._calls = 0

    async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
        self._calls += 1
        if not self.replies:
            raise AssertionError(
                f"SequencedProvider exhausted after {self._calls - 1} scripted replies : "
                "un appel LLM supplémentaire (titre/diagnostic/confirmation/synthèse) n'a pas été "
                "prévu par ce test — ajoutez une réponse scriptée de plus."
            )
        return self.replies.pop(0)


def _override_with_sequenced_replies(replies: list[str], retriever=None):
    """Construit une dépendance de surcharge partageant UN SEUL `SequencedProvider`.

    FastAPI appelle la dépendance à chaque requête HTTP (une nouvelle
    `DiagnosticService` par requête, comme en production) : le provider doit
    donc être créé une seule fois ici, en dehors de `_override`, pour que sa
    liste de réponses se consomme progressivement au fil des requêtes d'un
    même test plutôt que de repartir de zéro à chaque appel.
    """

    provider = SequencedProvider(replies)

    async def _override(db: AsyncSession = Depends(get_db_session)) -> DiagnosticService:
        return DiagnosticService(
            db, llm_service=LLMService(provider=provider), retriever=retriever or NullRetriever()
        )

    return _override


# --- Ticket créé uniquement après confirmation explicite (Tâche 1 révisée) --


@pytest.mark.asyncio
async def test_send_message_creates_ticket_only_after_explicit_confirmation(client, chat_user, db_session):
    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)

    app.dependency_overrides[get_diagnostic_service] = _override_with_sequenced_replies(
        [
            "Four ne s'allume plus",
            "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
            "Panne four ne s'allume plus",
            "Je ne parviens pas à résoudre ce problème. Voulez-vous un ticket ?\n[STATUT: A_ESCALADER]",
            "Très bien, votre ticket va être créé.\n[CONFIRMATION: OUI]",
            "Le four ne s'allume plus malgré la vérification du fusible.\n[PRODUIT: AUCUN]",
        ]
    )

    first = await client.post(
        "/api/v1/chat/message", json={"content": "Mon four ne s'allume plus du tout"}, headers=headers
    )
    conversation_id = first.json()["conversation_id"]

    before = await client.get("/api/v1/tickets/", headers=headers)
    assert before.status_code == 200
    assert before.json() == []

    second = await client.post(
        "/api/v1/chat/message",
        json={"content": "Oui, le fusible est bon, toujours rien", "conversation_id": conversation_id},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["ticket_id"] is None  # proposition seulement, pas encore de ticket

    after_proposal = await client.get("/api/v1/tickets/", headers=headers)
    assert after_proposal.json() == []  # proposition seulement, pas encore de ticket

    third = await client.post(
        "/api/v1/chat/message",
        json={"content": "Oui, créez le ticket", "conversation_id": conversation_id},
        headers=headers,
    )
    assert third.status_code == 200

    after_confirmation = await client.get("/api/v1/tickets/", headers=headers)
    tickets = after_confirmation.json()
    assert len(tickets) == 1
    assert tickets[0]["client"]["id"] == str(user.id)
    assert tickets[0]["description"] == "Le four ne s'allume plus malgré la vérification du fusible."
    assert tickets[0]["product"] is None
    assert third.json()["ticket_id"] == tickets[0]["id"]  # exposé dans la réponse du tour qui confirme

    await db_session.execute(delete(Ticket).where(Ticket.client_id == user.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_send_message_resolves_product_via_rag_and_database(client, chat_user, db_session, product):
    """Scénario bout-en-bout complet : diagnostic non résolu -> proposition -> confirmation
    explicite -> synthèse LLM -> identification produit via RAG -> recherche DB -> ticket.product_id.
    """

    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)

    corroborating_chunk = RetrievedChunk(
        text=f"Guide de dépannage pour {product.name} (référence {product.reference}).",
        document_id=uuid.uuid4(),
        title=f"Manuel {product.name}",
        category="manuals",
        distance=0.1,
    )
    app.dependency_overrides[get_diagnostic_service] = _override_with_sequenced_replies(
        [
            "Four ne s'allume plus",
            "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
            "Panne four ne s'allume plus",
            "Je ne parviens pas à résoudre ce problème. Voulez-vous un ticket ?\n[STATUT: A_ESCALADER]",
            "Très bien, votre ticket va être créé.\n[CONFIRMATION: OUI]",
            f"Panne confirmée sur l'appareil référencé.\n[PRODUIT: {product.reference}]",
        ],
        retriever=StubRetriever([corroborating_chunk]),
    )

    first = await client.post(
        "/api/v1/chat/message", json={"content": "Mon four ne s'allume plus du tout"}, headers=headers
    )
    conversation_id = first.json()["conversation_id"]

    await client.post(
        "/api/v1/chat/message",
        json={"content": "Oui, le fusible est bon, toujours rien", "conversation_id": conversation_id},
        headers=headers,
    )
    third = await client.post(
        "/api/v1/chat/message",
        json={"content": "Oui, créez le ticket", "conversation_id": conversation_id},
        headers=headers,
    )
    assert third.status_code == 200

    tickets_response = await client.get("/api/v1/tickets/", headers=headers)
    tickets = tickets_response.json()
    assert len(tickets) == 1
    assert tickets[0]["product"] is not None
    assert tickets[0]["product"]["id"] == str(product.id)
    assert third.json()["ticket_id"] == tickets[0]["id"]

    await db_session.execute(delete(Ticket).where(Ticket.client_id == user.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_send_message_creates_no_ticket_when_client_declines(client, chat_user):
    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)

    app.dependency_overrides[get_diagnostic_service] = _override_with_sequenced_replies(
        [
            "Four ne s'allume plus",
            "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
            "Panne four ne s'allume plus",
            "Je ne parviens pas à résoudre ce problème. Voulez-vous un ticket ?\n[STATUT: A_ESCALADER]",
            "Entendu, n'hésitez pas à revenir si besoin.\n[CONFIRMATION: NON]",
        ]
    )

    first = await client.post(
        "/api/v1/chat/message", json={"content": "Mon four ne s'allume plus du tout"}, headers=headers
    )
    conversation_id = first.json()["conversation_id"]

    await client.post(
        "/api/v1/chat/message",
        json={"content": "Oui, le fusible est bon, toujours rien", "conversation_id": conversation_id},
        headers=headers,
    )
    third = await client.post(
        "/api/v1/chat/message",
        json={"content": "Non merci, je vais réessayer seul", "conversation_id": conversation_id},
        headers=headers,
    )
    assert third.status_code == 200
    assert third.json()["ticket_id"] is None

    response = await client.get("/api/v1/tickets/", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_send_message_creates_no_ticket_on_resolved_status(client, chat_user):
    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)

    app.dependency_overrides[get_diagnostic_service] = _override_with_sequenced_replies(
        ["Erreur E17", "Vérifiez le bac papier.\n[STATUT: RESOLU]"]
    )

    response = await client.post(
        "/api/v1/chat/message", json={"content": "Mon imprimante affiche Erreur E17"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["ticket_id"] is None

    tickets = await client.get("/api/v1/tickets/", headers=headers)
    assert tickets.json() == []


@pytest.mark.external
@pytest.mark.asyncio
@pytest.mark.skipif(not settings.GEMINI_API_KEY, reason="GEMINI_API_KEY is not configured")
async def test_send_message_real_call_with_gemini_through_http(client, chat_user):
    """Test d'intégration réel : appelle réellement Gemini via la route HTTP (sans override)."""

    user, password = chat_user
    headers = await _auth_headers(client, user.email, password)

    app.dependency_overrides.pop(get_diagnostic_service, None)  # désactive le fournisseur factice pour ce test
    try:
        response = await client.post(
            "/api/v1/chat/message", json={"content": "Réponds uniquement par le mot OK."}, headers=headers
        )
    finally:
        app.dependency_overrides[get_diagnostic_service] = _override_get_diagnostic_service

    assert response.status_code == 200
    assert response.json()["message"]["content"].strip() != ""


__all__: list[str] = []
