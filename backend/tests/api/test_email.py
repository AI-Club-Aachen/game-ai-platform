from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt
from sqlmodel import select

from app.core.config import settings
from app.models.user import User
from tests.fakes import _extract_token_from_html


API_PREFIX = settings.API_V1_PREFIX


def _make_bearer_for_user(user: User) -> str:
    """
    Create a JWT for the given user matching the app's JWT settings.

    This is used to call /email/verification-status and /email/resend-verification
    as an authenticated (but possibly unverified) user.
    """
    now = datetime.now(UTC)
    exp = now + timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user.id),
        "exp": exp,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return f"Bearer {token}"


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


async def _register_verify_login_bearer(api_client, fake_email_client, username, email, password) -> tuple[str, str]:
    """
    Helper for failure tests: register, verify via email, then login to get bearer token.
    Returns (user_id, bearer_token).
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
    return str(data["user_id"]), f"Bearer {data['access_token']}"


# ---------------------------------------------------------------------------
# Success: register -> verification sent -> status -> resend -> verify
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_email_verification_full_flow_success(api_client, fake_email_client, db_session):
    username = "email_flow_user"
    email = "email_flow_user@example.com"
    password = "EmailFlowPass1!"

    fake_email_client.sent.clear()

    # 1) User registers -> verification email is sent.
    await _register_user(api_client, username, email, password)
    assert len(fake_email_client.sent) == 1
    first_email = fake_email_client.sent[-1]
    assert "Verify Your Email Address" in first_email["subject"]
    assert first_email["to_email"] == email

    # Fetch the newly created user from the DB.
    user = db_session.exec(select(User).where(User.email == email)).first()
    assert user is not None
    assert user.email_verified is False
    assert user.email_verification_token_hash is not None
    original_token_hash = user.email_verification_token_hash

    # Create a JWT for this unverified user to call status/resend endpoints.
    bearer = _make_bearer_for_user(user)

    # 2) Check verification status before verifying.
    status_response = await api_client.get(
        f"{API_PREFIX}/email/verification-status",
        headers={"Authorization": bearer},
    )
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["email"] == email
    assert status_data["email_verified"] is False
    assert status_data["can_resend"] is True
    assert status_data["verification_expires_at"] is not None

    # 3) Resend verification email.
    resend_response = await api_client.post(
        f"{API_PREFIX}/email/resend-verification",
        headers={"Authorization": bearer},
    )
    assert resend_response.status_code == 200
    resend_data = resend_response.json()
    assert resend_data["message"] == "Verification email sent. Check your inbox."

    # A second verification email should have been sent.
    assert len(fake_email_client.sent) == 2
    second_email = fake_email_client.sent[-1]
    assert "Verify Your Email Address" in second_email["subject"]
    assert second_email["to_email"] == email

    # Token in DB should have been refreshed.
    db_session.refresh(user)
    assert user.email_verification_token_hash is not None
    assert user.email_verification_token_hash != original_token_hash

    # 4) Verify email using token from the resent email.
    verification_token = _extract_token_from_html(second_email["html_content"])
    verify_response = await api_client.post(
        f"{API_PREFIX}/email/verify-email",
        json={"token": verification_token},
    )
    assert verify_response.status_code == 200
    verify_data = verify_response.json()
    assert verify_data["email"] == email
    assert verify_data["email_verified"] is True

    # User record should be updated accordingly.
    db_session.refresh(user)
    assert user.email_verified is True
    assert user.email_verification_token_hash is None
    assert user.email_verification_expires_at is None

    # 5) Verification status after successful verification.
    status_response_2 = await api_client.get(
        f"{API_PREFIX}/email/verification-status",
        headers={"Authorization": bearer},
    )
    assert status_response_2.status_code == 200
    status_data_2 = status_response_2.json()
    assert status_data_2["email"] == email
    assert status_data_2["email_verified"] is True
    assert status_data_2["can_resend"] is False
    # After verification, expiry is cleared.
    assert status_data_2["verification_expires_at"] is None


# ---------------------------------------------------------------------------
# Fail: verify-email bad format / invalid token
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_verify_email_fails_for_invalid_token_format(api_client):
    # Token too short to satisfy EmailVerificationRequest / route checks.
    response = await api_client.post(
        f"{API_PREFIX}/email/verify-email",
        json={"token": "short"},
    )
    # Expect Pydantic validation error
    assert response.status_code == 422
    data = response.json()
    # Basic sanity check on the validation error structure
    assert "detail" in data
    # Optional: assert that the validation refers to 'token'
    assert any(err.get("loc", [None])[-1] == "token" for err in data["detail"])


@pytest.mark.anyio
async def test_verify_email_fails_for_unknown_token(api_client):
    # Well-formed but unknown token should be rejected.
    response = await api_client.post(
        f"{API_PREFIX}/email/verify-email",
        json={"token": "x" * 32},
    )
    assert response.status_code == 400
    data = response.json()
    assert "Invalid verification token" in data["detail"]


# ---------------------------------------------------------------------------
# Fail: resend-verification for already verified user
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_resend_verification_fails_for_already_verified_user(api_client, fake_email_client):
    username = "already_verified_user"
    email = "already_verified_user@example.com"
    password = "AlreadyVer1fiedPass!"

    _, bearer = await _register_verify_login_bearer(api_client, fake_email_client, username, email, password)

    # At this point the user is verified and logged in; resend should fail.
    response = await api_client.post(
        f"{API_PREFIX}/email/resend-verification",
        headers={"Authorization": bearer},
    )
    assert response.status_code == 400
    data = response.json()
    assert "Email already verified" in data["detail"]


# ---------------------------------------------------------------------------
# Fail: verification-status requires authentication
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_verification_status_unauthenticated_fails(api_client):
    response = await api_client.get(f"{API_PREFIX}/email/verification-status")
    # HTTPBearer returns 403 when Authorization header is missing.
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Success: admin resend verification email for unverified user
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_admin_resend_verification_email_for_unverified_user_success(
    api_client, fake_email_client, db_session
):
    from tests.api.test_users import _create_admin_and_token

    # Create unverified user (register but do not verify).
    username = "unverified_for_admin"
    email = "unverified_for_admin@example.com"
    password = "Unver1fiedAcc0unt!2"

    fake_email_client.sent.clear()
    await _register_user(api_client, username, email, password)

    # Fetch user from DB to confirm unverified.
    user = db_session.exec(select(User).where(User.email == email)).first()
    assert user is not None
    assert user.email_verified is False
    old_token_hash = user.email_verification_token_hash

    # Admin.
    admin_username = "admin_for_resend"
    admin_email = "admin_for_resend@example.com"
    admin_password = "ResendRootX!3"
    _, admin_token = await _create_admin_and_token(
        api_client,
        fake_email_client,
        db_session,
        admin_username,
        admin_email,
        admin_password,
    )

    # Admin triggers resend verification for that user.
    response = await api_client.post(
        f"{API_PREFIX}/email/{user.id}/resend-verification",
        headers={"Authorization": admin_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(user.id)
    assert data["message"] == "Verification email sent"

    # Token fields should be updated in DB.
    db_session.refresh(user)
    assert user.email_verified is False
    assert user.email_verification_token_hash is not None
    assert user.email_verification_token_hash != old_token_hash
    assert user.email_verification_expires_at is not None

    # Verify email was actually sent
    assert len(fake_email_client.sent) >= 1
    last_email = fake_email_client.sent[-1]
    assert "Verify Your Email Address" in last_email["subject"]
    assert last_email["to_email"] == email


@pytest.mark.anyio
async def test_non_admin_cannot_resend_verification(
    api_client, fake_email_client, db_session
):
    # Create a normal verified user (role GUEST).
    username = "non_admin_user_email"
    email = "non_admin_user_email@example.com"
    password = "NonPrivAcc0unt!1"
    user_id, user_token = await _register_verify_login_bearer(
        api_client, fake_email_client, username, email, password
    )

    # Try to resend verification for self (using admin endpoint)
    response = await api_client.post(
        f"{API_PREFIX}/email/{user_id}/resend-verification",
        headers={"Authorization": user_token},
    )
    assert response.status_code == 403

