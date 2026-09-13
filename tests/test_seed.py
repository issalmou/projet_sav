"""Tests de app/database/seed.py — en particulier la non-régression du
crash en boucle du conteneur observé quand FIRST_ADMIN_PASSWORD ne respecte
pas la politique de mot de passe (ex. le placeholder `change-me` de
.env.example laissé tel quel : pas de majuscule, pas de chiffre)."""
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.config import settings
from app.database.seed import seed_first_admin
from app.models.user import User
from conftest import unique_email


@pytest_asyncio.fixture
async def no_existing_superuser(db_session):
    """Neutralise temporairement les superusers déjà présents dans la base
    de dev partagée : `seed_first_admin` ne fait rien dès qu'il en trouve un,
    ce qui masquerait le comportement testé ici. Restauré après le test."""

    result = await db_session.execute(select(User).where(User.is_superuser.is_(True)))
    existing = result.scalars().all()
    for user in existing:
        user.is_superuser = False
    await db_session.commit()

    yield

    for user in existing:
        row = await db_session.get(User, user.id)
        if row is not None:
            row.is_superuser = True
    await db_session.commit()


@pytest.mark.asyncio
async def test_seed_first_admin_with_invalid_password_does_not_crash(
    no_existing_superuser, monkeypatch, db_session
):
    """Reproduit le crash observé en conteneur : mot de passe sans majuscule
    ni chiffre -> `seed_first_admin` ne doit jamais lever, seulement renoncer
    proprement à créer le super admin."""

    email = unique_email("seed.badpw")
    monkeypatch.setattr(settings, "FIRST_ADMIN_EMAIL", email)
    monkeypatch.setattr(settings, "FIRST_ADMIN_PASSWORD", "change-me")

    await seed_first_admin()  # ne doit lever aucune exception

    created = await db_session.execute(select(User).where(User.email == email))
    assert created.scalar_one_or_none() is None  # rien créé


@pytest.mark.asyncio
async def test_seed_first_admin_with_valid_password_creates_superuser(
    no_existing_superuser, monkeypatch, db_session
):
    email = unique_email("seed.goodpw")
    monkeypatch.setattr(settings, "FIRST_ADMIN_EMAIL", email)
    monkeypatch.setattr(settings, "FIRST_ADMIN_PASSWORD", "ChangeMe123")

    await seed_first_admin()

    created = await db_session.execute(select(User).where(User.email == email))
    user = created.scalar_one_or_none()
    assert user is not None
    assert user.is_superuser is True

    await db_session.delete(user)
    await db_session.commit()


__all__: list[str] = []
