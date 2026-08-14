"""Stockage vectoriel des chunks documentaires dans ChromaDB."""
from pathlib import Path
from uuid import UUID

import chromadb

from app.ai.rag.chunker import Chunk
from app.core.config import settings

COLLECTION_NAME = "sav_documents"


class VectorStore:
    """Interface autour de la collection ChromaDB des chunks documentaires."""

    def __init__(self, persist_directory: str | Path | None = None) -> None:
        client = chromadb.PersistentClient(path=str(persist_directory or settings.CHROMA_DB_DIR))
        # embedding_function=None : les embeddings sont toujours calculés en
        # amont par EmbeddingService, jamais par ChromaDB lui-même.
        self._collection = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=None)

    def upsert_document_chunks(
        self,
        *,
        document_id: UUID,
        title: str,
        category: str,
        product_ids: list[UUID],
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """Stocke (ou remplace) les chunks d'un document, avec embeddings et métadonnées."""

        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        if not chunks:
            return

        product_id_strings = [str(product_id) for product_id in product_ids]

        self._collection.upsert(
            ids=[_chunk_id(document_id, chunk.index) for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {
                    "document_id": str(document_id),
                    "title": title,
                    "category": category,
                    "chunk_index": chunk.index,
                    "is_general": not product_id_strings,
                    **({"product_ids": product_id_strings} if product_id_strings else {}),
                }
                for chunk in chunks
            ],
        )

    def query(
        self, *, query_embedding: list[float], n_results: int, product_id: UUID | None = None
    ) -> list[tuple[str, dict, float]]:
        """Recherche vectorielle : retourne (texte, métadonnées, distance) triés par pertinence."""

        where = None
        if product_id is not None:
            where = {"$or": [{"product_ids": {"$contains": str(product_id)}}, {"is_general": True}]}

        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        documents = (result["documents"] or [[]])[0]
        metadatas = (result["metadatas"] or [[]])[0]
        distances = (result["distances"] or [[]])[0]

        return list(zip(documents, metadatas, distances))

    def delete_document_chunks(self, document_id: UUID) -> None:
        """Supprime tous les chunks d'un document (ex: avant un ré-upload/ré-indexation)."""

        self._collection.delete(where={"document_id": str(document_id)})

    def get_document_chunks(self, document_id: UUID) -> list[str]:
        """Retourne les textes des chunks stockés pour un document (utilitaire de test/debug)."""

        result = self._collection.get(where={"document_id": str(document_id)})
        return result["documents"] or []

    def get_document_chunk_metadatas(self, document_id: UUID) -> list[dict]:
        """Retourne les métadonnées des chunks stockés pour un document (utilitaire de test/debug)."""

        result = self._collection.get(where={"document_id": str(document_id)}, include=["metadatas"])
        return result["metadatas"] or []

    def count(self) -> int:
        return self._collection.count()


def _chunk_id(document_id: UUID, chunk_index: int) -> str:
    return f"{document_id}:{chunk_index}"


__all__ = ["COLLECTION_NAME", "VectorStore"]
