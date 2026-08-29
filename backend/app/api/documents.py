"""Routes de gestion documentaire.

Le module expose uniquement des endpoints préparatoires.
La logique métier de gestion documentaire sera ajoutée dans une phase ultérieure.
"""
from fastapi import APIRouter, status


router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/status", status_code=status.HTTP_200_OK)
async def documents_status() -> dict[str, str]:
	"""Retourne un état simple pour valider que le module est branché."""

	return {"message": "Document routes are ready"}


@router.get("/", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def list_documents_placeholder() -> dict[str, str]:
	"""Point d'entrée préparé pour lister les documents."""

	return {"detail": "Document listing will be implemented in a later phase"}


@router.post("/", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def upload_document_placeholder() -> dict[str, str]:
	"""Point d'entrée préparé pour déposer un document."""

	return {"detail": "Document upload will be implemented in a later phase"}


@router.delete("/{document_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def delete_document_placeholder(document_id: str) -> dict[str, str]:
	"""Point d'entrée préparé pour supprimer un document."""

	return {"detail": f"Document {document_id} deletion will be implemented in a later phase"}


__all__ = ["router"]
