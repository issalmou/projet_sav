"""Modèle User.

Le modèle conserve uniquement les champs nécessaires à la fondation du
backend: identité, sécurité, langue préférée, statut et rattachement à un rôle.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.role import Role


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Utilisateur applicatif authentifiable."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    preferred_language: Mapped[str] = mapped_column(String(5), default="fr", nullable=False)

    # Traçabilité du consentement (RGPD)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )
    role: Mapped["Role" | None] = relationship(back_populates="users", lazy="joined")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


__all__ = ["User"]