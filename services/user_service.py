"""Service de gestion des utilisateurs.

Ce module centralise la logique métier de création, consultation et mise
à jour des utilisateurs : hachage du mot de passe et unicité de l'email.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.document import Document
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserHasDependentsError(Exception):
    """L'utilisateur a des tickets (en tant que client) ou des documents à son
    nom : sa suppression est bloquée en base (`ondelete="RESTRICT"`, cf.
    `models.ticket.Ticket.client_id` / `models.document.Document.created_by_id`)
    pour préserver l'historique — jamais un simple 500 d'IntegrityError.
    """


class UserService:
    """Orchestrateur métier pour la gestion des utilisateurs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Récupère un utilisateur par son identifiant."""

        return await self.session.get(User, user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        """Récupère un utilisateur par son email."""

        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_users(
        self, limit: int = 50, offset: int = 0, role_names: list[str] | None = None
    ) -> list[User]:
        """Liste les utilisateurs avec une pagination simple, filtrable par nom de rôle."""

        query = select(User)
        if role_names is not None:
            query = query.join(Role, User.role_id == Role.id).where(Role.name.in_(role_names))

        result = await self.session.execute(query.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def create_user(self, data: UserCreate) -> User:
        """Crée un utilisateur avec un mot de passe haché."""

        if await self.get_user_by_email(data.email) is not None:
            raise ValueError("Email already registered")

        user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            phone_number=data.phone_number,
            is_active=data.is_active,
            is_superuser=data.is_superuser,
            preferred_language=data.preferred_language,
            consent_given_at=data.consent_given_at,
            role_id=data.role_id,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user_id: UUID, data: UserUpdate) -> User | None:
        """Met à jour partiellement un utilisateur existant."""

        user = await self.get_user_by_id(user_id)
        if user is None:
            return None
        if data.email is not None and data.email != user.email:
            if await self.get_user_by_email(data.email) is not None:
                raise ValueError("Email already registered")

        updates = data.model_dump(exclude_unset=True, exclude={"password"})
        for field, value in updates.items():
            setattr(user, field, value)

        if data.password is not None:
            user.hashed_password = get_password_hash(data.password)

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete_user(self, user_id: UUID) -> None:
        """Supprime un utilisateur. Lève `ValueError` (404) s'il n'existe pas.

        Ses conversations et affectations produit sont supprimées en cascade
        (`ondelete="CASCADE"`). En revanche, un ticket dont il est le client ou
        un document qu'il a créé bloquent la suppression en base
        (`ondelete="RESTRICT"`, historique préservé) : vérifié ici pour
        lever `UserHasDependentsError` (409) plutôt qu'une `IntegrityError`
        brute — même principe que `RoleService.delete_role` (`RoleInUseError`).
        """

        user = await self.get_user_by_id(user_id)
        if user is None:
            raise ValueError("User not found")

        has_ticket = (
            await self.session.execute(select(Ticket.id).where(Ticket.client_id == user_id).limit(1))
        ).scalar_one_or_none()
        if has_ticket is not None:
            raise UserHasDependentsError("User still has tickets and cannot be deleted")

        has_document = (
            await self.session.execute(select(Document.id).where(Document.created_by_id == user_id).limit(1))
        ).scalar_one_or_none()
        if has_document is not None:
            raise UserHasDependentsError("User still has documents and cannot be deleted")

        await self.session.delete(user)
        await self.session.commit()


__all__ = ["UserHasDependentsError", "UserService"]
