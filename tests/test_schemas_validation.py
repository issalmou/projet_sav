"""Tests de validation Pydantic (tâches 6, 7) : rôles CDC, langue, complexité du mot de passe."""
import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest
from app.schemas.role import RoleCreate
from app.schemas.user import UserCreate, UserUpdate


def test_role_name_must_be_one_of_the_cdc_roles():
    with pytest.raises(ValidationError):
        RoleCreate(name="role_invente")

    role = RoleCreate(name="administrateur")
    assert role.name == "administrateur"


def test_preferred_language_must_be_supported():
    with pytest.raises(ValidationError):
        UserCreate(email="a@example.com", password="ValidPass1", preferred_language="xx")

    user = UserCreate(email="a@example.com", password="ValidPass1", preferred_language="en")
    assert user.preferred_language == "en"


def test_password_requires_uppercase_and_digit():
    with pytest.raises(ValidationError):
        UserCreate(email="a@example.com", password="alllowercase1")

    with pytest.raises(ValidationError):
        UserCreate(email="a@example.com", password="NoDigitsHere")

    user = UserCreate(email="a@example.com", password="ValidPass1")
    assert user.password == "ValidPass1"


def test_user_update_password_complexity_only_checked_if_provided():
    update = UserUpdate(full_name="Just a rename")
    assert update.password is None  # aucune erreur : le mot de passe n'est pas fourni

    with pytest.raises(ValidationError):
        UserUpdate(password="weak")


def test_login_request_does_not_enforce_password_complexity():
    # Un login ne doit jamais rejeter un mot de passe existant à cause d'une
    # règle de complexité ajoutée après coup (tâche 7).
    login = LoginRequest(email="a@example.com", password="simplepassword")
    assert login.password == "simplepassword"
