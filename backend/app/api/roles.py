"""Routes de consultation des rôles applicatifs.

Expose les rôles (identifiant + nom) au staff pour la gestion des comptes.
Le responsable SAV ne voit que les rôles qu'il peut attribuer (technicien,
client) ; l'administrateur voit tous les rôles.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.permissions import (
    RESPONSABLE_SAV_MANAGEABLE_ROLES,
    STAFF_ROLES,
    get_role_name,
    require_roles,
)
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleRead
from app.services.role_service import RoleService
from app.utils.constants import RoleName


router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=list[RoleRead])
async def list_roles(
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[Role]:
    """Liste les rôles. Périmètre réduit aux rôles gérables par l'appelant."""

    role_names = None
    if not current_user.is_superuser and get_role_name(current_user) == RoleName.RESPONSABLE_SAV.value:
        role_names = list(RESPONSABLE_SAV_MANAGEABLE_ROLES)

    return await RoleService(db).list_roles(names=role_names)


__all__ = ["router"]