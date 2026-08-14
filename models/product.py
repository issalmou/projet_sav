"""Modèle Product.

Ce modèle constitue la base de la gestion des produits référencés par le
futur module tickets, diagnostic et recherche documentaire.
"""
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Produit référencé dans la plateforme."""

    __tablename__ = "products"

    reference: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    warranty_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    documents: Mapped[list["Document"]] = relationship(secondary="document_products", back_populates="products")

    def __repr__(self) -> str:
        return f"<Product id={self.id} reference={self.reference}>"


__all__ = ["Product"]