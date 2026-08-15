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


class ProductWarrantyRead(BaseModel):
    """Garantie d'un produit (CDC semaine 6 : API Garanties).

    Option A validée : propriété statique du produit (`Product.warranty_months`),
    pas de garantie par instance (aucune date d'achat/expiration dans le modèle).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference: str
    name: str
    warranty_months: int | None


class WarrantyUpdate(BaseModel):
    """Données attendues pour modifier la garantie d'un produit (CDC semaine 6 : API Garanties).

    Option A validée : seule `warranty_months` est modifiable via `/warranties`
    (les autres champs du produit passent par `PATCH /products/{id}`).
    """

    warranty_months: int = Field(ge=0)


__all__ = [
    "ProductBase",
    "ProductCreate",
    "ProductRead",
    "ProductUpdate",
    "ProductWarrantyRead",
    "WarrantyUpdate",
]
