"""Service de gestion des rôles.

Ce module centralise la logique métier de création et de consultation des
rôles applicatifs (unicité du nom). Les rôles restent volontairement figés
aux 4 valeurs officielles du CDC (voir utils/constants.py et database/seed.py) :
aucune mise à jour ni suppression n'est exposée, il n'y a donc pas de
route API dédiée à leur gestion.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.schemas.role import RoleCreate


class RoleService:
    """Orchestrateur métier pour la gestion des rôles."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_role_by_id(self, role_id: UUID) -> Role | None:
        """Récupère un rôle par son identifiant."""

        return await self.session.get(Role, role_id)

    async def get_role_by_name(self, name: str) -> Role | None:
        """Récupère un rôle par son nom."""

        result = await self.session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def create_role(self, data: RoleCreate) -> Role:
        """Crée un rôle avec un nom unique."""

        if await self.get_role_by_name(data.name) is not None:
            raise ValueError("Role name already exists")

        role = Role(name=data.name, description=data.description)
        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)
        return role


__all__ = ["RoleService"]
