"""Recherche sémantique dans la base documentaire."""
from dataclasses import dataclass
from uuid import UUID

from app.ai.embedding_service import EmbeddingService
from app.ai.rag.vector_store import VectorStore

DEFAULT_TOP_K = 5
DEFAULT_MAX_DISTANCE = 1.0


@dataclass(frozen=True)
class RetrievedChunk:
    """Un chunk retrouvé, avec son document d'origine et son score de pertinence."""

    text: str
    document_id: UUID
    title: str
    category: str
    distance: float


class RetrieverService:
    """Recherche sémantique : question -> embedding -> recherche vectorielle -> contexte."""

    def __init__(
        self,
        *,
        embedder: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
        top_k: int = DEFAULT_TOP_K,
        max_distance: float = DEFAULT_MAX_DISTANCE,
    ) -> None:
        self._embedder = embedder or EmbeddingService()
        self._vector_store = vector_store or VectorStore()
        self._top_k = top_k
        self._max_distance = max_distance

    async def retrieve(self, question: str, *, product_id: UUID | None = None) -> list[RetrievedChunk]:
        """Retourne les chunks les plus pertinents pour `question`.

        Si `product_id` est connu, la recherche est filtrée aux documents
        associés à ce produit + aux documents généraux (une FAQ générale
        doit rester trouvable même quand le produit du client est connu).
        Si `product_id` est `None`, recherche sémantique globale.
        """

        if not question.strip():
            return []

        [query_embedding] = await self._embedder.embed_texts([question])

        results = self._vector_store.query(
            query_embedding=query_embedding, n_results=self._top_k, product_id=product_id
        )

        return [
            RetrievedChunk(
                text=text,
                document_id=UUID(metadata["document_id"]),
                title=metadata["title"],
                category=metadata["category"],
                distance=distance,
            )
            for text, metadata, distance in results
            if distance <= self._max_distance
        ]

    @staticmethod
    def is_low_confidence(chunks: list["RetrievedChunk"]) -> bool:
        """Vrai si aucun chunk suffisamment pertinent n'a été retrouvé."""

        return len(chunks) == 0


__all__ = ["DEFAULT_MAX_DISTANCE", "DEFAULT_TOP_K", "RetrievedChunk", "RetrieverService"]
