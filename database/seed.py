"""Script de peuplement initial de la base de données.

Crée les rôles applicatifs officiels définis par le cahier des charges, ainsi que le tout premier compte super admin,
s'ils n'existent pas déjà. Peut être exécuté plusieurs fois sans effet de
bord (idempotent).
"""
import asyncio

from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.role import RoleCreate
from app.schemas.user import UserCreate
from app.services.role_service import RoleService
from app.services.user_service import UserService
from app.utils.constants import RoleName


ROLE_DESCRIPTIONS: dict[RoleName, str] = {
    RoleName.CLIENT: "Utilisateur final qui sollicite le support (SAV).",
    RoleName.TECHNICIEN: "Intervient sur les diagnostics et les résolutions techniques.",
    RoleName.RESPONSABLE_SAV: "Supervise l'activité SAV et l'équipe de techniciens.",
    RoleName.ADMINISTRATEUR: "Administre la plateforme (utilisateurs, rôles, configuration).",
}


async def seed_roles() -> None:
    """Crée les rôles officiels s'ils n'existent pas déjà."""

    async with AsyncSessionLocal() as session:
        service = RoleService(session)

        for role_name, description in ROLE_DESCRIPTIONS.items():
            if await service.get_role_by_name(role_name.value) is not None:
                continue

            await service.create_role(RoleCreate(name=role_name, description=description))


async def seed_first_admin() -> None:
    """Crée le tout premier compte super admin (is_superuser=True) s'il n'en existe aucun.

    Nécessaire car aucune route API ne peut créer un premier administrateur :
    il faut déjà être administrateur pour en créer un autre.
    """

    async with AsyncSessionLocal() as session:
        # Plusieurs superusers sont valides : on vérifie seulement l'existence.
        existing = await session.execute(select(User).where(User.is_superuser.is_(True)))
        if existing.scalars().first() is not None:
            return

        if not settings.FIRST_ADMIN_EMAIL or not settings.FIRST_ADMIN_PASSWORD:
            print("FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD absents de .env : super admin non créé.")
            return

        admin_role = await RoleService(session).get_role_by_name(RoleName.ADMINISTRATEUR.value)

        try:
            payload = UserCreate(
                email=settings.FIRST_ADMIN_EMAIL,
                password=settings.FIRST_ADMIN_PASSWORD,
                is_superuser=True,
                role_id=admin_role.id if admin_role else None,
            )
        except ValidationError as exc:
            # Une configuration invalide ne doit pas bloquer le démarrage de l'API.
            print(f"FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD invalide(s), super admin non créé : {exc}")
            return

        await UserService(session).create_user(payload)
        print(f"Super admin créé : {settings.FIRST_ADMIN_EMAIL}")


async def main() -> None:
    await seed_roles()
    await seed_first_admin()


if __name__ == "__main__":
    asyncio.run(main())
