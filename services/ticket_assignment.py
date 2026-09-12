"""Affectation automatique d'un ticket à un technicien.

Règle métier (décision validée, PAS une exigence du CDC) :
1. choisir **aléatoirement** un technicien ACTIF (rôle `technicien`,
   `is_active = true`) — chaque technicien actif a une chance égale d'être
   choisi ;
2. si aucun technicien actif n'existe : `None` (le ticket reste non assigné,
   `assigned_technician_id` est nullable — le staff l'affectera à la main).

Concurrence : la sélection aléatoire est **sans état** (elle ne lit aucun
compteur de charge), donc deux créations concurrentes ne peuvent pas se
« marcher dessus » — l'ancien `pg_advisory_xact_lock` (utile seulement pour
sérialiser un « lire la charge puis décider ») n'a plus lieu d'être et a été
retiré. La sélection reste faite dans la transaction qui insère le ticket.
"""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.models.user import User
from app.utils.constants import RoleName


async def pick_technician(session: AsyncSession) -> UUID | None:
    """Retourne l'identifiant d'un technicien actif choisi au hasard, ou `None` si aucun."""

    stmt = (
        select(User.id)
        .join(Role, Role.id == User.role_id)
        .where(Role.name == RoleName.TECHNICIEN.value, User.is_active.is_(True))
        .order_by(func.random())
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()


__all__ = ["pick_technician"]
