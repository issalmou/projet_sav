"""Tests de DocumentService.delete_document et DELETE /documents/{id} (semaine 4, complément).

Chaque Responsable SAV ne peut supprimer que les documents qu'il a lui-même
ajoutés, sauf un superuser (validation métier du 2026-08-08).
"""
import uuid
from pathlib import Path

import pytest

from app.ai.embedding_service import EmbeddingService
from app.ai.embeddings.base import EmbeddingProvider
from app.ai.rag.vector_store import VectorStore
from app.models.document import Document
from app.schemas.user import UserCreate
from app.services.document import DocumentPermissionError, DocumentService
from app.services.user_service import UserService
from conftest import auth_headers as _auth_headers
from conftest import create_and_login


class FakeEmbeddingProvider(EmbeddingProvider):
    async def aembed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


def _document_for(created_by_id, file_path: Path, *, title: str = "Document a supprimer") -> Document:
    file_path.write_text("Contenu du document a supprimer.", encoding="utf-8")
    return Document(
        title=title,
        file_type="txt",
        category="faq",
        file_name=file_path.name,
        file_path=str(file_path),
        file_size=file_path.stat().st_size,
        created_by_id=created_by_id,
    )


@pytest.mark.asyncio
async def test_delete_document_removes_row_file_and_chunks(db_session, sav_user, tmp_path):
    document = _document_for(sav_user.id, tmp_path / "guide.txt")
    db_session.add(document)
    await db_session.flush()

    vector_store = VectorStore(persist_directory=tmp_path / "chroma")
    service = DocumentService(
        db_session, embedder=EmbeddingService(provider=FakeEmbeddingProvider()), vector_store=vector_store
    )

    document_id = document.id
    await service.index_document(document)
    assert vector_store.count() > 0

    await service.delete_document(document_id, sav_user)

    assert await db_session.get(Document, document_id) is None
    assert not (tmp_path / "guide.txt").exists()
    assert vector_store.get_document_chunks(document_id) == []


@pytest.mark.asyncio
async def test_delete_unknown_document_raises_value_error(db_session, sav_user, tmp_path):
    service = DocumentService(db_session, vector_store=VectorStore(persist_directory=tmp_path / "chroma"))

    with pytest.raises(ValueError):
        await service.delete_document(uuid.uuid4(), sav_user)


@pytest.mark.asyncio
async def test_delete_document_forbidden_for_another_responsable_sav(db_session, sav_user, tmp_path):
    other = await UserService(db_session).create_user(
        UserCreate(email=f"otherSav.{uuid.uuid4().hex[:10]}@example.com", password="ValidPass1")
    )

    document = _document_for(sav_user.id, tmp_path / "guide.txt")
    db_session.add(document)
    await db_session.flush()
    document_id = document.id

    service = DocumentService(db_session, vector_store=VectorStore(persist_directory=tmp_path / "chroma"))

    with pytest.raises(DocumentPermissionError):
        await service.delete_document(document_id, other)

    # le document n'a pas ete supprime
    assert await db_session.get(Document, document_id) is not None

    await db_session.delete(document)
    await db_session.delete(other)
    await db_session.commit()


@pytest.mark.asyncio
async def test_superuser_can_delete_document_created_by_someone_else(db_session, sav_user, tmp_path):
    superuser = await UserService(db_session).create_user(
        UserCreate(email=f"super.{uuid.uuid4().hex[:10]}@example.com", password="ValidPass1", is_superuser=True)
    )

    document = _document_for(sav_user.id, tmp_path / "guide.txt")
    db_session.add(document)
    await db_session.flush()
    document_id = document.id

    service = DocumentService(db_session, vector_store=VectorStore(persist_directory=tmp_path / "chroma"))
    await service.delete_document(document_id, superuser)

    assert await db_session.get(Document, document_id) is None

    await db_session.delete(superuser)
    await db_session.commit()


@pytest.mark.asyncio
async def test_delete_document_via_api_returns_204(client, db_session, actors, tmp_path):
    _, responsable_token = actors["responsable"]

    upload = await client.post(
        "/api/v1/documents/upload",
        headers=_auth_headers(responsable_token),
        files={"file": ("guide.txt", b"Contenu.", "text/plain")},
        data={"title": "A supprimer via API", "category": "faq"},
    )
    document_id = upload.json()["id"]
    file_path = Path((await db_session.get(Document, uuid.UUID(document_id))).file_path)

    response = await client.delete(f"/api/v1/documents/{document_id}", headers=_auth_headers(responsable_token))

    assert response.status_code == 204
    assert not file_path.exists()

    not_found = await client.delete(f"/api/v1/documents/{document_id}", headers=_auth_headers(responsable_token))
    assert not_found.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_via_api_forbidden_for_non_creator(client, db_session, actors, role_ids, tmp_path):
    _, responsable_token = actors["responsable"]
    other_responsable, other_responsable_token = await create_and_login(
        client, db_session, role_id=role_ids["responsable_sav"]
    )

    upload = await client.post(
        "/api/v1/documents/upload",
        headers=_auth_headers(responsable_token),
        files={"file": ("guide.txt", b"Contenu.", "text/plain")},
        data={"title": "Pas a toi", "category": "faq"},
    )
    document_id = upload.json()["id"]

    response = await client.delete(
        f"/api/v1/documents/{document_id}", headers=_auth_headers(other_responsable_token)
    )

    assert response.status_code == 403

    # nettoyage : le createur original le supprime, puis le compte extra
    cleanup = await client.delete(f"/api/v1/documents/{document_id}", headers=_auth_headers(responsable_token))
    assert cleanup.status_code == 204

    await db_session.delete(other_responsable)
    await db_session.commit()


__all__: list[str] = []
