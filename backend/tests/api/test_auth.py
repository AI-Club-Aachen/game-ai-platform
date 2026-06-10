import re

import pytest

from app.core.config import settings
from tests.utils import random_email, random_username, strong_password


API_PREFIX = settings.API_V1_PREFIX


def _extract_token_from_html(html: str) -> str:
    # Find the first "token=..." in any link, used for both verify and reset.
    match = re.search(r"token=([^\"&\s]+)", html)
    if not match:
        raise AssertionError("No token=... found in email HTML")
    return match.group(1)


async def _register_user(api_client, username: str, email: str, password: str) -> dict:
    response = await api_client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
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


async def _create_verified_user(api_client, fake_email_client, username: str, email: str, password: str):
    fake_email_client.sent.clear()
    await _register_user(api_client, username, email, password)
    await _verify_latest_email(api_client, fake_email_client)


@pytest.mark.anyio
async def test_auth_happy_path_register_verify_login_reset_password(api_client, fake_email_client):
    username = random_username()
    email = random_email()
    original_password = strong_password()
    new_password = strong_password()

    fake_email_client.sent.clear()

    # 1) Register user -> verification email is sent.
    await _register_user(api_client, username, email, original_password)
    assert len(fake_email_client.sent) == 1
    verification_email = fake_email_client.sent[-1]
    assert "Verify Your Email Address" in verification_email["subject"]

    # 2) Verify email using token from email.
    await _verify_latest_email(api_client, fake_email_client)

    # 3) Login succeeds and returns JWT.
    login_response = await api_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": original_password},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert isinstance(login_data["access_token"], str)
    assert login_data["token_type"] == "bearer"
    assert login_data["username"] == username

    # 4) Request password reset -> reset email sent.
    reset_request_response = await api_client.post(
        f"{API_PREFIX}/auth/request-password-reset",
        json={"email": email},
    )
    assert reset_request_response.status_code == 200
    reset_request_data = reset_request_response.json()
    assert "If email exists" in reset_request_data["message"]

    assert len(fake_email_client.sent) == 2
    reset_email = fake_email_client.sent[-1]
    assert "Password Reset Request" in reset_email["subject"]

    # 5) Extract reset token from email and reset password.
    reset_token = _extract_token_from_html(reset_email["html_content"])
    reset_response = await api_client.post(
        f"{API_PREFIX}/auth/reset-password",
        json={"token": reset_token, "new_password": new_password},
    )
    assert reset_response.status_code == 200
    reset_user = reset_response.json()
    assert reset_user["email"] == email
    assert reset_user["email_verified"] is True

    # 6) Old password no longer works.
    old_login_response = await api_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": original_password},
    )
    assert old_login_response.status_code == 401

    # 7) New password works.
    new_login_response = await api_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": new_password},
    )
    assert new_login_response.status_code == 200
    new_login_data = new_login_response.json()
    assert isinstance(new_login_data["access_token"], str)
    assert new_login_data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_fails_if_email_not_verified(api_client, fake_email_client):
    username = random_username()
    email = random_email()
    password = strong_password()

    fake_email_client.sent.clear()

    await _register_user(api_client, username, email, password)

    response = await api_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 403
    data = response.json()
    assert "Email not verified" in data["detail"]


@pytest.mark.anyio
async def test_login_fails_with_wrong_credentials(api_client, fake_email_client):
    username = random_username()
    email = random_email()
    password = strong_password()
    wrong_password = strong_password()

    await _create_verified_user(api_client, fake_email_client, username, email, password)

    response = await api_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": wrong_password},
    )
    assert response.status_code == 401
    data = response.json()
    assert "Invalid email or password" in data["detail"]


@pytest.mark.anyio
async def test_register_fails_if_user_already_exists(api_client, fake_email_client):
    username = random_username()
    email = random_email()
    password = strong_password()

    await _create_verified_user(api_client, fake_email_client, username, email, password)

    response = await api_client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 409
    data = response.json()
    assert any(msg in data["detail"] for msg in ("Username already registered", "Email already registered"))


@pytest.mark.anyio
async def test_register_fails_with_readable_invalid_username(api_client):
    response = await api_client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "username": "user@example.com",
            "email": random_email(),
            "password": strong_password(),
        },
    )

    assert response.status_code == 422
    data = response.json()
    messages = [error["msg"] for error in data["detail"]]
    assert any(
        "Username can only contain letters, numbers, underscores, and hyphens" in message for message in messages
    )
    assert "Object of type ValueError is not JSON serializable" not in response.text


@pytest.mark.anyio
async def test_password_reset_nonexistent_user_is_noop(api_client, fake_email_client):
    fake_email_client.sent.clear()
    initial_count = len(fake_email_client.sent)

    email = "does-not-exist@example.com"

    response = await api_client.post(
        f"{API_PREFIX}/auth/request-password-reset",
        json={"email": email},
    )
    assert response.status_code == 200
    data = response.json()
    assert "If email exists" in data["message"]

    assert len(fake_email_client.sent) == initial_count


@pytest.mark.anyio
async def test_password_reset_uses_body_not_query_params(api_client):
    """H-6: the secrets must be read from the JSON body, not the URL query string.

    Passing them only as query params (the old, leaky behaviour) is now rejected
    because the request body is required.
    """
    # reset-password with the secrets only in the query string -> 422 (missing body).
    query_only = await api_client.post(
        f"{API_PREFIX}/auth/reset-password",
        params={"token": "x" * 32, "new_password": strong_password()},
    )
    assert query_only.status_code == 422

    # request-password-reset with the email only in the query string -> 422.
    query_only_request = await api_client.post(
        f"{API_PREFIX}/auth/request-password-reset",
        params={"email": random_email()},
    )
    assert query_only_request.status_code == 422


@pytest.mark.anyio
async def test_password_reset_invalidates_existing_tokens(api_client, fake_email_client):
    """M-11: a JWT issued before a password reset is rejected afterwards; a fresh login works."""
    username = random_username()
    email = random_email()
    password = strong_password()
    new_password = strong_password()

    await _create_verified_user(api_client, fake_email_client, username, email, password)

    login = await api_client.post(f"{API_PREFIX}/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    old_token = login.json()["access_token"]
    old_headers = {"Authorization": f"Bearer {old_token}"}

    # The pre-reset token works.
    assert (await api_client.get(f"{API_PREFIX}/users/me", headers=old_headers)).status_code == 200

    # Reset the password via the body model.
    fake_email_client.sent.clear()
    await api_client.post(f"{API_PREFIX}/auth/request-password-reset", json={"email": email})
    reset_token = _extract_token_from_html(fake_email_client.sent[-1]["html_content"])
    reset = await api_client.post(
        f"{API_PREFIX}/auth/reset-password",
        json={"token": reset_token, "new_password": new_password},
    )
    assert reset.status_code == 200

    # The old token is now revoked.
    revoked = await api_client.get(f"{API_PREFIX}/users/me", headers=old_headers)
    assert revoked.status_code == 401

    # A fresh login with the new password yields a working token.
    relogin = await api_client.post(f"{API_PREFIX}/auth/login", json={"email": email, "password": new_password})
    assert relogin.status_code == 200
    new_headers = {"Authorization": f"Bearer {relogin.json()['access_token']}"}
    assert (await api_client.get(f"{API_PREFIX}/users/me", headers=new_headers)).status_code == 200
