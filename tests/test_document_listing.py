"""Tests de DocumentService.list_documents et GET /documents/ (semaine 4, complément).

Chaque Responsable SAV ne voit que les documents qu'il a lui-même ajoutés,
sauf un superuser qui voit tout — même règle de portée que la suppression.
"""
import uuid

import pytest

from app.models.document import Document
from app.services.document import DocumentService
from app.services.user_service import UserService
from app.schemas.user import UserCreate
from conftest import auth_headers as _auth_headers
from conftest import create_and_login


def _document_for(created_by_id, title: str) -> Document:
    return Document(
        title=title,
        file_type="txt",
        category="faq",
        file_name="guide.txt",
        file_path=f"uploads/{uuid.uuid4()}.txt",
        file_size=10,
        created_by_id=created_by_id,
    )


@pytest.mark.asyncio
async def test_list_documents_is_scoped_to_creator(db_session, sav_user):
    other = await UserService(db_session).create_user(
        UserCreate(email=f"otherSav.{uuid.uuid4().hex[:10]}@example.com", password="ValidPass1")
    )

    mine = _document_for(sav_user.id, "A moi")
    theirs = _document_for(other.id, "Pas a moi")
    db_session.add_all([mine, theirs])
    await db_session.commit()

    service = DocumentService(db_session)
    results = await service.list_documents(sav_user)

    assert [document.id for document in results] == [mine.id]

    await db_session.delete(mine)
    await db_session.delete(theirs)
    await db_session.delete(other)
    await db_session.commit()


@pytest.mark.asyncio
async def test_superuser_sees_documents_from_every_creator(db_session, sav_user):
    superuser = await UserService(db_session).create_user(
        UserCreate(email=f"super.{uuid.uuid4().hex[:10]}@example.com", password="ValidPass1", is_superuser=True)
    )

    mine = _document_for(sav_user.id, "A moi")
    db_session.add(mine)
    await db_session.commit()

    service = DocumentService(db_session)
    results = await service.list_documents(superuser)

    assert mine.id in {document.id for document in results}

    await db_session.delete(mine)
    await db_session.delete(superuser)
    await db_session.commit()


@pytest.mark.asyncio
async def test_list_documents_via_api_is_scoped_to_creator(client, db_session, actors, role_ids):
    _, responsable_token = actors["responsable"]
    other_responsable, other_token = await create_and_login(client, db_session, role_id=role_ids["responsable_sav"])

    own_upload = await client.post(
        "/api/v1/documents/upload",
        headers=_auth_headers(responsable_token),
        files={"file": ("guide.txt", b"Contenu.", "text/plain")},
        data={"title": "A moi via API", "category": "faq"},
    )
    other_upload = await client.post(
        "/api/v1/documents/upload",
        headers=_auth_headers(other_token),
        files={"file": ("guide.txt", b"Contenu.", "text/plain")},
        data={"title": "Pas a moi via API", "category": "faq"},
    )

    response = await client.get("/api/v1/documents/", headers=_auth_headers(responsable_token))

    assert response.status_code == 200
    listed_ids = {doc["id"] for doc in response.json()}
    assert own_upload.json()["id"] in listed_ids
    assert other_upload.json()["id"] not in listed_ids

    # nettoyage
    await client.delete(f"/api/v1/documents/{own_upload.json()['id']}", headers=_auth_headers(responsable_token))
    await client.delete(f"/api/v1/documents/{other_upload.json()['id']}", headers=_auth_headers(other_token))
    await db_session.delete(other_responsable)
    await db_session.commit()


__all__: list[str] = []
