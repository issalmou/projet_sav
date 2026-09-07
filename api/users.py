"""Routes de gestion des utilisateurs.

Règles d'accès (voir core/permissions.py) :
- Un utilisateur consulte/modifie son propre profil librement, sauf son
  rôle et son statut de compte (role_id, is_active, is_superuser).
- Le staff (administrateur, responsable SAV) gère les autres comptes dans
  la limite de son périmètre : un responsable SAV ne gère que les clients
  et les techniciens ; un administrateur gère tout sauf les autres
  administrateurs, sauf s'il est super admin (is_superuser=True).
- Le statut `is_superuser` ne suit pas ce périmètre : seul un super admin
  peut l'accorder ou le retirer, et seul un super admin peut gérer un
  compte qui est déjà super admin (voir `can_manage_superuser_flag`).
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.core.permissions import (
    STAFF_ROLES,
    can_manage_role,
    can_manage_superuser_flag,
    get_role_name,
    require_roles,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.role_service import RoleService
from app.services.user_service import UserService
from app.utils.constants import RoleName


router = APIRouter(prefix="/users", tags=["Users"])

SELF_SERVICE_FORBIDDEN_FIELDS = {"role_id", "is_active", "is_superuser"}


@router.get("/status", status_code=status.HTTP_200_OK)
async def users_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "User routes are ready"}


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {
            "description": (
                "Rôle insuffisant, rôle demandé hors du périmètre de l'appelant, "
                "ou tentative d'accorder le statut super admin sans l'être soi-même."
            )
        },
        409: {"description": "Un utilisateur avec cet email existe déjà."},
        422: {"description": "Payload invalide (email, mot de passe ou langue non conformes)."},
    },
)
async def create_user(
    payload: UserCreate,
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Crée un utilisateur. Le rôle demandé doit être dans le périmètre de l'appelant."""

    target_role_name = None
    if payload.role_id is not None:
        target_role = await RoleService(db).get_role_by_id(payload.role_id)
        target_role_name = target_role.name if target_role else None

    if not can_manage_role(current_user, target_role_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to create a user with this role",
        )

    if payload.is_superuser and not can_manage_superuser_flag(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a superuser can grant superuser status",
        )

    try:
        return await UserService(db).create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get(
    "/",
    response_model=list[UserRead],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé au staff)."},
    },
)
async def list_users(
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 50,
    offset: int = 0,
) -> list[User]:
    """Liste les utilisateurs. Un responsable SAV ne voit que les clients et techniciens."""

    role_names = None
    if not current_user.is_superuser and get_role_name(current_user) == RoleName.RESPONSABLE_SAV.value:
        role_names = [RoleName.CLIENT.value, RoleName.TECHNICIEN.value]

    return await UserService(db).list_users(limit=limit, offset=offset, role_names=role_names)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Utilisateur ciblé hors du périmètre de l'appelant."},
        404: {"description": "Utilisateur introuvable."},
    },
)
async def get_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Consulte un utilisateur : soi-même, ou un utilisateur dans le périmètre du staff appelant."""

    target = await UserService(db).get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if current_user.id != target.id and not can_manage_role(current_user, get_role_name(target)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this user")

    return target


@router.put(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {
            "description": (
                "Modification de son propre rôle/statut, utilisateur/rôle hors périmètre, "
                "gestion d'un compte super admin, ou modification du statut super admin sans l'être soi-même."
            )
        },
        404: {"description": "Utilisateur introuvable."},
        409: {"description": "Un utilisateur avec cet email existe déjà."},
        422: {"description": "Payload invalide."},
    },
)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Met à jour un utilisateur : soi-même (hors rôle/statut), ou le staff dans son périmètre."""

    target = await UserService(db).get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_self = current_user.id == target.id
    provided_fields = set(payload.model_dump(exclude_unset=True).keys())

    if is_self:
        if provided_fields & SELF_SERVICE_FORBIDDEN_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot change your own role or account status",
            )
    else:
        if target.is_superuser and not can_manage_superuser_flag(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a superuser can manage a superuser account",
            )

        if not can_manage_role(current_user, get_role_name(target)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot manage this user")

        if "is_superuser" in provided_fields and not can_manage_superuser_flag(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a superuser can change the superuser status of an account",
            )

        if payload.role_id is not None:
            new_role = await RoleService(db).get_role_by_id(payload.role_id)
            new_role_name = new_role.name if new_role else None
            if not can_manage_role(current_user, new_role_name):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not allowed to assign this role",
                )

    try:
        updated = await UserService(db).update_user(user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return updated


__all__ = ["router"]
