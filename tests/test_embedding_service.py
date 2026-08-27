"""Tests de app.ai.embedding_service.EmbeddingService (semaine 4, tâche 6).

Tous les cas sont testés avec un fournisseur factice (aucun appel réseau) —
même approche que test_llm_service.py.
"""
import pytest

from app.ai.embedding_service import EmbeddingService
from app.ai.embeddings.base import EmbeddingProvider
from app.ai.exceptions import EmbeddingError, EmbeddingRequestError


class FakeEmbeddingProvider(EmbeddingProvider):
    """Fournisseur factice : rejoue des vecteurs fixes ou lève une erreur donnée."""

    def __init__(self, vectors: list[list[float]] | None = None, error: Exception | None = None) -> None:
        self.vectors = vectors
        self.error = error
        self.received_texts: list[str] | None = None

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        self.received_texts = texts

        if self.error is not None:
            raise self.error

        return self.vectors or []


@pytest.mark.asyncio
async def test_embed_texts_returns_provider_vectors():
    provider = FakeEmbeddingProvider(vectors=[[0.1, 0.2, 0.3]])
    service = EmbeddingService(provider=provider)

    vectors = await service.embed_texts(["Vérifiez le capteur papier."])

    assert vectors == [[0.1, 0.2, 0.3]]


@pytest.mark.asyncio
async def test_embed_texts_forwards_texts_unchanged():
    provider = FakeEmbeddingProvider(vectors=[[0.1], [0.2]])
    service = EmbeddingService(provider=provider)
    texts = ["chunk un", "chunk deux"]

    await service.embed_texts(texts)

    assert provider.received_texts == texts


@pytest.mark.asyncio
async def test_embed_texts_with_empty_list_raises_embedding_error():
    service = EmbeddingService(provider=FakeEmbeddingProvider(vectors=[]))

    with pytest.raises(EmbeddingError):
        await service.embed_texts([])


@pytest.mark.asyncio
async def test_embed_texts_propagates_provider_error():
    provider = FakeEmbeddingProvider(error=EmbeddingRequestError("quota exceeded"))
    service = EmbeddingService(provider=provider)

    with pytest.raises(EmbeddingRequestError):
        await service.embed_texts(["chunk"])


__all__: list[str] = []
