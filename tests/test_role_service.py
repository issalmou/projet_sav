"""Tests de services/role_service.py (tâche 3, étendus pour la gestion des rôles).

Les rôles sont limités aux 4 rôles officiels du CDC (tâche 6), déjà
présents en base grâce au seed : `create_role` ne peut donc jamais créer un
5e rôle (son `name` est typé `RoleName`, les 4 valeurs existent déjà) — ces
tests s'appuient sur eux pour `get`/`create`. Les tests de `list_roles`,
`update_role` et `delete_role` utilisent la fixture `extra_role` (rôle créé
directement en base, hors service) pour ne jamais toucher aux 4 rôles
officiels réutilisés par le reste de la suite.
"""
import uuid

import pytest

from app.schemas.role import RoleCreate, RoleUpdate
from app.schemas.user import UserCreate
from app.services.role_service import RoleInUseError, RoleService
from app.services.user_service import UserService
from app.utils.constants import RoleName


@pytest.mark.asyncio
async def test_create_role_with_existing_name_is_rejected(db_session, role_ids):
    service = RoleService(db_session)

    with pytest.raises(ValueError, match="already exists"):
        await service.create_role(RoleCreate(name=RoleName.CLIENT))


@pytest.mark.asyncio
async def test_get_role_by_id_and_by_name_agree(db_session, role_ids):
    service = RoleService(db_session)

    by_id = await service.get_role_by_id(role_ids["technicien"])
    by_name = await service.get_role_by_name("technicien")

    assert by_id is not None
    assert by_id.id == by_name.id


@pytest.mark.asyncio
async def test_list_roles_includes_all_by_default(db_session, role_ids, extra_role):
    service = RoleService(db_session)

    roles = await service.list_roles()

    names = {role.name for role in roles}
    assert names >= {"client", "technicien", "responsable_sav", "administrateur", extra_role.name}


@pytest.mark.asyncio
async def test_list_roles_can_exclude_names(db_session, role_ids, extra_role):
    service = RoleService(db_session)

    roles = await service.list_roles(exclude_names=["administrateur"])

    names = {role.name for role in roles}
    assert "administrateur" not in names
    assert extra_role.name in names


@pytest.mark.asyncio
async def test_update_role_changes_description_only(db_session, extra_role):
    service = RoleService(db_session)

    updated = await service.update_role(extra_role.id, RoleUpdate(description="Nouvelle description"))

    assert updated.name == extra_role.name
    assert updated.description == "Nouvelle description"


@pytest.mark.asyncio
async def test_update_role_missing_is_rejected(db_session, role_ids):
    service = RoleService(db_session)

    with pytest.raises(ValueError, match="not found"):
        await service.update_role(uuid.uuid4(), RoleUpdate(description="x"))


@pytest.mark.asyncio
async def test_delete_role_missing_is_rejected(db_session, role_ids):
    service = RoleService(db_session)

    with pytest.raises(ValueError, match="not found"):
        await service.delete_role(uuid.uuid4())


@pytest.mark.asyncio
async def test_delete_role_blocked_while_users_attached(db_session, extra_role):
    role_service = RoleService(db_session)
    user_service = UserService(db_session)

    email = f"role-in-use.{uuid.uuid4().hex[:10]}@example.com"
    user = await user_service.create_user(UserCreate(email=email, password="ValidPass1", role_id=extra_role.id))

    with pytest.raises(RoleInUseError):
        await role_service.delete_role(extra_role.id)

    # nettoyage : libère le rôle avant que la fixture extra_role ne tente de le supprimer
    await db_session.delete(await user_service.get_user_by_id(user.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_delete_role_succeeds_once_unused(db_session, extra_role):
    service = RoleService(db_session)

    await service.delete_role(extra_role.id)

    assert await service.get_role_by_id(extra_role.id) is None
