"""Modèle ClientProduct.

Association plusieurs-à-plusieurs entre un utilisateur ayant le rôle
« client » et les produits qui lui sont rattachés.

Comme pour DocumentProduct, il n'existe pas d'entité « Client » distincte :
un client est un User dont le rôle est « client ». La colonne porte donc
``user_id`` (et non ``client_id``), même si la contrainte d'unicité est
nommée ``uq_client_product`` pour refléter l'intention métier.

Le rattachement est géré exclusivement par le staff (administrateur /
responsable SAV) ; le client peut le consulter mais jamais le modifier.
"""
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClientProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Association plusieurs-à-plusieurs entre User (rôle client) et Product."""

    __tablename__ = "client_products"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_client_product"),
        CheckConstraint("qte >= 1", name="qte_positive"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Quantité de ce produit affectée au client. >= 1 (contrainte CHECK) : une
    # ligne d'affectation à 0 n'aurait pas de sens métier — pour « ne plus rien
    # affecter », on supprime la ligne (DELETE). Réaffecter le même produit
    # met à jour la quantité (upsert), sans jamais violer uq_client_product.
    qte: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    def __repr__(self) -> str:
        return f"<ClientProduct user_id={self.user_id} product_id={self.product_id} qte={self.qte}>"


__all__ = ["ClientProduct"]
