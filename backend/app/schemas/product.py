"""Schémas Pydantic pour les produits."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    """Champs partagés par les schémas Product."""

    reference: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=400)
    warranty_months: int | None = Field(default=None, ge=0)


class ProductCreate(ProductBase):
    """Données attendues pour créer un produit."""


class ProductUpdate(BaseModel):
    """Données autorisées pour la mise à jour partielle d'un produit."""

    reference: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=400)
    warranty_months: int | None = Field(default=None, ge=0)


class ProductRead(ProductBase):
    """Représentation complète d'un produit exposée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


__all__ = ["ProductBase", "ProductCreate", "ProductUpdate", "ProductRead"]
