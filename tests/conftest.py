"""Fixtures partagées pour les tests de la Semaine 2.

Ces tests utilisent la vraie base PostgreSQL de développement (pas de base
de test séparée). Ils créent leurs propres données (avec des emails
uniques) et les suppriment après coup. Ils nécessitent que le seed ait déjà
été exécuté au moins une fois : `python -m app.database.seed`.

Lancer les tests depuis `backend/` avec `PYTHONPATH=.` :
    PYTHONPATH=. pytest
"""
import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database.session import AsyncSessionLocal
from app.main import app
from app.models.product import Product
from app.schemas.user import UserCreate
from app.services.role_service import RoleService
from app.services.user_service import UserService
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


def unique_email(prefix: str) -> str:
    """Email de test unique, pour éviter les collisions entre tests."""

    return f"{prefix}.{uuid.uuid4().hex[:10]}@example.com"


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def create_and_login(client, db_session, role_id=None, is_superuser=False):
    """Crée un utilisateur directement via le service (hors API) et retourne (user, access_token)."""

    service = UserService(db_session)
    email = unique_email("rbac")
    user = await service.create_user(
        UserCreate(email=email, password="ValidPass1", role_id=role_id, is_superuser=is_superuser)
    )

    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPass1"})
    token = login.json()["access_token"]

    return user, token


@pytest_asyncio.fixture
async def actors(client, db_session, role_ids):
    """Un utilisateur de chaque rôle (+ un super admin), nettoyés après le test."""

    super_admin, super_token = await create_and_login(
        client, db_session, role_id=role_ids["administrateur"], is_superuser=True
    )
    admin, admin_token = await create_and_login(client, db_session, role_id=role_ids["administrateur"])
    responsable, responsable_token = await create_and_login(client, db_session, role_id=role_ids["responsable_sav"])
    technicien, technicien_token = await create_and_login(client, db_session, role_id=role_ids["technicien"])
    client_user, client_token = await create_and_login(client, db_session, role_id=role_ids["client"])

    yield {
        "super_admin": (super_admin, super_token),
        "admin": (admin, admin_token),
        "responsable": (responsable, responsable_token),
        "technicien": (technicien, technicien_token),
        "client": (client_user, client_token),
    }

    service = UserService(db_session)
    for user, _ in [
        (super_admin, None),
        (admin, None),
        (responsable, None),
        (technicien, None),
        (client_user, None),
    ]:
        still_there = await service.get_user_by_id(user.id)
        if still_there is not None:
            await db_session.delete(still_there)
    await db_session.commit()


@pytest_asyncio.fixture
async def sav_user(db_session):
    """Utilisateur de test jouant le rôle de créateur de document (Responsable SAV)."""

    service = UserService(db_session)
    email = unique_email("sav")
    user = await service.create_user(UserCreate(email=email, password="ValidPass1"))
    user_id = user.id  # capturé avant le test : un rollback() y expirerait `user`

    yield user

    still_there = await service.get_user_by_id(user_id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


@pytest_asyncio.fixture
async def product(db_session):
    """Produit de test utilisé pour l'association many-to-many avec les documents."""

    item = Product(reference=f"REF-{uuid.uuid4().hex[:8]}", name="Imprimante Test")
    db_session.add(item)
    await db_session.commit()

    yield item

    still_there = await db_session.get(Product, item.id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


class NullRetriever:
    """Double de RetrieverService qui ne retourne jamais de contexte.

    Pour les tests de ChatService qui ne portent pas sur le RAG (tâche 10) :
    évite tout appel réseau (embeddings) et tout accès disque (ChromaDB) que
    la construction par défaut de RetrieverService() déclencherait sinon.
    """

    async def retrieve(self, question: str, *, product_id=None) -> list:
        return []


class StubRetriever:
    """Double de RetrieverService qui retourne toujours les mêmes chunks fournis.

    Utilisé pour tester la vérification croisée produit/contexte RAG
    (DiagnosticService._resolve_product_id) sans dépendre d'un vrai VectorStore :
    les chunks passés au constructeur doivent mentionner le produit attendu
    dans leur texte/titre pour que la corroboration réussisse.
    """

    def __init__(self, chunks: list) -> None:
        self._chunks = chunks

    async def retrieve(self, question: str, *, product_id=None) -> list:
        return self._chunks
