"""Tests de core/security.py : hachage des mots de passe et JWT (tâches 1, 7, 8)."""
from app.core import security


def test_password_hash_and_verify():
    hashed = security.get_password_hash("SuperSecret123")

    assert hashed != "SuperSecret123"
    assert security.verify_password("SuperSecret123", hashed)
    assert not security.verify_password("WrongPassword1", hashed)


def test_password_hash_is_salted():
    first_hash = security.get_password_hash("SamePassword1")
    second_hash = security.get_password_hash("SamePassword1")

    assert first_hash != second_hash  # bcrypt utilise un sel aléatoire à chaque appel


def test_access_token_roundtrip():
    token = security.create_access_token("user-123")

    assert security.get_token_subject(token) == "user-123"
    assert security.get_token_type(token) == "access"


def test_refresh_token_has_refresh_type():
    token = security.create_refresh_token("user-123")

    assert security.get_token_subject(token) == "user-123"
    assert security.get_token_type(token) == "refresh"


def test_invalid_token_returns_none():
    assert security.get_token_subject("garbage.token.value") is None
    assert security.get_token_type("garbage.token.value") is None
