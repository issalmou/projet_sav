"""Services liés à l'authentification.

Ce module contient la logique métier de l'authentification JWT :
vérification des identifiants et génération/renouvellement des tokens.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.models.user import User
from app.services.user_service import UserService


class AuthService:
    """Orchestrateur métier pour l'authentification."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """Vérifie l'email et le mot de passe, retourne l'utilisateur si valide."""

        result = await self.session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            return None

        if not security.verify_password(password, user.hashed_password):
            return None

        return user

    async def create_access_token(self, subject: str) -> str:
        """Génère un jeton d'accès JWT pour l'utilisateur donné."""

        return security.create_access_token(subject)

    async def create_refresh_token(self, subject: str) -> str:
        """Génère un jeton de renouvellement JWT pour l'utilisateur donné."""

        return security.create_refresh_token(subject)

    async def refresh_access_token(self, refresh_token: str) -> str:
        """Vérifie un refresh token et retourne un nouveau access token."""

        subject = security.get_token_subject(refresh_token)
        if subject is None:
            raise ValueError("Invalid or expired refresh token")

        if security.get_token_type(refresh_token) != "refresh":
            raise ValueError("Provided token is not a refresh token")

        try:
            user_id = UUID(subject)
        except ValueError:
            raise ValueError("Invalid or expired refresh token")

        user = await UserService(self.session).get_user_by_id(user_id)
        if user is None:
            raise ValueError("The user associated with this token no longer exists")

        if not user.is_active:
            raise ValueError("This user account has been deactivated")

        if user.tokens_revoked_at is not None:
            issued_at = security.get_token_issued_at(refresh_token)
            if issued_at is None or issued_at < user.tokens_revoked_at:
                raise ValueError("This refresh token has been revoked, please log in again")

        return security.create_access_token(str(user.id))

    async def logout_user(self, user: User) -> None:
        """Révoque immédiatement tous les tokens (access et refresh) de l'utilisateur."""

        user.tokens_revoked_at = datetime.now(timezone.utc)
        await self.session.commit()


__all__ = ["AuthService"]