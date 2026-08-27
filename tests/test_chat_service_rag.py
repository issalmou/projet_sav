"""Tests de l'intégration RAG dans ChatService.send_message (semaine 4, tâche 10)."""
import uuid

import pytest
import pytest_asyncio

from app.ai.llm import LLMService
from app.ai.providers.base import LLMProvider, Message as LLMMessage
from app.ai.rag.retriever import RetrievedChunk
from app.schemas.user import UserCreate
from app.services.chat_service import ChatService
from app.services.user_service import UserService


class FakeProvider(LLMProvider):
    """Fournisseur factice : rejoue une réponse fixe, sans appel réseau."""

    def __init__(self, reply: str = "Réponse factice") -> None:
        self.reply = reply
        self.received_messages: list[LLMMessage] | None = None

    async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
        self.received_messages = messages
        return self.reply


class StubRetriever:
    """Double de RetrieverService : rejoue des chunks fixes (ou une erreur), sans I/O réelle."""

    def __init__(self, chunks: list[RetrievedChunk] | None = None, error: Exception | None = None) -> None:
        self.chunks = chunks or []
        self.error = error
        self.received_calls: list[tuple[str, uuid.UUID | None]] = []

    async def retrieve(self, question: str, *, product_id: uuid.UUID | None = None) -> list[RetrievedChunk]:
        self.received_calls.append((question, product_id))
        if self.error is not None:
            raise self.error
        return self.chunks


def _chunk(text: str = "Vérifiez le capteur papier.") -> RetrievedChunk:
    return RetrievedChunk(text=text, document_id=uuid.uuid4(), title="Guide E17", category="faq", distance=0.1)


@pytest_asyncio.fixture
async def chat_user(db_session):
    service = UserService(db_session)
    email = f"chatrag.{uuid.uuid4().hex[:10]}@example.com"
    user = await service.create_user(UserCreate(email=email, password="ValidPass1"))
    user_id = user.id

    yield user

    still_there = await service.get_user_by_id(user_id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


@pytest.mark.asyncio
async def test_send_message_injects_retrieved_context_into_system_prompt(db_session, chat_user):
    provider = FakeProvider()
    retriever = StubRetriever(chunks=[_chunk("Vérifiez le capteur papier.")])
    chat_service = ChatService(db_session, llm_service=LLMService(provider=provider), retriever=retriever)

    await chat_service.send_message(chat_user, "Mon imprimante affiche E17")

    system_message = provider.received_messages[0]
    assert system_message["role"] == "system"
    assert "Vérifiez le capteur papier." in system_message["content"]
    assert "Guide E17" in system_message["content"]


@pytest.mark.asyncio
async def test_send_message_passes_question_and_product_id_to_retriever(db_session, chat_user):
    provider = FakeProvider()
    retriever = StubRetriever(chunks=[_chunk()])
    product_id = uuid.uuid4()
    chat_service = ChatService(db_session, llm_service=LLMService(provider=provider), retriever=retriever)

    await chat_service.send_message(chat_user, "Mon imprimante affiche E17", product_id=product_id)

    assert retriever.received_calls == [("Mon imprimante affiche E17", product_id)]


@pytest.mark.asyncio
async def test_send_message_asks_for_product_model_when_low_confidence_and_unknown(db_session, chat_user):
    provider = FakeProvider()
    retriever = StubRetriever(chunks=[])  # aucun résultat pertinent
    chat_service = ChatService(db_session, llm_service=LLMService(provider=provider), retriever=retriever)

    await chat_service.send_message(chat_user, "Question hors base de connaissances")

    system_message = provider.received_messages[0]
    assert "modèle" in system_message["content"].lower()


@pytest.mark.asyncio
async def test_send_message_does_not_ask_for_product_model_when_already_known(db_session, chat_user):
    provider = FakeProvider()
    retriever = StubRetriever(chunks=[])  # aucun résultat pertinent, mais produit déjà connu
    chat_service = ChatService(db_session, llm_service=LLMService(provider=provider), retriever=retriever)

    await chat_service.send_message(chat_user, "Question", product_id=uuid.uuid4())

    system_message = provider.received_messages[0]
    assert "modèle" not in system_message["content"].lower()


@pytest.mark.asyncio
async def test_send_message_does_not_ask_for_product_model_when_context_found(db_session, chat_user):
    provider = FakeProvider()
    retriever = StubRetriever(chunks=[_chunk()])
    chat_service = ChatService(db_session, llm_service=LLMService(provider=provider), retriever=retriever)

    await chat_service.send_message(chat_user, "Mon imprimante affiche E17")

    system_message = provider.received_messages[0]
    assert "modèle" not in system_message["content"].lower()


@pytest.mark.asyncio
async def test_send_message_survives_retrieval_failure(db_session, chat_user):
    """Une panne du RAG (ChromaDB, embeddings...) ne doit jamais faire échouer le chat."""

    provider = FakeProvider(reply="Réponse malgré tout")
    retriever = StubRetriever(error=RuntimeError("ChromaDB is unreachable"))
    chat_service = ChatService(db_session, llm_service=LLMService(provider=provider), retriever=retriever)

    conversation, assistant_message = await chat_service.send_message(chat_user, "Bonjour")

    assert assistant_message.content == "Réponse malgré tout"
    system_message = provider.received_messages[0]
    assert "Contexte documentaire" not in system_message["content"]


__all__: list[str] = []
