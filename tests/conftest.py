# tests/conftest.py
import os
import random
import string
import time

import pytest
import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000/api/v1")


def random_lower_string(length: int = 10) -> str:
    """Generate a random lower-case string."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_email() -> str:
    """Generate a random email."""
    return f"{random_lower_string()}@{random_lower_string()}.com"


def random_username() -> str:
    """Generate a random username."""
    return f"user_{random_lower_string(8)}"


def strong_password() -> str:
    """Generate a strong password meeting requirements."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*"),
    ]
    pwd += random.choices(chars, k=10)
    random.shuffle(pwd)
    return "".join(pwd)


@pytest.fixture
def api_base_url():
    """Return the base API URL."""
    return API_URL


@pytest.fixture
def user_credentials():
    """Fixture that returns a fresh set of user credentials."""
    return {
        "username": random_username(),
        "email": random_email(),
        "password": strong_password(),
    }


@pytest.fixture
def verified_user_token(api_base_url, user_credentials):
    """
    Register and login a user, returning the access token.
    
    Note: For this to work in environments with email verification, the server
    must have verification disabled or a way to bypass it for tests must be 
    implemented.
    """
    # 1. Register the user
    reg_res = requests.post(
        f"{api_base_url}/auth/register", 
        json=user_credentials,
        timeout=10
    )
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"

    # 2. Login (assume account is verified or verification is disabled in test environment)
    login_res = requests.post(
        f"{api_base_url}/auth/login",
        json={
            "email": user_credentials["email"],
            "password": user_credentials["password"]
        },
        timeout=10
    )
    
    # If 403 Forbidden is returned, it likely means email verification is required.
    # In a full E2E setup, we'd either query a test-only route or bypass this centrally.
    if login_res.status_code == 403:
        pytest.fail(f"Login failed because account is unverified. Verification bypass may be needed. Error: {login_res.text}")
        
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    return login_res.json()["access_token"]


@pytest.fixture
def auth_headers(verified_user_token):
    """Fixture that returns authorization headers for a verified user."""
    return {"Authorization": f"Bearer {verified_user_token}"}
