"""Services liés à l'authentification.

Ce module prépare la couche métier de l'authentification JWT sans
implémenter la logique complète à ce stade de fondation.
"""
from sqlalchemy.ext.asyncio import AsyncSession


class AuthService:
    """Orchestrateur métier pour l'authentification."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def authenticate_user(self, email: str, password: str) -> object:
        """Prévu pour vérifier les identifiants et retourner l'utilisateur."""

        raise NotImplementedError("Authentication logic will be implemented later")

    async def create_access_token(self, subject: str) -> str:
        """Prévu pour générer un jeton d'accès JWT."""

        raise NotImplementedError("JWT generation will be implemented later")

    async def refresh_access_token(self, refresh_token: str) -> str:
        """Prévu pour renouveler un jeton d'accès."""

        raise NotImplementedError("Token refresh will be implemented later")


__all__ = ["AuthService"]