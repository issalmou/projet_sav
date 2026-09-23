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


@pytest.mark.asyncio
async def test_me_returns_phone_number(client, auth_user, db_session):
    user, password = auth_user
    await UserService(db_session).update_user(user.id, UserUpdate(phone_number="+33612345678"))

    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    access_token = login.json()["access_token"]

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["phone_number"] == "+33612345678"


@pytest.mark.asyncio
async def test_update_profile_via_patch_me(client, auth_user):
    user, password = auth_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    access_token = login.json()["access_token"]

    response = await client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "full_name": "Nouveau Nom Me",
            "phone_number": "+216 12 345 678",
            "preferred_language": "ar",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Nouveau Nom Me"
    assert data["phone_number"] == "+216 12 345 678"
    assert data["preferred_language"] == "ar"

    # Vérification avec GET /auth/me
    get_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert get_res.status_code == 200
    assert get_res.json()["full_name"] == "Nouveau Nom Me"
    assert get_res.json()["phone_number"] == "+216 12 345 678"


@pytest.mark.asyncio
async def test_update_profile_via_put_me(client, auth_user):
    user, password = auth_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    access_token = login.json()["access_token"]

    response = await client.put(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"full_name": "Nom Modifie PUT"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Nom Modifie PUT"


@pytest.mark.asyncio
async def test_client_and_technicien_can_update_own_profile_via_me(client, actors):
    """Vérifie que les rôles client et technicien peuvent mettre à jour leur profil via /auth/me."""
    client_user, client_token = actors["client"]
    technicien_user, technicien_token = actors["technicien"]

    # Client
    res_client = await client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"full_name": "Client Nom Modifie", "phone_number": "+33600000001"},
    )
    assert res_client.status_code == 200
    assert res_client.json()["full_name"] == "Client Nom Modifie"
    assert res_client.json()["phone_number"] == "+33600000001"

    # Technicien
    res_tech = await client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {technicien_token}"},
        json={"full_name": "Tech Nom Modifie", "phone_number": "+33600000002"},
    )
    assert res_tech.status_code == 200
    assert res_tech.json()["full_name"] == "Tech Nom Modifie"
    assert res_tech.json()["phone_number"] == "+33600000002"


@pytest.mark.asyncio
async def test_update_password_via_me_allows_subsequent_login(client, auth_user):
    user, old_password = auth_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": old_password})
    access_token = login.json()["access_token"]

    response = await client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"password": "NewSecretPassword123"},
    )
    assert response.status_code == 200

    # Ancien mot de passe ne marche plus
    bad_login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": old_password})
    assert bad_login.status_code == 401

    # Nouveau mot de passe fonctionne
    good_login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "NewSecretPassword123"})
    assert good_login.status_code == 200


@pytest.mark.asyncio
async def test_update_email_duplicate_via_me_is_409(client, auth_user, actors):
    user, password = auth_user
    client_user, _ = actors["client"]
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    access_token = login.json()["access_token"]

    response = await client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"email": client_user.email},
    )
    assert response.status_code == 409

