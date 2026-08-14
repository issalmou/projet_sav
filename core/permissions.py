"""Contrôle d'accès basé sur les rôles (RBAC).

Ce module fournit une dépendance FastAPI paramétrable pour restreindre une
route à un ou plusieurs rôles autorisés, à partir de l'utilisateur
authentifié (core.dependencies.get_current_user) et de son rôle
(models.role.Role).
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.user import User
from app.utils.constants import RoleName


STAFF_ROLES = (RoleName.ADMINISTRATEUR.value, RoleName.RESPONSABLE_SAV.value)
RESPONSABLE_SAV_MANAGEABLE_ROLES = (RoleName.CLIENT.value, RoleName.TECHNICIEN.value)


def require_roles(*allowed_roles: str):
    """Retourne une dépendance qui n'autorise que les rôles donnés (ou un superuser)."""

    async def _check_role(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.is_superuser:
            return current_user

        user_role_name = current_user.role.name if current_user.role else None

        if user_role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the following roles: {', '.join(allowed_roles)}",
            )

        return current_user

    return _check_role

require_document_manager = require_roles(RoleName.RESPONSABLE_SAV.value)

def get_role_name(user: User) -> str | None:
    """Retourne le nom du rôle d'un utilisateur, ou None s'il n'en a pas."""

    return user.role.name if user.role else None


def can_manage_role(actor: User, target_role_name: str | None) -> bool:
    """Vérifie si `actor` (un membre du staff) peut gérer un utilisateur ayant `target_role_name`.

    - Le super admin (`is_superuser=True`) gère tout, y compris les autres administrateurs.
    - Un administrateur normal gère tout, sauf un autre compte administrateur.
    - Un responsable SAV ne gère que les clients et les techniciens.
    """

    if actor.is_superuser:
        return True

    actor_role = get_role_name(actor)

    if actor_role == RoleName.ADMINISTRATEUR.value:
        return target_role_name != RoleName.ADMINISTRATEUR.value

    if actor_role == RoleName.RESPONSABLE_SAV.value:
        return target_role_name is None or target_role_name in RESPONSABLE_SAV_MANAGEABLE_ROLES

    return False


__all__ = [
    "RESPONSABLE_SAV_MANAGEABLE_ROLES",
    "STAFF_ROLES",
    "can_manage_role",
    "get_role_name",
    "require_document_manager",
    "require_roles",
]
