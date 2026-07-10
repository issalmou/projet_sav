"""Base déclarative SQLAlchemy 2.0 et mixins réutilisables.

La metadata définit des conventions de nommage stables pour faciliter
les migrations Alembic et éviter les différences de noms entre bases.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles ORM de l'application."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """
    Clé primaire UUID plutôt qu'un entier auto-incrémenté :
    - évite l'énumération d'identifiants séquentiels (exigence Sécurité)
    - facilite la fédération de données entre microservices futurs
    """
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )


class TimestampMixin:
    """Horodatage de création / mise à jour, utile pour l'audit RGPD et le debug."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


__all__ = ["Base", "UUIDPrimaryKeyMixin", "TimestampMixin", "utcnow", "NAMING_CONVENTION"]