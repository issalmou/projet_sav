"""Tests de services/user_service.py (tâche 2)."""
import uuid

import pytest
import pytest_asyncio

from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService


def _unique_email() -> str:
    return f"user.{uuid.uuid4().hex[:10]}@example.com"


@pytest_asyncio.fixture
async def created_user(db_session):
    """Crée un utilisateur de test et le supprime après le test (best-effort)."""

    service = UserService(db_session)
    user = await service.create_user(UserCreate(email=_unique_email(), password="ValidPass1"))

    yield user

    still_there = await service.get_user_by_id(user.id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


@pytest.mark.asyncio
async def test_create_user_hashes_the_password(db_session, created_user):
    assert created_user.hashed_password != "ValidPass1"
    assert created_user.hashed_password.startswith("$2b$")


@pytest.mark.asyncio
async def test_create_user_with_duplicate_email_is_rejected(db_session, created_user):
    service = UserService(db_session)

    with pytest.raises(ValueError, match="already registered"):
        await service.create_user(UserCreate(email=created_user.email, password="AnotherPass1"))


@pytest.mark.asyncio
async def test_get_by_id_and_by_email(db_session, created_user):
    service = UserService(db_session)

    by_id = await service.get_user_by_id(created_user.id)
    by_email = await service.get_user_by_email(created_user.email)

    assert by_id.id == created_user.id
    assert by_email.id == created_user.id


@pytest.mark.asyncio
async def test_update_user_rehashes_password_only_when_provided(db_session, created_user):
    service = UserService(db_session)
    original_hash = created_user.hashed_password

    renamed = await service.update_user(created_user.id, UserUpdate(full_name="Nouveau nom"))
    assert renamed.full_name == "Nouveau nom"
    assert renamed.hashed_password == original_hash  # pas de mot de passe fourni : hash inchangé

    repassworded = await service.update_user(created_user.id, UserUpdate(password="AnotherValid1"))
    assert repassworded.hashed_password != original_hash


@pytest.mark.asyncio
async def test_update_missing_user_returns_none(db_session):
    service = UserService(db_session)

    result = await service.update_user(uuid.uuid4(), UserUpdate(full_name="x"))
    assert result is None
