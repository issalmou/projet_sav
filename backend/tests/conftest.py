"""Fixtures partagées pour les tests de la Semaine 2.

Ces tests utilisent la vraie base PostgreSQL de développement (pas de base
de test séparée). Ils créent leurs propres données (avec des emails
uniques) et les suppriment après coup. Ils nécessitent que le seed ait déjà
été exécuté au moins une fois : `python -m app.database.seed`.

Lancer les tests depuis `backend/` avec `PYTHONPATH=.` :
    PYTHONPATH=. pytest
"""
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database.session import AsyncSessionLocal
from app.main import app
from app.services.role_service import RoleService
from app.utils.constants import RoleName


@pytest_asyncio.fixture
async def client():
    """Client HTTP asynchrone branché directement sur l'application FastAPI (pas de vrai serveur réseau)."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    """Session SQLAlchemy sur la base de développement."""

    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def role_ids(db_session):
    """Identifiants des 4 rôles officiels du CDC (doivent déjà exister via le seed)."""

    service = RoleService(db_session)
    ids = {}
    for role in RoleName:
        role_obj = await service.get_role_by_name(role.value)
        assert role_obj is not None, f"Rôle {role.value} manquant — lance `python -m app.database.seed`"
        ids[role.value] = role_obj.id
    return ids
