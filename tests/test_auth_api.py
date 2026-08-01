"""Tests HTTP de api/auth.py : /login, /me, /refresh (tâches 1, 4, 8)."""
import uuid

import pytest
import pytest_asyncio

from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService


@pytest_asyncio.fixture
async def auth_user(db_session):
    """Utilisateur de test avec un mot de passe connu, supprimé après le test."""

    service = UserService(db_session)
    email = f"auth.{uuid.uuid4().hex[:10]}@example.com"
    user = await service.create_user(UserCreate(email=email, password="ValidPass1"))

    yield user, "ValidPass1"

    still_there = await service.get_user_by_id(user.id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


@pytest.mark.asyncio
async def test_login_success_returns_access_and_refresh_tokens(client, auth_user):
    user, password = auth_user

    response = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_is_401(client, auth_user):
    user, _ = auth_user

    response = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "WrongPassword1"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_is_401(client):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "ValidPass1"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token_is_401(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token_returns_profile(client, auth_user):
    user, password = auth_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    access_token = login.json()["access_token"]

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.json()["email"] == user.email


@pytest.mark.asyncio
async def test_me_with_deactivated_account_is_403(client, db_session, auth_user):
    user, password = auth_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    access_token = login.json()["access_token"]

    await UserService(db_session).update_user(user.id, UserUpdate(is_active=False))

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_refresh_with_refresh_token_returns_new_access_token(client, auth_user):
    user, password = auth_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    refresh_token = login.json()["refresh_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_refresh_with_access_token_is_rejected(client, auth_user):
    user, password = auth_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    access_token = login.json()["access_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})

    assert response.status_code == 401
    assert "not a refresh token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_me_with_refresh_token_is_rejected(client, auth_user):
    user, password = auth_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    refresh_token = login.json()["refresh_token"]

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_without_token_is_401(client):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_access_token(client, auth_user):
    user, password = auth_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    access_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    logout_response = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout_response.status_code == 200

    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client, auth_user):
    user, password = auth_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    access_token = login.json()["access_token"]
    refresh_token = login.json()["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_response.status_code == 200

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_after_logout_issues_valid_tokens(client, auth_user):
    user, password = auth_user
    first_login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    first_access_token = first_login.json()["access_token"]

    await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {first_access_token}"})

    second_login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    second_access_token = second_login.json()["access_token"]

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {second_access_token}"})
    assert response.status_code == 200
