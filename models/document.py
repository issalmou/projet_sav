"""Modèles Document et DocumentProduct.

Un document appartient à la base de connaissances gérée par le Responsable
SAV. Le lien avec les produits est plusieurs-à-plusieurs : chaque document
ajouté doit être rattaché à AU MOINS un produit existant (contrainte
appliquée à l'upload par `DocumentUploadMetadata.product_ids`), afin que le
RAG puisse filtrer la recherche documentaire par produit. La colonne
`is_general` du VectorStore (chunk sans produit) reste supportée pour
compatibilité mais n'est plus produite par le flux d'upload.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.constants import DocumentStatus

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.user import User


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Document de la base de connaissances SAV (manuel, FAQ, procédure...)."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("file_type IN ('pdf', 'docx', 'txt')", name="file_type_valid"),
        CheckConstraint(
            "category IN ('faq', 'manuals', 'procedures', 'products', 'videos')", name="category_valid"
        ),
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="status_valid"),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.DRAFT.value, nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(30), default="1.0", nullable=False)

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # NULL = pas encore indexé pour le RAG (extraction + chunking + embedding
    # + stockage vectoriel). Sert de garde d'idempotence : on
    # ne réindexe pas un document déjà traité (cf. DocumentService.index_document).
    # Même principe que User.consent_given_at / User.tokens_revoked_at : un
    # horodatage nullable qui fait à la fois office de statut et de date.
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # RESTRICT plutôt que CASCADE/SET NULL : on ne veut pas qu'une suppression
    # de compte Responsable SAV efface silencieusement l'attribution des
    # documents qu'il a ajoutés à la base de connaissances partagée.
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    created_by: Mapped["User"] = relationship()
    products: Mapped[list["Product"]] = relationship(
        secondary="document_products", back_populates="documents", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title}>"


class DocumentProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Association plusieurs-à-plusieurs entre Document et Product."""

    __tablename__ = "document_products"
    __table_args__ = (UniqueConstraint("document_id", "product_id", name="uq_document_product"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<DocumentProduct document_id={self.document_id} product_id={self.product_id}>"


__all__ = ["Document", "DocumentProduct"]
