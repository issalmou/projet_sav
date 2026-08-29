"""Tests de services/role_service.py (tâche 3).

Les rôles sont limités aux 4 rôles officiels du CDC (tâche 6), déjà
présents en base grâce au seed : ces tests s'appuient sur eux plutôt que
d'en créer de nouveaux. Le service ne fournit volontairement pas de mise
à jour ni de suppression : les rôles restent figés au vocabulaire du CDC.
"""
import pytest

from app.schemas.role import RoleCreate
from app.services.role_service import RoleService
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
