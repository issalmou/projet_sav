"""Tests de ai/rag/retriever.py : recherche sémantique (semaine 4, tâche 9).

Utilise un fournisseur d'embeddings factice à vecteurs fixes (déterministe,
sans appel réseau — l'intégration réelle est déjà validée par
tests/test_embedding_providers.py::test_gemini_embedding_real_call).
"""
import uuid

import pytest

from app.ai.embedding_service import EmbeddingService
from app.ai.embeddings.base import EmbeddingProvider
from app.ai.rag.chunker import Chunk
from app.ai.rag.retriever import RetrieverService
from app.ai.rag.vector_store import VectorStore


class FakeEmbeddingProvider(EmbeddingProvider):
    """Retourne un vecteur fixe par texte connu, pour contrôler le classement des résultats."""

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        return [self._vectors[text] for text in texts]


@pytest.fixture
def vector_store(tmp_path) -> VectorStore:
    return VectorStore(persist_directory=tmp_path / "chroma")


def _seed(vector_store: VectorStore, *, text: str, embedding: list[float], category="faq", product_ids=None):
    document_id = uuid.uuid4()
    vector_store.upsert_document_chunks(
        document_id=document_id,
        title=f"Doc: {text[:20]}",
        category=category,
        product_ids=product_ids or [],
        chunks=[Chunk(index=0, text=text)],
        embeddings=[embedding],
    )
    return document_id


@pytest.mark.asyncio
async def test_retrieve_returns_closest_chunk_first(vector_store):
    close_id = _seed(vector_store, text="Erreur E17 : vérifier le capteur papier.", embedding=[1.0, 0.0])
    _seed(vector_store, text="Contenu totalement hors-sujet.", embedding=[-1.0, 0.0])

    embedder = EmbeddingService(provider=FakeEmbeddingProvider({"Mon imprimante affiche E17": [1.0, 0.0]}))
    retriever = RetrieverService(embedder=embedder, vector_store=vector_store, max_distance=10.0)

    chunks = await retriever.retrieve("Mon imprimante affiche E17")

    assert chunks[0].document_id == close_id
    assert chunks[0].text == "Erreur E17 : vérifier le capteur papier."


@pytest.mark.asyncio
async def test_retrieve_with_known_product_also_includes_general_documents(vector_store):
    product_id = uuid.uuid4()
    other_product_id = uuid.uuid4()

    _seed(
        vector_store,
        text="chunk produit cible",
        embedding=[1.0, 0.0],
        category="products",
        product_ids=[product_id],
    )
    _seed(
        vector_store,
        text="chunk autre produit",
        embedding=[1.0, 0.0],
        category="products",
        product_ids=[other_product_id],
    )
    _seed(vector_store, text="chunk general", embedding=[1.0, 0.0])

    embedder = EmbeddingService(provider=FakeEmbeddingProvider({"question": [1.0, 0.0]}))
    retriever = RetrieverService(embedder=embedder, vector_store=vector_store, max_distance=10.0, top_k=10)

    chunks = await retriever.retrieve("question", product_id=product_id)
    texts = {chunk.text for chunk in chunks}

    assert "chunk produit cible" in texts
    assert "chunk general" in texts
    assert "chunk autre produit" not in texts


@pytest.mark.asyncio
async def test_retrieve_without_product_searches_globally(vector_store):
    product_id = uuid.uuid4()
    _seed(vector_store, text="chunk produit", embedding=[1.0, 0.0], category="products", product_ids=[product_id])
    _seed(vector_store, text="chunk general", embedding=[1.0, 0.0])

    embedder = EmbeddingService(provider=FakeEmbeddingProvider({"question": [1.0, 0.0]}))
    retriever = RetrieverService(embedder=embedder, vector_store=vector_store, max_distance=10.0, top_k=10)

    chunks = await retriever.retrieve("question")

    assert {chunk.text for chunk in chunks} == {"chunk produit", "chunk general"}


@pytest.mark.asyncio
async def test_low_confidence_when_nothing_relevant_found(vector_store):
    _seed(vector_store, text="chunk", embedding=[1.0, 0.0])

    embedder = EmbeddingService(provider=FakeEmbeddingProvider({"question": [-1.0, 0.0]}))
    retriever = RetrieverService(embedder=embedder, vector_store=vector_store, max_distance=0.1)

    chunks = await retriever.retrieve("question")

    assert chunks == []
    assert RetrieverService.is_low_confidence(chunks) is True


@pytest.mark.asyncio
async def test_high_confidence_when_relevant_chunk_found(vector_store):
    _seed(vector_store, text="chunk", embedding=[1.0, 0.0])

    embedder = EmbeddingService(provider=FakeEmbeddingProvider({"question": [1.0, 0.0]}))
    retriever = RetrieverService(embedder=embedder, vector_store=vector_store, max_distance=10.0)

    chunks = await retriever.retrieve("question")

    assert RetrieverService.is_low_confidence(chunks) is False


@pytest.mark.asyncio
async def test_empty_question_returns_no_chunks_without_calling_embedder(vector_store):
    embedder = EmbeddingService(provider=FakeEmbeddingProvider({}))  # lèverait KeyError si appelé
    retriever = RetrieverService(embedder=embedder, vector_store=vector_store)

    chunks = await retriever.retrieve("   ")

    assert chunks == []


__all__: list[str] = []
