# tests/conftest.py
import os
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel, Session, create_engine

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_email_client, get_email_notification_service
from app.api.services.email import EmailNotificationService
from app.core.config import settings
from app.db.session import get_session
from app.main import app
from tests.fakes import FakeEmailClient

# Prefer a dedicated test DB URL; fall back to the main DATABASE_URL if not set.
# In CI/local you typically set both DATABASE_URL and TEST_DATABASE_URL to point
# at a throwaway database (e.g. gameai_test).
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", settings.DATABASE_URL)


@pytest.fixture(scope="session")
def test_engine():
    """
    Create a dedicated SQLModel engine for tests.

    The schema is recreated once per test session so it always matches
    the current models, independent of Alembic migrations.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        echo=False,          # keep test/CI logs clean
        pool_pre_ping=True,  # safer for long-running sessions
    )

    # Start from a clean schema for the whole session.
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    Yield a DB session bound to the test engine for direct DB assertions.
    """
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="session", autouse=True)
def override_get_session(test_engine):
    """
    Override FastAPI's get_session dependency so all routes use the test DB.
    """

    def _get_session_override() -> Generator[Session, None, None]:
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = _get_session_override
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture(scope="session")
def fake_email_client() -> FakeEmailClient:
    """
    Shared fake email client for the whole test session.
    """
    return FakeEmailClient()


@pytest.fixture(scope="session", autouse=True)
def override_email_dependencies(fake_email_client: FakeEmailClient):
    """
    Override email dependencies so the real EmailNotificationService
    uses the in-memory FakeEmailClient.

    This way, /auth/register, /email/verify, password reset, etc.
    all run through the real service logic, but no real SMTP is used.
    """

    def _get_email_client_override() -> FakeEmailClient:
        return fake_email_client

    def _get_email_notification_service_override() -> EmailNotificationService:
        # Wire the fake into the real notification service so
        # higher-level flows are exercised end-to-end.
        return EmailNotificationService(fake_email_client)

    app.dependency_overrides[get_email_client] = _get_email_client_override
    app.dependency_overrides[get_email_notification_service] = (
        _get_email_notification_service_override
    )

    try:
        yield
    finally:
        app.dependency_overrides.pop(get_email_client, None)
        app.dependency_overrides.pop(get_email_notification_service, None)


@pytest.fixture(scope="session", autouse=True)
def override_rate_limiter():
    """
    Override SlowAPI limiter to use an in-memory backend during tests.

    The app's main module configures a Redis-backed limiter with
    storage_uri="redis://redis:6379", which fails when tests run on
    the host and Redis is not reachable at that hostname.
    Using an in-memory limiter avoids network calls and makes rate
    limiting effectively a no-op for these E2E tests.
    """
    test_limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[],        # disable default global limits in tests
        storage_uri="memory://",  # in-memory backend, no Redis
    )
    app.state.limiter = test_limiter
    yield


# Tell pytest-anyio to use only asyncio, so tests are not duplicated for trio.
@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def api_client(anyio_backend) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client talking to the real FastAPI app in-memory.

    Use this fixture to hit /auth/register, /auth/login, /email/verify-email,
    /auth/request-password-reset, /users/*, etc. as true end-to-end HTTP calls.
    """
    transport = ASGITransport(app=app)
    # Use 'http://localhost' so Host header is allowed by TrustedHostMiddleware.
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        yield client
