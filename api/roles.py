"""Routes de gestion des rôles applicatifs.

Règles d'accès (cf. échanges de cadrage, tâche "Gestion des rôles + reset
password" — pas une exigence explicite du CDC) :
- Lecture (`GET`) : staff (administrateur, responsable SAV) ou superuser.
  Le responsable SAV ne voit jamais le rôle `administrateur` (ni dans la
  liste, ni par accès direct à son id), pour l'empêcher de récupérer ce
  `role_id` et de l'utiliser lors de la création/modification d'un
  utilisateur (`api/users.py`, logique de gestion des utilisateurs
  inchangée par ailleurs).
- Écriture (création/modification/suppression) : réservée à l'administrateur
  ou au superuser (`RoleName.ADMINISTRATEUR`, superuser toujours autorisé via
  `require_roles`). Le responsable SAV n'y a pas accès, contrairement à la
  gestion des utilisateurs où il conserve son périmètre habituel.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.permissions import STAFF_ROLES, get_role_name, require_roles
from app.models.user import User
from app.schemas.role import RoleCreate, RoleRead, RoleUpdate
from app.services.role_service import RoleInUseError, RoleService
from app.utils.constants import RoleName


router = APIRouter(prefix="/roles", tags=["Roles"])

_HIDDEN_FROM_RESPONSABLE_SAV = (RoleName.ADMINISTRATEUR.value,)


async def get_role_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> RoleService:
    """Fournit un RoleService lié à la session de la requête (même pattern que `get_product_service`)."""

    return RoleService(db)


def _is_restricted_responsable_sav(user: User) -> bool:
    """Vrai si `user` doit avoir le rôle `administrateur` masqué (responsable SAV non superuser)."""

    return not user.is_superuser and get_role_name(user) == RoleName.RESPONSABLE_SAV.value


@router.get("/status", status_code=status.HTTP_200_OK)
async def roles_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "Role routes are ready"}


@router.post(
    "/",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé à administrateur/superuser)."},
        409: {"description": "Un rôle avec ce nom existe déjà."},
        422: {"description": "Payload invalide."},
    },
)
async def create_role(
    payload: RoleCreate,
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMINISTRATEUR.value))],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> RoleRead:
    """Crée un rôle (réservé à administrateur/superuser)."""

    try:
        return await role_service.create_role(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get(
    "/",
    response_model=list[RoleRead],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé au staff)."},
    },
)
async def list_roles(
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> list[RoleRead]:
    """Liste les rôles. Un responsable SAV ne voit jamais le rôle `administrateur`."""

    exclude = list(_HIDDEN_FROM_RESPONSABLE_SAV) if _is_restricted_responsable_sav(current_user) else None
    return await role_service.list_roles(exclude_names=exclude)


@router.get(
    "/{role_id}",
    response_model=RoleRead,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant, ou rôle `administrateur` hors périmètre du responsable SAV."},
        404: {"description": "Rôle introuvable."},
    },
)
async def get_role(
    role_id: UUID,
    current_user: Annotated[User, Depends(require_roles(*STAFF_ROLES))],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> RoleRead:
    """Retourne un rôle par identifiant. Un responsable SAV ne peut pas accéder au rôle `administrateur`."""

    role = await role_service.get_role_by_id(role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if _is_restricted_responsable_sav(current_user) and role.name in _HIDDEN_FROM_RESPONSABLE_SAV:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this role")

    return role


@router.put(
    "/{role_id}",
    response_model=RoleRead,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé à administrateur/superuser)."},
        404: {"description": "Rôle introuvable."},
        422: {"description": "Payload invalide."},
    },
)
async def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMINISTRATEUR.value))],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> RoleRead:
    """Met à jour la description d'un rôle (réservé à administrateur/superuser). Le nom n'est pas modifiable."""

    try:
        return await role_service.update_role(role_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Jeton JWT manquant, invalide, expiré ou révoqué."},
        403: {"description": "Rôle insuffisant (réservé à administrateur/superuser)."},
        404: {"description": "Rôle introuvable."},
        409: {"description": "Au moins un utilisateur a encore ce rôle."},
    },
)
async def delete_role(
    role_id: UUID,
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMINISTRATEUR.value))],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> None:
    """Supprime un rôle (réservé à administrateur/superuser), refusé si des utilisateurs y sont rattachés."""

    try:
        await role_service.delete_role(role_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RoleInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


__all__ = ["get_role_service", "router"]
