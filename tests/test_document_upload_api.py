"""Tests HTTP de POST /documents/upload (semaine 4, tâche 3 ; Tâche 2 : indexation obligatoire)."""
import uuid
from pathlib import Path

import pytest
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedding_service import EmbeddingService
from app.ai.embeddings.base import EmbeddingProvider
from app.ai.exceptions import EmbeddingRequestError
from app.ai.rag.vector_store import VectorStore
from app.api.documents import get_document_service
from app.core.config import settings
from app.core.dependencies import get_db_session
from app.main import app
from app.models.document import Document
from app.services.document import DocumentService
from conftest import auth_headers as _auth_headers


class FakeEmbeddingProvider(EmbeddingProvider):
    """Vecteurs déterministes, sans appel réseau (même convention que test_document_indexing.py)."""

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 0.0, 1.0] for text in texts]


class FailingEmbeddingProvider(EmbeddingProvider):
    """Échoue systématiquement, pour tester l'annulation atomique de l'upload."""

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingRequestError("Fournisseur d'embeddings indisponible")


def _override_document_service(tmp_path: Path, *, failing: bool = False):
    """Surcharge `get_document_service` avec un embedder factice et un VectorStore isolé.

    Sans cette surcharge, `upload_document` appellerait désormais réellement
    le fournisseur d'embeddings configuré (Gemini) et écrirait dans le
    ChromaDB persistant de l'application (Tâche 2 : l'indexation est
    obligatoire) — inacceptable pour des tests rapides et déterministes.
    """

    provider = FailingEmbeddingProvider() if failing else FakeEmbeddingProvider()

    async def _override(db: AsyncSession = Depends(get_db_session)) -> DocumentService:
        return DocumentService(
            db, embedder=EmbeddingService(provider=provider), vector_store=VectorStore(persist_directory=tmp_path / "chroma")
        )

    return _override


async def _cleanup_document(db_session, document_id: uuid.UUID) -> None:
    """Supprime le document et son fichier physique (created_by_id est en RESTRICT)."""

    document = await db_session.get(Document, document_id)
    if document is None:
        return

    file_path = Path(document.file_path)
    await db_session.delete(document)
    await db_session.commit()

    if file_path.exists():
        file_path.unlink()


@pytest.mark.asyncio
async def test_responsable_sav_can_upload_txt_document(client, db_session, actors, tmp_path):
    _, responsable_token = actors["responsable"]

    app.dependency_overrides[get_document_service] = _override_document_service(tmp_path)
    try:
        response = await client.post(
            "/api/v1/documents/upload",
            headers=_auth_headers(responsable_token),
            files={"file": ("guide.txt", "Verifiez le capteur papier.".encode(), "text/plain")},
            data={"title": "Guide erreur E17", "category": "faq", "version": "1.0"},
        )
    finally:
        app.dependency_overrides.pop(get_document_service, None)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Guide erreur E17"
    assert body["file_type"] == "txt"
    assert body["category"] == "faq"
    assert body["status"] == "draft"
    assert body["products"] == []
    assert body["created_by"]["id"] == str(actors["responsable"][0].id)
    assert Path(settings.UPLOAD_DIR).exists()

    # Tâche 2 : l'upload réussi implique désormais une indexation réelle.
    indexed_document = await db_session.get(Document, uuid.UUID(body["id"]))
    assert indexed_document.indexed_at is not None

    await _cleanup_document(db_session, uuid.UUID(body["id"]))


@pytest.mark.asyncio
async def test_upload_links_provided_products(client, db_session, actors, product, tmp_path):
    _, responsable_token = actors["responsable"]

    app.dependency_overrides[get_document_service] = _override_document_service(tmp_path)
    try:
        response = await client.post(
            "/api/v1/documents/upload",
            headers=_auth_headers(responsable_token),
            files={"file": ("notice.txt", b"Contenu de notice.", "text/plain")},
            data={"title": "Notice produit", "category": "manuals", "product_ids": [str(product.id)]},
        )
    finally:
        app.dependency_overrides.pop(get_document_service, None)

    assert response.status_code == 201
    body = response.json()
    assert [p["id"] for p in body["products"]] == [str(product.id)]

    await _cleanup_document(db_session, uuid.UUID(body["id"]))


@pytest.mark.asyncio
async def test_upload_returns_500_and_leaves_no_trace_when_indexing_fails(client, db_session, actors, tmp_path):
    """Scénario bout-en-bout (Tâche 2) : échec d'indexation -> 500, aucun document, aucun fichier orphelin."""

    _, responsable_token = actors["responsable"]

    app.dependency_overrides[get_document_service] = _override_document_service(tmp_path, failing=True)
    before_files = set(settings.UPLOAD_DIR.glob("*.txt"))

    try:
        response = await client.post(
            "/api/v1/documents/upload",
            headers=_auth_headers(responsable_token),
            files={"file": ("guide.txt", b"Contenu valide pour extraction et chunking.", "text/plain")},
            data={"title": "Titre indexation KO HTTP", "category": "faq", "version": "1.0"},
        )
    finally:
        app.dependency_overrides.pop(get_document_service, None)

    assert response.status_code == 500
    body = response.json()
    body_text = str(body).lower()
    assert "traceback" not in body_text
    assert "embeddingrequesterror" not in body_text  # jamais le type/message de l'exception interne

    result = await db_session.execute(select(Document).where(Document.title == "Titre indexation KO HTTP"))
    assert result.scalar_one_or_none() is None  # aucun document partiellement créé

    after_files = set(settings.UPLOAD_DIR.glob("*.txt"))
    assert after_files == before_files  # aucun fichier orphelin


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_file_type(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.post(
        "/api/v1/documents/upload",
        headers=_auth_headers(responsable_token),
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
        data={"title": "Fichier interdit", "category": "faq"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_unknown_product_id(client, actors):
    _, responsable_token = actors["responsable"]

    response = await client.post(
        "/api/v1/documents/upload",
        headers=_auth_headers(responsable_token),
        files={"file": ("notice.txt", b"Contenu.", "text/plain")},
        data={"title": "Notice orpheline", "category": "manuals", "product_ids": [str(uuid.uuid4())]},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_rejects_file_too_large(client, actors, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)
    _, responsable_token = actors["responsable"]

    response = await client.post(
        "/api/v1/documents/upload",
        headers=_auth_headers(responsable_token),
        files={"file": ("guide.txt", b"un octet suffit", "text/plain")},
        data={"title": "Trop volumineux", "category": "faq"},
    )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_client_cannot_upload_document(client, actors):
    _, client_token = actors["client"]

    response = await client.post(
        "/api/v1/documents/upload",
        headers=_auth_headers(client_token),
        files={"file": ("guide.txt", b"contenu", "text/plain")},
        data={"title": "Guide", "category": "faq"},
    )

    assert response.status_code == 403


__all__: list[str] = []
