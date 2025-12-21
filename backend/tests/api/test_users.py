import re
import uuid

import pytest
from sqlmodel import select

from app.core.config import settings
from app.models.user import User, UserRole


API_PREFIX = settings.API_V1_PREFIX


def _extract_token_from_html(html: str) -> str:
    """
    Helper to pull the first 'token=...' from any link in the email HTML.
    Used for both verification and reset flows.
    """
    match = re.search(r"token=([^\"&\s]+)", html)
    if not match:
        raise AssertionError("No token=... found in email HTML")
    return match.group(1)


async def _register_user(api_client, username: str, email: str, password: str) -> dict:
    response = await api_client.post(
        f"{API_PREFIX}/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    return data


async def _verify_latest_email(api_client, fake_email_client) -> dict:
    assert fake_email_client.sent, "No email was sent"
    email = fake_email_client.sent[-1]
    html = email["html_content"]
    token = _extract_token_from_html(html)

    response = await api_client.post(
        f"{API_PREFIX}/email/verify-email",
        json={"token": token},
    )
    assert response.status_code == 200
    user = response.json()
    assert user["email_verified"] is True
    assert user["email"] == email["to_email"]
    return user


async def _create_verified_user_and_token(
    api_client, fake_email_client, username: str, email: str, password: str
) -> tuple[str, str]:
    """
    Register + verify + login, returning (user_id, bearer_token).
    """
    fake_email_client.sent.clear()
    await _register_user(api_client, username, email, password)
    await _verify_latest_email(api_client, fake_email_client)

    login_response = await api_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    data = login_response.json()
    user_id = data["user_id"]
    bearer_token = f"Bearer {data['access_token']}"
    return user_id, bearer_token


async def _create_admin_and_token(
    api_client, fake_email_client, db_session, username: str, email: str, password: str
) -> tuple[str, str]:
    """
    Create a verified user, promote to admin in the DB, and return (admin_id, bearer_token).
    """
    user_id, bearer_token = await _create_verified_user_and_token(
        api_client, fake_email_client, username, email, password
    )

    # Promote to admin via direct DB update for test bootstrap.
    user_uuid = uuid.UUID(user_id)
    user = db_session.exec(select(User).where(User.id == user_uuid)).first()
    assert user is not None
    user.role = UserRole.ADMIN
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.role == UserRole.ADMIN
    return str(user.id), bearer_token


# ---------------------------------------------------------------------------
# Success: user self-service (profile + password)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_user_profile_and_change_password_success(api_client, fake_email_client):
    username = "user_profile_change"
    email = "user_profile_change@example.com"
    original_password = "Us€rPr0f1leP4ss!"
    new_password = "Us€rProf1leP4ssN€w!"

    # Create verified user and login.
    user_id, bearer_token = await _create_verified_user_and_token(
        api_client, fake_email_client, username, email, original_password
    )

    # 1) Get current user profile.
    me_response = await api_client.get(
        f"{API_PREFIX}/users/me",
        headers={"Authorization": bearer_token},
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["id"] == user_id
    assert me_data["email"] == email
    assert me_data["username"] == username

    # 2) Update current user profile (username only to avoid re-verification logic).
    new_username = "user_profile_change_updated"
    update_response = await api_client.patch(
        f"{API_PREFIX}/users/me",
        headers={"Authorization": bearer_token},
        json={"username": new_username},
    )
    assert update_response.status_code == 200
    updated_data = update_response.json()
    assert updated_data["id"] == user_id
    assert updated_data["username"] == new_username
    assert updated_data["email"] == email

    # 3) Change password.
    change_pw_response = await api_client.post(
        f"{API_PREFIX}/users/change-password",
        headers={"Authorization": bearer_token},
        json={
            "current_password": original_password,
            "new_password": new_password,
        },
    )
    assert change_pw_response.status_code == 200
    msg = change_pw_response.json()
    assert msg["message"] == "Password changed successfully"

    # 4) Login with new password works.
    login_new_response = await api_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": new_password},
    )
    assert login_new_response.status_code == 200
    login_new_data = login_new_response.json()
    assert login_new_data["user_id"] == user_id
    assert login_new_data["username"] == new_username


# ---------------------------------------------------------------------------
# Success: admin operations on users (list, get, role, delete)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_admin_list_get_update_role_delete_user_success(api_client, fake_email_client, db_session):
    # Target user the admin will manage.
    target_username = "managed_user"
    target_email = "managed_user@example.com"
    target_password = "ManagedAcc0unt!1"
    target_id, _ = await _create_verified_user_and_token(
        api_client, fake_email_client, target_username, target_email, target_password
    )

    # Admin.
    admin_username = "admin_user"
    admin_email = "admin_user@example.com"
    admin_password = "RootRol3Str0ng!1"
    admin_id, admin_token = await _create_admin_and_token(
        api_client, fake_email_client, db_session, admin_username, admin_email, admin_password
    )

    # 1) Admin list users.
    list_response = await api_client.get(
        f"{API_PREFIX}/users/?skip=0&limit=10",
        headers={"Authorization": admin_token},
    )
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert "data" in list_data
    user_ids = {u["id"] for u in list_data["data"]}
    assert target_id in user_ids
    assert admin_id in user_ids

    # 2) Admin get user by ID.
    get_response = await api_client.get(
        f"{API_PREFIX}/users/{target_id}",
        headers={"Authorization": admin_token},
    )
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["id"] == target_id
    assert get_data["email"] == target_email

    # 3) Admin update user role (guest -> user).
    role_response = await api_client.patch(
        f"{API_PREFIX}/users/{target_id}/role",
        headers={"Authorization": admin_token},
        json={"role": "user"},
    )
    assert role_response.status_code == 200
    role_data = role_response.json()
    assert role_data["id"] == target_id
    assert role_data["role"] == "user"

    # 4) Admin delete user.
    delete_response = await api_client.delete(
        f"{API_PREFIX}/users/{target_id}",
        headers={"Authorization": admin_token},
    )
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    # Confirm in DB the user is gone.
    target_uuid = uuid.UUID(target_id)
    deleted_user = db_session.exec(select(User).where(User.id == target_uuid)).first()
    assert deleted_user is None


# ---------------------------------------------------------------------------
# Fail: unauthenticated access to user self endpoints
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_current_user_profile_unauthenticated_fails(api_client):
    response = await api_client.get(f"{API_PREFIX}/users/me")
    # HTTPBearer raises 403 when Authorization header is missing.
    assert response.status_code == 403


@pytest.mark.anyio
async def test_update_current_user_profile_unauthenticated_fails(api_client):
    response = await api_client.patch(
        f"{API_PREFIX}/users/me",
        json={"username": "should_not_work"},
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_change_password_unauthenticated_fails(api_client):
    response = await api_client.post(
        f"{API_PREFIX}/users/change-password",
        json={"current_password": "irrelevant", "new_password": "AlsoIrrelevant1!"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Fail: non-admin trying to use admin-only endpoints
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_non_admin_cannot_use_admin_endpoints(api_client, fake_email_client, db_session):
    # Create a normal verified user (role GUEST).
    username = "non_admin_user"
    email = "non_admin_user@example.com"
    password = "NonPrivAcc0unt!1"
    user_id, user_token = await _create_verified_user_and_token(
        api_client, fake_email_client, username, email, password
    )

    # 1) List users (admin-only).
    list_response = await api_client.get(
        f"{API_PREFIX}/users/?skip=0&limit=10",
        headers={"Authorization": user_token},
    )
    assert list_response.status_code == 403

    # 2) Get user by ID (admin-only).
    get_response = await api_client.get(
        f"{API_PREFIX}/users/{user_id}",
        headers={"Authorization": user_token},
    )
    assert get_response.status_code == 403

    # 3) Update user role (admin-only).
    role_response = await api_client.patch(
        f"{API_PREFIX}/users/{user_id}/role",
        headers={"Authorization": user_token},
        json={"role": "user"},
    )
    assert role_response.status_code == 403

    # 5) Delete user (admin-only).
    delete_response = await api_client.delete(
        f"{API_PREFIX}/users/{user_id}",
        headers={"Authorization": user_token},
    )
    assert delete_response.status_code == 403


# ---------------------------------------------------------------------------
# Fail: admin endpoints with non-existent user IDs
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_admin_get_update_delete_nonexistent_user_fails(api_client, fake_email_client, db_session):
    # Admin.
    admin_username = "admin_nonexistent"
    admin_email = "admin_nonexistent@example.com"
    admin_password = "SuperRootX!4"
    _, admin_token = await _create_admin_and_token(
        api_client, fake_email_client, db_session, admin_username, admin_email, admin_password
    )

    missing_id = str(uuid.uuid4())

    # 1) Get user by non-existent ID.
    get_response = await api_client.get(
        f"{API_PREFIX}/users/{missing_id}",
        headers={"Authorization": admin_token},
    )
    assert get_response.status_code == 404
    assert "User not found" in get_response.json()["detail"]

    # 2) Update role for non-existent user.
    role_response = await api_client.patch(
        f"{API_PREFIX}/users/{missing_id}/role",
        headers={"Authorization": admin_token},
        json={"role": "user"},
    )
    assert role_response.status_code == 404
    assert "User not found" in role_response.json()["detail"]

    # 3) Delete non-existent user.
    delete_response = await api_client.delete(
        f"{API_PREFIX}/users/{missing_id}",
        headers={"Authorization": admin_token},
    )
    assert delete_response.status_code == 404
    assert "User not found" in delete_response.json()["detail"]


# ---------------------------------------------------------------------------
# Success: get user roles
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_roles_authenticated(api_client, fake_email_client):
    username = "roles_user"
    email = "roles_user@example.com"
    password = "R0lesStr0ngP@ssw0rd!"
    _, token = await _create_verified_user_and_token(
        api_client, fake_email_client, username, email, password
    )

    response = await api_client.get(f"{API_PREFIX}/users/roles", headers={"Authorization": token})
    assert response.status_code == 200
    data = response.json()
    assert "roles" in data
    assert len(data["roles"]) == 3
    assert "guest" in data["roles"]
    assert "user" in data["roles"]
    assert "admin" in data["roles"]


@pytest.mark.anyio
async def test_get_roles_unauthenticated(api_client):
    response = await api_client.get(f"{API_PREFIX}/users/roles")
    # HTTPBearer raises 403 when Authorization header is missing.
    assert response.status_code == 403
