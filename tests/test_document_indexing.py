"""Tests de DocumentService.index_document / index_pending_documents (semaine 4, tâche 7).

Utilise un fournisseur d'embeddings factice (déterministe, sans appel
réseau) : l'intégration avec le vrai fournisseur Gemini est déjà validée par
tests/test_embedding_providers.py::test_gemini_embedding_real_call. Ces
tests-ci portent sur l'orchestration (idempotence, stockage, métadonnées),
pas sur la qualité des embeddings.
"""
from pathlib import Path

import pytest
from sqlalchemy import select

from app.ai.embedding_service import EmbeddingService
from app.ai.embeddings.base import EmbeddingProvider
from app.ai.exceptions import EmbeddingRequestError
from app.ai.rag.vector_store import VectorStore
from app.core.config import settings
from app.models.document import Document
from app.schemas.document import DocumentUploadMetadata
from app.services.document import DocumentIndexingError, DocumentService
from app.utils.constants import DocumentCategory

KNOWLEDGE_BASE_PRODUCTS = Path(__file__).resolve().parents[1] / "knowledge_base" / "products"


class FakeEmbeddingProvider(EmbeddingProvider):
    """Vecteurs déterministes, sans appel réseau."""

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 0.0, 1.0] for text in texts]


class FailingEmbeddingProvider(EmbeddingProvider):
    """Échoue systématiquement, pour simuler une panne du fournisseur d'embeddings."""

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingRequestError("Fournisseur d'embeddings indisponible")


class _BuggyVectorStore:
    """Double qui simule un bug inattendu (pas une EmbeddingError/DocumentLoadError) côté VectorStore."""

    def upsert_document_chunks(self, **kwargs) -> None:
        raise RuntimeError("Bug inattendu dans le VectorStore")

    def delete_document_chunks(self, document_id) -> None:
        pass  # nettoyage best-effort : ne doit jamais lever

    def count(self) -> int:
        return 0


class _FakeUploadFile:
    """Double minimal de `fastapi.UploadFile` pour appeler `upload_document` sans HTTP."""

    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


def _real_docx_document(created_by_id) -> Document:
    """Document pointant vers un vrai fichier métier (pas de contenu fabriqué)."""

    source = KNOWLEDGE_BASE_PRODUCTS / "Prime Châssis en Wallonie 2026.docx"
    assert source.exists(), "Document réel manquant dans knowledge_base/products/"

    return Document(
        title="Prime Châssis en Wallonie 2026",
        file_type="docx",
        category="products",
        file_name=source.name,
        file_path=str(source),
        file_size=source.stat().st_size,
        created_by_id=created_by_id,
    )


def _service(db_session, tmp_path, vector_store: VectorStore | None = None) -> DocumentService:
    return DocumentService(
        db_session,
        embedder=EmbeddingService(provider=FakeEmbeddingProvider()),
        vector_store=vector_store or VectorStore(persist_directory=tmp_path / "chroma"),
    )


@pytest.mark.asyncio
async def test_index_document_stores_chunks_with_embeddings_and_metadata(db_session, sav_user, tmp_path):
    document = _real_docx_document(sav_user.id)
    db_session.add(document)
    await db_session.flush()

    vector_store = VectorStore(persist_directory=tmp_path / "chroma")
    service = _service(db_session, tmp_path, vector_store)

    assert document.indexed_at is None

    chunks = await service.index_document(document)

    assert chunks is not None
    assert len(chunks) > 0
    assert document.indexed_at is not None
    assert vector_store.count() == len(chunks)
    assert len(vector_store.get_document_chunks(document.id)) == len(chunks)

    await db_session.delete(document)
    await db_session.commit()


@pytest.mark.asyncio
async def test_index_document_is_skipped_if_already_processed(db_session, sav_user, tmp_path):
    document = _real_docx_document(sav_user.id)
    db_session.add(document)
    await db_session.flush()

    vector_store = VectorStore(persist_directory=tmp_path / "chroma")
    service = _service(db_session, tmp_path, vector_store)

    first_pass = await service.index_document(document)
    indexed_at_after_first_pass = document.indexed_at
    count_after_first_pass = vector_store.count()

    assert first_pass is not None

    second_pass = await service.index_document(document)

    assert second_pass is None
    assert document.indexed_at == indexed_at_after_first_pass
    assert vector_store.count() == count_after_first_pass  # pas de doublons

    await db_session.delete(document)
    await db_session.commit()


@pytest.mark.asyncio
async def test_index_document_stores_product_ids_metadata(db_session, sav_user, product, tmp_path):
    document = _real_docx_document(sav_user.id)
    document.products = [product]
    db_session.add(document)
    await db_session.flush()

    vector_store = VectorStore(persist_directory=tmp_path / "chroma")
    service = _service(db_session, tmp_path, vector_store)

    await service.index_document(document)

    metadatas = vector_store.get_document_chunk_metadatas(document.id)
    assert all(str(product.id) in metadata["product_ids"] for metadata in metadatas)

    await db_session.delete(document)
    await db_session.commit()


@pytest.mark.asyncio
async def test_index_pending_documents_processes_only_unindexed_ones(db_session, sav_user, tmp_path):
    already_indexed = _real_docx_document(sav_user.id)
    already_indexed.title = "Déjà indexé"
    pending = _real_docx_document(sav_user.id)
    pending.title = "En attente"

    db_session.add_all([already_indexed, pending])
    await db_session.flush()

    vector_store = VectorStore(persist_directory=tmp_path / "chroma")
    service = _service(db_session, tmp_path, vector_store)
    await service.index_document(already_indexed)

    results = await service.index_pending_documents()

    assert pending.id in results
    assert already_indexed.id not in results
    assert len(results[pending.id]) > 0

    await db_session.delete(already_indexed)
    await db_session.delete(pending)
    await db_session.commit()


# --- upload_document : atomicité (indexation obligatoire, Tâche 2) -------------


@pytest.mark.asyncio
async def test_upload_document_indexes_successfully_and_stays_available_for_rag(db_session, sav_user, product, tmp_path):
    vector_store = VectorStore(persist_directory=tmp_path / "chroma")
    service = DocumentService(
        db_session, embedder=EmbeddingService(provider=FakeEmbeddingProvider()), vector_store=vector_store
    )

    document = await service.upload_document(
        file=_FakeUploadFile("guide.txt", b"Verifiez le capteur papier avant de redemarrer l'imprimante."),
        metadata=DocumentUploadMetadata(
            title="Guide upload OK", category=DocumentCategory.FAQ, version="1.0", product_ids=[product.id]
        ),
        created_by=sav_user,
    )

    assert document.id is not None
    assert document.indexed_at is not None
    assert vector_store.count() > 0
    assert len(vector_store.get_document_chunks(document.id)) > 0

    # Reste bien disponible en base (pas seulement en mémoire) après l'opération complète.
    reloaded = await db_session.get(Document, document.id)
    assert reloaded is not None
    assert reloaded.indexed_at is not None

    file_path = Path(document.file_path)
    await db_session.delete(reloaded)
    await db_session.commit()
    file_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_upload_document_rolls_back_everything_when_text_extraction_fails(db_session, sav_user, product, tmp_path):
    """DocumentLoadError (fichier sans texte extractible) -> upload entier annulé, 0 artefact."""

    vector_store = VectorStore(persist_directory=tmp_path / "chroma")
    service = DocumentService(
        db_session, embedder=EmbeddingService(provider=FakeEmbeddingProvider()), vector_store=vector_store
    )

    before_files = set(settings.UPLOAD_DIR.glob("*.txt"))

    with pytest.raises(DocumentIndexingError):
        await service.upload_document(
            file=_FakeUploadFile("vide.txt", b"   "),  # aucun texte extractible -> DocumentLoadError
            metadata=DocumentUploadMetadata(
                title="Titre extraction KO", category=DocumentCategory.FAQ, version="1.0", product_ids=[product.id]
            ),
            created_by=sav_user,
        )

    result = await db_session.execute(select(Document).where(Document.title == "Titre extraction KO"))
    assert result.scalar_one_or_none() is None  # aucun document partiellement créé

    after_files = set(settings.UPLOAD_DIR.glob("*.txt"))
    assert after_files == before_files  # aucun fichier orphelin


@pytest.mark.asyncio
async def test_upload_document_rolls_back_and_cleans_file_when_embedding_fails(db_session, sav_user, product, tmp_path):
    vector_store = VectorStore(persist_directory=tmp_path / "chroma")
    service = DocumentService(
        db_session, embedder=EmbeddingService(provider=FailingEmbeddingProvider()), vector_store=vector_store
    )

    before_files = set(settings.UPLOAD_DIR.glob("*.txt"))

    with pytest.raises(DocumentIndexingError):
        await service.upload_document(
            file=_FakeUploadFile("guide.txt", b"Contenu valide pour extraction et chunking."),
            metadata=DocumentUploadMetadata(
                title="Titre embedding KO", category=DocumentCategory.FAQ, version="1.0", product_ids=[product.id]
            ),
            created_by=sav_user,
        )

    result = await db_session.execute(select(Document).where(Document.title == "Titre embedding KO"))
    assert result.scalar_one_or_none() is None

    after_files = set(settings.UPLOAD_DIR.glob("*.txt"))
    assert after_files == before_files


@pytest.mark.asyncio
async def test_upload_document_rolls_back_and_cleans_file_on_unexpected_indexing_error(
    db_session, sav_user, product, caplog
):
    """Exception inattendue (pas DocumentLoadError/EmbeddingError) -> même garantie d'atomicité, log ERROR."""

    import logging

    service = DocumentService(
        db_session, embedder=EmbeddingService(provider=FakeEmbeddingProvider()), vector_store=_BuggyVectorStore()
    )

    before_files = set(settings.UPLOAD_DIR.glob("*.txt"))

    with caplog.at_level(logging.ERROR):
        with pytest.raises(DocumentIndexingError):
            await service.upload_document(
                file=_FakeUploadFile("guide.txt", b"Contenu valide pour declencher le chunking."),
                metadata=DocumentUploadMetadata(
                    title="Titre bug inattendu", category=DocumentCategory.FAQ, version="1.0", product_ids=[product.id]
                ),
                created_by=sav_user,
            )

    result = await db_session.execute(select(Document).where(Document.title == "Titre bug inattendu"))
    assert result.scalar_one_or_none() is None

    after_files = set(settings.UPLOAD_DIR.glob("*.txt"))
    assert after_files == before_files
    assert any(record.levelname == "ERROR" for record in caplog.records)


__all__: list[str] = []
