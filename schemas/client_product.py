"""Schémas Pydantic pour l'affectation de produits à un client (table client_products).

Aucune notion d'achat / commande / facture : il s'agit uniquement de
rattacher des produits DÉJÀ existants au catalogue à un utilisateur ayant le
rôle « client », avec une quantité (`qte >= 1`).
"""
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductRead


class ClientProductItem(BaseModel):
    """Un produit existant à affecter au client, avec sa quantité."""

    product_id: UUID
    qte: int = Field(default=1, ge=1, description="Quantité affectée (>= 1).")


class ClientProductAssign(BaseModel):
    """Corps de `POST /clients/{client_id}/products`.

    `items` : produits EXISTANTS à affecter au client. Les doublons de
    `product_id` dans la liste sont fusionnés (dernière quantité gagnante) ;
    un produit déjà affecté voit sa quantité **mise à jour** (upsert).
    """

    items: list[ClientProductItem] = Field(min_length=1)


class ClientProductRead(ProductRead):
    """Un produit affecté à un client, avec la quantité affectée."""

    model_config = ConfigDict(from_attributes=True)

    qte: int


__all__ = ["ClientProductAssign", "ClientProductItem", "ClientProductRead"]
