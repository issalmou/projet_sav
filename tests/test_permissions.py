"""Tests de core/permissions.py : logique RBAC pure (tâche 5, 9), sans base de données."""
from types import SimpleNamespace

from app.core.permissions import can_manage_role, can_manage_superuser_flag


def _actor(is_superuser: bool = False, role_name: str | None = None):
    """Construit un faux utilisateur (duck typing : seuls .is_superuser et .role.name comptent)."""

    role = SimpleNamespace(name=role_name) if role_name else None
    return SimpleNamespace(is_superuser=is_superuser, role=role)


def test_superuser_can_manage_everything():
    superuser = _actor(is_superuser=True)

    assert can_manage_role(superuser, "administrateur")
    assert can_manage_role(superuser, "responsable_sav")
    assert can_manage_role(superuser, "client")
    assert can_manage_role(superuser, None)


def test_normal_admin_cannot_manage_another_admin():
    admin = _actor(role_name="administrateur")

    assert not can_manage_role(admin, "administrateur")
    assert can_manage_role(admin, "responsable_sav")
    assert can_manage_role(admin, "technicien")
    assert can_manage_role(admin, "client")


def test_responsable_sav_scope_is_limited():
    responsable = _actor(role_name="responsable_sav")

    assert can_manage_role(responsable, "client")
    assert can_manage_role(responsable, "technicien")
    assert not can_manage_role(responsable, "responsable_sav")
    assert not can_manage_role(responsable, "administrateur")


def test_client_and_technicien_cannot_manage_anyone():
    client = _actor(role_name="client")
    technicien = _actor(role_name="technicien")

    assert not can_manage_role(client, "client")
    assert not can_manage_role(technicien, "technicien")


def test_only_superuser_can_manage_the_superuser_flag():
    assert can_manage_superuser_flag(_actor(is_superuser=True))
    assert not can_manage_superuser_flag(_actor(role_name="administrateur"))
    assert not can_manage_superuser_flag(_actor(role_name="responsable_sav"))
    assert not can_manage_superuser_flag(_actor(role_name="client"))
    assert not can_manage_superuser_flag(_actor())
