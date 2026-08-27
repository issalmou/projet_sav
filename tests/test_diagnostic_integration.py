"""Test d'intégration bout-en-bout (tâche 9) : Utilisateur -> Chat -> Diagnostic -> RAG -> LLM -> Ticket.

Chat, DiagnosticService, RAG (VectorStore réel + recherche vectorielle
réelle) et création de Ticket sont réels (vraie session PostgreSQL). Seuls
le fournisseur LLM et le fournisseur d'embeddings sont factices — même
convention que test_retriever.py (embeddings à vecteurs fixes, déterministe,
sans appel réseau) et test_diagnostic_service.py (LLM séquencé).

JWT/authentification restent hors périmètre ici (option A validée) : déjà
couverts séparément par test_tickets_api.py (401) et test_auth_api.py.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.ai.embedding_service import EmbeddingService
from app.ai.embeddings.base import EmbeddingProvider
from app.ai.llm import LLMService
from app.ai.providers.base import LLMProvider, Message as LLMMessage
from app.ai.rag.chunker import Chunk
from app.ai.rag.retriever import RetrieverService
from app.ai.rag.vector_store import VectorStore
from app.models.ticket import Ticket
from app.schemas.user import UserCreate
from app.services.diagnostic_service import DiagnosticService
from app.services.ticket_service import TicketService
from app.services.user_service import UserService
from app.utils.constants import DiagnosticStatus


class FakeEmbeddingProvider(EmbeddingProvider):
    """Vecteur fixe par texte connu (déterministe, sans appel réseau)."""

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        return [self._vectors[text] for text in texts]


class SequencedProvider(LLMProvider):
    """Fournisseur LLM factice qui rejoue une réponse différente à chaque appel."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.received_messages_per_call: list[list[LLMMessage]] = []

    async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
        self.received_messages_per_call.append(messages)
        return self.replies.pop(0)


@pytest.fixture
def vector_store(tmp_path) -> VectorStore:
    return VectorStore(persist_directory=tmp_path / "chroma")


def _seed_chunk(vector_store: VectorStore, *, text: str, embedding: list[float], title: str) -> None:
    vector_store.upsert_document_chunks(
        document_id=uuid.uuid4(),
        title=title,
        category="manuals",
        product_ids=[],
        chunks=[Chunk(index=0, text=text)],
        embeddings=[embedding],
    )


@pytest_asyncio.fixture
async def diag_user(db_session):
    service = UserService(db_session)
    email = f"diagint.{uuid.uuid4().hex[:10]}@example.com"
    user = await service.create_user(UserCreate(email=email, password="ValidPass1"))
    user_id = user.id  # capturé avant le test : un rollback() y expirerait `user`

    yield user

    # client_id est en RESTRICT (tâche 3) : supprimer les tickets créés par
    # le diagnostic avant de pouvoir supprimer l'utilisateur.
    await db_session.execute(delete(Ticket).where(Ticket.client_id == user_id))
    await db_session.commit()

    still_there = await service.get_user_by_id(user_id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


def _diagnostic_service(
    db_session, vector_store: VectorStore, embedding_vectors: dict[str, list[float]], replies: list[str]
) -> tuple[DiagnosticService, SequencedProvider]:
    # max_distance par défaut (RetrieverService.DEFAULT_MAX_DISTANCE) : suffisant pour un
    # match exact (distance 0) et pour exclure un chunk hors-sujet (vecteur opposé, distance ~2).
    embedder = EmbeddingService(provider=FakeEmbeddingProvider(embedding_vectors))
    retriever = RetrieverService(embedder=embedder, vector_store=vector_store)
    provider = SequencedProvider(replies)
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=retriever)
    return service, provider


@pytest.mark.asyncio
async def test_diagnostic_uses_real_rag_and_resolves_with_correct_answer(db_session, diag_user, vector_store):
    """Diagnostic + RAG réel : le contexte retrouvé atteint le LLM, la réponse finale est correctement nettoyée."""

    _seed_chunk(
        vector_store,
        text="Vérifiez que le bac papier est correctement inséré et redémarrez l'imprimante.",
        embedding=[1.0, 0.0],
        title="Guide erreur E17",
    )

    # Ordre des appels LLM (ChatService génère aussi le titre) : titre(Q1) -> diagnostic(Q1).
    service, provider = _diagnostic_service(
        db_session,
        vector_store,
        {"Mon imprimante affiche Erreur E17": [1.0, 0.0]},
        ["Erreur E17", "Vérifiez le bac papier comme indiqué dans le guide.\n[STATUT: RESOLU]"],
    )

    result = await service.diagnose(diag_user, "Mon imprimante affiche Erreur E17")

    system_message = provider.received_messages_per_call[1][0]
    assert system_message["role"] == "system"
    assert "Vérifiez que le bac papier est correctement inséré" in system_message["content"]
    assert "Guide erreur E17" in system_message["content"]

    assert result.status is DiagnosticStatus.RESOLVED
    assert result.message.content == "Vérifiez le bac papier comme indiqué dans le guide."
    assert result.ticket is None


@pytest.mark.asyncio
async def test_diagnostic_signals_insufficient_information_when_rag_finds_nothing_relevant(
    db_session, diag_user, vector_store
):
    """RAG réel sans contexte pertinent : l'instruction de faible confiance doit atteindre le LLM."""

    _seed_chunk(vector_store, text="Contenu totalement hors-sujet.", embedding=[-1.0, 0.0], title="Autre document")

    # Ordre des appels LLM (ChatService génère aussi le titre) : titre(Q1) -> diagnostic(Q1).
    service, provider = _diagnostic_service(
        db_session,
        vector_store,
        {"Mon four affiche un code inconnu": [1.0, 0.0]},
        ["Code inconnu four", "Pouvez-vous préciser le modèle de votre four ?\n[STATUT: EN_COURS]"],
    )

    result = await service.diagnose(diag_user, "Mon four affiche un code inconnu")

    system_message = provider.received_messages_per_call[1][0]
    assert "Aucun document pertinent" in system_message["content"]
    assert result.status is DiagnosticStatus.IN_PROGRESS
    assert result.ticket is None


@pytest.mark.asyncio
async def test_full_workflow_user_chat_diagnostic_rag_llm_ticket(db_session, diag_user, vector_store):
    """Parcours complet (tâche 9) : Utilisateur -> Chat -> Diagnostic -> RAG -> LLM -> Ticket.

    `diag_user` est un utilisateur réel authentifiable (mot de passe haché,
    persisté) ; JWT/HTTP ne sont pas exercés dans ce test (option A validée),
    déjà couverts séparément.
    """

    _seed_chunk(
        vector_store,
        text="Vérifiez le fusible thermique du four avant tout remplacement.",
        embedding=[1.0, 0.0],
        title="Guide panne four",
    )

    embedding_vectors = {
        "Mon four ne s'allume plus du tout": [1.0, 0.0],
        "Le fusible est bon, toujours rien après vérification": [1.0, 0.0],
        "Oui, créez le ticket": [1.0, 0.0],
    }
    # Ordre des appels LLM (ChatService génère aussi le titre) :
    # titre(Q1) -> diagnostic(Q1, EN_COURS) -> titre affiné(Q1+Q2) -> diagnostic(Q2, A_ESCALADER)
    # -> confirmation(Q3, OUI, pas de titre : 3e message utilisateur) -> synthèse de la description du ticket
    replies = [
        "Panne four",
        "Avez-vous vérifié le fusible thermique ?\n[STATUT: EN_COURS]",
        "Panne four persistante",
        "Je ne parviens pas à résoudre ce problème malgré la documentation. "
        "Voulez-vous qu'un ticket soit créé ?\n[STATUT: A_ESCALADER]",
        "Très bien, votre ticket va être créé.\n[CONFIRMATION: OUI]",
        "Le four ne s'allume plus malgré la vérification du fusible thermique recommandée "
        "par la documentation ; nécessite une intervention sur place.\n[PRODUIT: AUCUN]",
    ]
    service, provider = _diagnostic_service(db_session, vector_store, embedding_vectors, replies)

    first = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout")
    assert first.status is DiagnosticStatus.IN_PROGRESS
    assert first.ticket is None

    # Le contexte réel retrouvé par le RAG a bien atteint le LLM au 1er tour.
    first_system_message = provider.received_messages_per_call[1][0]
    assert "Vérifiez le fusible thermique du four" in first_system_message["content"]

    second = await service.diagnose(
        diag_user, "Le fusible est bon, toujours rien après vérification", conversation_id=first.conversation.id
    )

    # Sur A_ESCALADER, le ticket n'est PAS créé immédiatement : proposition seulement.
    assert second.status is DiagnosticStatus.ESCALATE
    assert second.ticket is None
    assert second.conversation.pending_ticket_confirmation is True

    third = await service.diagnose(
        diag_user, "Oui, créez le ticket", conversation_id=first.conversation.id
    )

    assert third.status is DiagnosticStatus.ESCALATE
    assert third.ticket is not None
    assert third.conversation.pending_ticket_confirmation is False
    # Description générée par l'appel de synthèse dédié (RAG + LLM), pas la confirmation "oui" :
    assert "Oui, créez le ticket" not in third.ticket.description
    assert "nécessite une intervention sur place" in third.ticket.description
    assert third.ticket.product_id is None  # [PRODUIT: AUCUN] -> jamais d'ID deviné

    # Le ticket est réellement persisté en base (pas seulement en mémoire) :
    # re-lu via une nouvelle requête TicketService, indépendante du résultat en mémoire.
    ticket_service = TicketService(db_session)
    persisted = await ticket_service.get_ticket(third.ticket.id, diag_user)

    assert persisted.id == third.ticket.id
    assert persisted.client_id == diag_user.id
    assert persisted.conversation_id == third.conversation.id
    assert persisted.status == "open"
    assert persisted.title == third.conversation.title


__all__: list[str] = []
