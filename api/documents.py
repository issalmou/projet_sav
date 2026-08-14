"""Routes de gestion documentaire."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.permissions import require_document_manager
from app.models.user import User
from app.schemas.document import DocumentRead, DocumentUploadMetadata
from app.services.document import (
    DocumentPermissionError,
    DocumentService,
    FileTooLargeError,
    ProductNotFoundError,
    UnsupportedFileTypeError,
)


router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/status", status_code=status.HTTP_200_OK)
async def documents_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "Document routes are ready"}


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: Annotated[User, Depends(require_document_manager)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    file: Annotated[UploadFile, File(description="Fichier PDF, DOCX ou TXT")],
    title: Annotated[str, Form()],
    category: Annotated[str, Form()],
    version: Annotated[str, Form()] = "1.0",
    product_ids: Annotated[list[UUID], Form()] = [],  # noqa: B006 (jamais muté ; valeur par défaut en lecture seule)
) -> DocumentRead:
    """Dépose un document dans la base de connaissances (réservé au Responsable SAV)."""

    try:
        metadata = DocumentUploadMetadata(title=title, category=category, version=version, product_ids=product_ids)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())

    try:
        return await DocumentService(db).upload_document(file=file, metadata=metadata, created_by=current_user)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except FileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc))


@router.get("/", response_model=list[DocumentRead], status_code=status.HTTP_200_OK)
async def list_documents(
    current_user: Annotated[User, Depends(require_document_manager)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[DocumentRead]:
    """Liste les documents ajoutés par le Responsable SAV courant (tous pour un superuser)."""

    return await DocumentService(db).list_documents(current_user)


@router.post("/", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_document_placeholder(
    current_user: Annotated[User, Depends(require_document_manager)],
) -> dict[str, str]:
    """Réservé à un usage futur distinct de l'upload (ex: création sans fichier)."""

    return {"detail": "This endpoint is not implemented; use POST /documents/upload"}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(require_document_manager)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Supprime un document de la base de connaissances.

    Réservé au Responsable SAV qui l'a créé (ou à un superuser)."""

    try:
        await DocumentService(db).delete_document(document_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DocumentPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


__all__ = ["router"]
