import pytest
import uuid
import string
import random
from app.core.config import settings
from tests.api.test_users import _create_verified_user_and_token, _create_admin_and_token

API_PREFIX = settings.API_V1_PREFIX

def _generate_strong_password() -> str:
    """Generate a password that satisfies strict complexity requirements."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    # Ensure at least one of each required type
    password = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*"),
    ]
    # Fill the rest
    password.extend(random.choice(chars) for _ in range(12))
    random.shuffle(password)
    return "".join(password)

@pytest.mark.anyio
async def test_role_enforcement_flow(api_client, fake_email_client, db_session):
    """
    E2E: Verify that role changes dynamically affect access control.
    1. User (Guest) -> Admin Endpoint -> 403
    2. Admin promotes User to Admin -> Admin Endpoint -> 200
    3. Admin demotes User to Guest -> Admin Endpoint -> 403
    """
    # 1. Create standard user (Guest)
    username = f"role_test_user_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = _generate_strong_password()
    user_id, user_token = await _create_verified_user_and_token(
        api_client, fake_email_client, username, email, password
    )

    # 2. Create Admin
    admin_username = f"role_test_admin_{uuid.uuid4().hex[:8]}"
    admin_email = f"{admin_username}@example.com"
    admin_password = _generate_strong_password()
    _, admin_token = await _create_admin_and_token(
        api_client, fake_email_client, db_session, admin_username, admin_email, admin_password
    )

    # 3. User tries to access admin endpoint (List Users) -> Expect 403
    response = await api_client.get(
        f"{API_PREFIX}/users/?skip=0&limit=1",
        headers={"Authorization": user_token},
    )
    assert response.status_code == 403

    # 4. Admin promotes User to Admin
    response = await api_client.patch(
        f"{API_PREFIX}/users/{user_id}/role",
        headers={"Authorization": admin_token},
        json={"role": "admin"},
    )
    assert response.status_code == 200

    # 5. User tries to access admin endpoint -> Expect 200
    response = await api_client.get(
        f"{API_PREFIX}/users/?skip=0&limit=1",
        headers={"Authorization": user_token},
    )
    assert response.status_code == 200

    # 6. Admin tries to demote User back to User -> Expect 403 (Safety rule: Admin cannot demote Admin)
    response = await api_client.patch(
        f"{API_PREFIX}/users/{user_id}/role",
        headers={"Authorization": admin_token},
        json={"role": "user"},
    )
    assert response.status_code == 403

    # 7. Manually demote user in DB to verify access is revoked when role changes
    from app.models.user import User, UserRole
    from sqlmodel import select
    
    user_uuid = uuid.UUID(user_id)
    user_db = db_session.exec(select(User).where(User.id == user_uuid)).first()
    user_db.role = UserRole.USER
    db_session.add(user_db)
    db_session.commit()

    # 8. User tries to access admin endpoint -> Expect 403
    response = await api_client.get(
        f"{API_PREFIX}/users/?skip=0&limit=1",
        headers={"Authorization": user_token},
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_user_deletion_flow(api_client, fake_email_client, db_session):
    """
    E2E: Verify that a deleted user cannot login.
    1. Create User -> Login -> Success
    2. Admin deletes User
    3. User tries to Login -> Fail
    """
    # 1. Create User
    username = f"delete_test_user_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = _generate_strong_password()
    user_id, _ = await _create_verified_user_and_token(
        api_client, fake_email_client, username, email, password
    )

    # 2. Login check (should work)
    response = await api_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200

    # 3. Create Admin
    admin_username = f"delete_test_admin_{uuid.uuid4().hex[:8]}"
    admin_email = f"{admin_username}@example.com"
    admin_password = _generate_strong_password()
    _, admin_token = await _create_admin_and_token(
        api_client, fake_email_client, db_session, admin_username, admin_email, admin_password
    )

    # 4. Admin deletes User
    response = await api_client.delete(
        f"{API_PREFIX}/users/{user_id}",
        headers={"Authorization": admin_token},
    )
    assert response.status_code == 204

    # 5. User tries to Login -> Expect 401 (Invalid credentials/User not found)
    response = await api_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": password},
    )
    # Depending on implementation, this might be 401 or 404, but usually 401 for login
    assert response.status_code == 401


@pytest.mark.anyio
async def test_password_change_security_flow(api_client, fake_email_client):
    """
    E2E: Verify that changing password invalidates the old one.
    1. Create User
    2. Change Password
    3. Login with Old Password -> Fail
    4. Login with New Password -> Success
    """
    username = f"pw_security_user_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    old_password = _generate_strong_password()
    new_password = _generate_strong_password()

    user_id, bearer_token = await _create_verified_user_and_token(
        api_client, fake_email_client, username, email, old_password
    )

    # Change Password
    response = await api_client.post(
        f"{API_PREFIX}/users/change-password",
        headers={"Authorization": bearer_token},
        json={"current_password": old_password, "new_password": new_password},
    )
    assert response.status_code == 200

    # Login with Old Password -> Fail
    response = await api_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": old_password},
    )
    assert response.status_code == 401

    # Login with New Password -> Success
    response = await api_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": new_password},
    )
    assert response.status_code == 200
