"""Service de gestion des rôles.

Ce module centralise la logique métier de création, consultation, mise à
jour et suppression des rôles applicatifs. Les 4 rôles officiels du CDC
(voir utils/constants.py et database/seed.py) ne sont ni renommables ni
recréables sous un autre nom (RoleUpdate n'expose pas `name`, et `name` est
typé `RoleName` dans RoleCreate) ; la suppression est bloquée tant qu'au
moins un utilisateur y est encore rattaché (voir `RoleInUseError`).
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleCreate, RoleUpdate


class RoleInUseError(Exception):
    """Le rôle existe mais au moins un utilisateur y est encore rattaché.

    Volontairement pas une sous-classe de `ValueError` (réservé au "rôle
    introuvable", même principe que `TicketPermissionError` dans
    ticket_service.py) : la suppression n'est pas invalide en soi, elle est
    juste refusée tant que ce rattachement existe, pour éviter de faire
    perdre silencieusement leurs permissions à des comptes existants (le FK
    `User.role_id` est en `ondelete=SET NULL`).
    """


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

    async def list_roles(self, exclude_names: list[str] | None = None) -> list[Role]:
        """Liste les rôles, en excluant éventuellement certains noms (ex : `administrateur`)."""

        query = select(Role).order_by(Role.name)
        if exclude_names:
            query = query.where(Role.name.notin_(exclude_names))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_role(self, data: RoleCreate) -> Role:
        """Crée un rôle avec un nom unique."""

        if await self.get_role_by_name(data.name) is not None:
            raise ValueError("Role name already exists")

        role = Role(name=data.name, description=data.description)
        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def update_role(self, role_id: UUID, data: RoleUpdate) -> Role:
        """Met à jour la description d'un rôle. Lève `ValueError` (404) s'il n'existe pas."""

        role = await self.get_role_by_id(role_id)
        if role is None:
            raise ValueError("Role not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(role, field, value)

        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def delete_role(self, role_id: UUID) -> None:
        """Supprime un rôle. Lève `ValueError` (404) s'il n'existe pas.

        Lève `RoleInUseError` (409) si au moins un utilisateur a encore ce
        `role_id`, plutôt que de le laisser passer à NULL silencieusement.
        """

        role = await self.get_role_by_id(role_id)
        if role is None:
            raise ValueError("Role not found")

        result = await self.session.execute(select(User.id).where(User.role_id == role_id).limit(1))
        if result.scalar_one_or_none() is not None:
            raise RoleInUseError("Role is still assigned to at least one user")

        await self.session.delete(role)
        await self.session.commit()


__all__ = ["RoleInUseError", "RoleService"]
