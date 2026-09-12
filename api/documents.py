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
    DocumentIndexingError,
    DocumentPermissionError,
    DocumentService,
    FileTooLargeError,
    ProductNotFoundError,
    UnsupportedFileTypeError,
)


router = APIRouter(prefix="/documents", tags=["Documents"])


async def get_document_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> DocumentService:
    """Fournit un DocumentService lié à la session de la requête.

    Dépendance dédiée (même pattern que `get_ticket_service`/`get_diagnostic_service`)
    pour permettre aux tests d'injecter un embedder/vector_store factices sur
    la route d'upload, sans appel réseau réel ni écriture dans le ChromaDB
    persistant de l'application.
    """

    return DocumentService(db)


@router.get("/status", status_code=status.HTTP_200_OK)
async def documents_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "Document routes are ready"}


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Format de fichier non supporté (attendu : PDF, DOCX ou TXT)."},
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé au Responsable SAV)."},
        404: {"description": "Un des product_ids fournis est introuvable."},
        413: {"description": "Fichier dépassant la taille maximale autorisée."},
        422: {"description": "Métadonnées invalides (title, category, version, ou product_ids vide/absent)."},
        500: {"description": "L'indexation RAG a échoué : l'upload est intégralement annulé."},
    },
)
async def upload_document(
    current_user: Annotated[User, Depends(require_document_manager)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    file: Annotated[UploadFile, File(description="Fichier PDF, DOCX ou TXT")],
    title: Annotated[str, Form()],
    category: Annotated[str, Form()],
    version: Annotated[str, Form()] = "1.0",
    product_ids: Annotated[list[UUID], Form()] = [],  # noqa: B006 (jamais muté ; valeur par défaut en lecture seule)
) -> DocumentRead:
    """Dépose un document dans la base de connaissances (réservé au Responsable SAV).

    `product_ids` est obligatoire (au moins un produit existant) : le document
    est rattaché à ces produits pour permettre le filtrage RAG par produit.
    L'indexation RAG est obligatoire : en cas d'échec, l'upload entier est
    annulé (aucun document ni fichier orphelin conservé) et l'API renvoie 500.
    """

    try:
        metadata = DocumentUploadMetadata(title=title, category=category, version=version, product_ids=product_ids)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())

    try:
        return await document_service.upload_document(file=file, metadata=metadata, created_by=current_user)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except FileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc))
    except DocumentIndexingError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed during indexing. Please try again.",
        )


@router.get(
    "/",
    response_model=list[DocumentRead],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé au Responsable SAV)."},
    },
)
async def list_documents(
    current_user: Annotated[User, Depends(require_document_manager)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[DocumentRead]:
    """Liste les documents ajoutés par le Responsable SAV courant (tous pour un superuser)."""

    return await DocumentService(db).list_documents(current_user)


@router.post(
    "/",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé au Responsable SAV)."},
    },
)
async def create_document_placeholder(
    current_user: Annotated[User, Depends(require_document_manager)],
) -> dict[str, str]:
    """Réservé à un usage futur distinct de l'upload (ex: création sans fichier)."""

    return {"detail": "This endpoint is not implemented; use POST /documents/upload"}


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Document créé par un autre Responsable SAV (non superuser)."},
        404: {"description": "Document introuvable."},
    },
)
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
