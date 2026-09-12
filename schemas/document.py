"""Schémas Pydantic pour les documents (base de connaissances / RAG, semaine 4)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductRead
from app.schemas.user import UserPublic
from app.utils.constants import DocumentCategory, DocumentStatus, DocumentType


class DocumentUploadMetadata(BaseModel):
    """Métadonnées envoyées aux côtés du fichier lors de l'upload.

    `product_ids` est OBLIGATOIRE (au moins un produit) : chaque document de la
    base de connaissances est rattaché à un ou plusieurs produits existants,
    ce qui permet au RAG de filtrer la recherche documentaire par produit
    (`VectorStore.query(product_id=...)`).
    """

    title: str = Field(min_length=1, max_length=200)
    category: DocumentCategory
    version: str = Field(default="1.0", max_length=30)
    product_ids: list[UUID] = Field(min_length=1)


class DocumentRead(BaseModel):
    """Représentation d'un document exposée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    file_type: DocumentType
    category: DocumentCategory
    status: DocumentStatus
    version: str
    file_name: str
    file_size: int
    created_by: UserPublic
    products: list[ProductRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


__all__ = ["DocumentRead", "DocumentUploadMetadata"]
