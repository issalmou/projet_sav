"""Modèle Role.

Ce modèle sert de socle à la gestion des permissions et au rattachement
des utilisateurs à un profil métier.
"""
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Rôle applicatif attribuable à un utilisateur."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name}>"


__all__ = ["Role"]