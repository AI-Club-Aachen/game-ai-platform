# tests/api/test_rate_limiting.py
"""Regression tests for centralized, configurable rate limiting (H-3 / M-5).

Covers:
- per-category settings exist, parse, and reject malformed limit strings
- production config rejects RATE_LIMITING_ENABLED=false
- the limiter key function picks user-id vs IP vs worker-API-key correctly,
  honoring TRUST_PROXY_HEADERS and DISABLE_IP_RATE_LIMITING
- a tightened endpoint actually returns 429 once its limit is exceeded
- valid worker-key requests are exempt from limits
- RATE_LIMITING_ENABLED=false / disabled limiter turns everything off
"""

import uuid

import pytest
from limits import parse_many
from pydantic import ValidationError
from starlette.requests import Request as StarletteRequest

from app.core.config import Settings, settings
from app.core.rate_limit import limiter, rate_limit_key
from app.core.security import create_access_token


pytestmark = pytest.mark.anyio


REQUIRED_SETTINGS = {
    "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/test",
    "JWT_SECRET_KEY": "x" * 32,
}

PRODUCTION_SETTINGS = {
    **REQUIRED_SETTINGS,
    "ENVIRONMENT": "production",
    "ALLOW_ORIGINS": "https://example.com",
    "TRUSTED_HOSTS": "api.example.com",
    "WORKER_API_KEY": "w" * 48,
    "BYPASS_EMAIL_VERIFICATION": False,
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": 465,
    "SMTP_USERNAME": "user",
    "SMTP_PASSWORD": "pass",
    "SMTP_FROM_ADDRESS": "noreply@example.com",
}

EXPECTED_CATEGORY_DEFAULTS = {
    "RATE_LIMIT_LOGIN": "10/minute;60/hour",
    "RATE_LIMIT_REGISTER": "6/minute;40/hour",
    "RATE_LIMIT_EMAIL_TOKEN": "6/minute;20/hour",
    "RATE_LIMIT_READS": "600/minute;10000/hour",
    "RATE_LIMIT_PROFILE": "120/minute",
    "RATE_LIMIT_MUTATIONS": "120/minute;2000/hour",
    "RATE_LIMIT_UPLOAD": "10/minute;60/hour",
    "RATE_LIMIT_MATCH_CREATE": "20/minute;200/hour",
    "RATE_LIMIT_STREAM": "60/minute",
    "RATE_LIMIT_ADMIN": "20000/minute",
}


def make_request(
    headers: dict[str, str] | None = None,
    client: tuple[str, int] | None = ("203.0.113.5", 1234),
) -> StarletteRequest:
    """Build a bare starlette Request for key-function tests."""
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": raw_headers,
        "query_string": b"",
        "client": client,
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return StarletteRequest(scope)


# ---------------------------------------------------------------------------
# Settings schema
# ---------------------------------------------------------------------------


class TestRateLimitSettings:
    def test_categories_exist_with_required_defaults_and_parse(self):
        s = Settings(_env_file=None, **REQUIRED_SETTINGS)
        for field, expected in EXPECTED_CATEGORY_DEFAULTS.items():
            assert getattr(s, field) == expected, field
            assert parse_many(getattr(s, field)), field

    def test_toggle_defaults(self):
        s = Settings(_env_file=None, **REQUIRED_SETTINGS)
        assert s.RATE_LIMITING_ENABLED is True
        assert s.DISABLE_IP_RATE_LIMITING is False
        assert s.TRUST_PROXY_HEADERS is False
        assert s.rate_limiting_active is True

    def test_malformed_limit_string_rejected(self):
        with pytest.raises(ValidationError, match="RATE_LIMIT_LOGIN"):
            Settings(_env_file=None, **REQUIRED_SETTINGS, RATE_LIMIT_LOGIN="not-a-limit")

    def test_rate_limiting_active_reflects_enabled(self):
        disabled = Settings(_env_file=None, **REQUIRED_SETTINGS, RATE_LIMITING_ENABLED=False)
        assert disabled.rate_limiting_active is False

    def test_production_rejects_disabled_rate_limiting(self):
        with pytest.raises(ValidationError, match="RATE_LIMITING_ENABLED"):
            Settings(_env_file=None, **PRODUCTION_SETTINGS, RATE_LIMITING_ENABLED=False)

    def test_production_accepts_enabled_rate_limiting(self):
        s = Settings(_env_file=None, **PRODUCTION_SETTINGS, RATE_LIMITING_ENABLED=True)
        assert s.rate_limiting_active is True

    def test_development_allows_disabled_rate_limiting(self):
        s = Settings(_env_file=None, **REQUIRED_SETTINGS, RATE_LIMITING_ENABLED=False)
        assert s.RATE_LIMITING_ENABLED is False


# ---------------------------------------------------------------------------
# Production config hardening (M-5)
# ---------------------------------------------------------------------------


class TestProductionHardening:
    def test_valid_production_config_accepted(self):
        s = Settings(_env_file=None, **PRODUCTION_SETTINGS)
        assert s.is_production is True

    def test_rejects_default_worker_key(self):
        cfg = {**PRODUCTION_SETTINGS}
        cfg.pop("WORKER_API_KEY")  # fall back to the default dev key
        with pytest.raises(ValidationError, match="WORKER_API_KEY must not use the default"):
            Settings(_env_file=None, **cfg)

    def test_rejects_short_worker_key(self):
        with pytest.raises(ValidationError, match="WORKER_API_KEY must be at least"):
            Settings(_env_file=None, **{**PRODUCTION_SETTINGS, "WORKER_API_KEY": "too-short"})

    def test_rejects_missing_trusted_hosts(self):
        with pytest.raises(ValidationError, match="TRUSTED_HOSTS must be set"):
            Settings(_env_file=None, **{**PRODUCTION_SETTINGS, "TRUSTED_HOSTS": ""})

    def test_rejects_email_verification_bypass(self):
        with pytest.raises(ValidationError, match="BYPASS_EMAIL_VERIFICATION must be false"):
            Settings(_env_file=None, **{**PRODUCTION_SETTINGS, "BYPASS_EMAIL_VERIFICATION": True})

    def test_reports_all_problems_together(self):
        cfg = {**PRODUCTION_SETTINGS, "TRUSTED_HOSTS": "", "BYPASS_EMAIL_VERIFICATION": True}
        cfg.pop("WORKER_API_KEY")
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None, **cfg)
        message = str(exc_info.value)
        assert "WORKER_API_KEY" in message
        assert "TRUSTED_HOSTS" in message
        assert "BYPASS_EMAIL_VERIFICATION" in message

    def test_development_allows_default_key_and_no_trusted_hosts(self):
        s = Settings(_env_file=None, **REQUIRED_SETTINGS, BYPASS_EMAIL_VERIFICATION=True)
        assert s.WORKER_API_KEY == Settings.DEFAULT_WORKER_API_KEY
        assert s.trusted_hosts_list == []
        assert s.BYPASS_EMAIL_VERIFICATION is True


# ---------------------------------------------------------------------------
# Key function
# ---------------------------------------------------------------------------


class TestRateLimitKeyFunction:
    def test_valid_worker_key_is_exempt_unique_bucket(self):
        request = make_request({"x-api-key": settings.WORKER_API_KEY})
        first = rate_limit_key(request)
        second = rate_limit_key(make_request({"x-api-key": settings.WORKER_API_KEY}))
        assert first.startswith("worker:")
        assert second.startswith("worker:")
        # Unique per request -> hits never accumulate -> effectively exempt.
        assert first != second

    def test_invalid_worker_key_falls_back_to_ip(self):
        request = make_request({"x-api-key": "wrong-key"})
        assert rate_limit_key(request) == "ip:203.0.113.5"

    def test_jwt_user_keyed_by_user_id(self):
        user_id = str(uuid.uuid4())
        token = create_access_token({"sub": user_id, "role": "user"})
        request = make_request({"authorization": f"Bearer {token}"})
        assert rate_limit_key(request) == f"user:{user_id}"

    def test_invalid_jwt_falls_back_to_ip(self):
        request = make_request({"authorization": "Bearer not-a-real-token"})
        assert rate_limit_key(request) == "ip:203.0.113.5"

    def test_anonymous_keyed_by_ip(self):
        assert rate_limit_key(make_request()) == "ip:203.0.113.5"

    def test_forwarded_for_ignored_by_default(self):
        request = make_request({"x-forwarded-for": "198.51.100.7, 10.0.0.1"})
        assert rate_limit_key(request) == "ip:203.0.113.5"

    def test_forwarded_for_trusted_when_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
        request = make_request({"x-forwarded-for": "198.51.100.7, 10.0.0.1"})
        # Right-most hop is the one appended by the trusted proxy.
        assert rate_limit_key(request) == "ip:10.0.0.1"

    def test_disable_ip_rate_limiting_gives_unique_anon_keys(self, monkeypatch):
        monkeypatch.setattr(settings, "DISABLE_IP_RATE_LIMITING", True)
        first = rate_limit_key(make_request())
        second = rate_limit_key(make_request())
        assert first.startswith("anon:")
        assert first != second

    def test_disable_ip_rate_limiting_keeps_user_keys(self, monkeypatch):
        monkeypatch.setattr(settings, "DISABLE_IP_RATE_LIMITING", True)
        user_id = str(uuid.uuid4())
        token = create_access_token({"sub": user_id, "role": "user"})
        request = make_request({"authorization": f"Bearer {token}"})
        assert rate_limit_key(request) == f"user:{user_id}"


# ---------------------------------------------------------------------------
# Enforcement (end-to-end through the app)
# ---------------------------------------------------------------------------


@pytest.fixture
def enabled_limiter():
    """Enable the central limiter for one test, with clean storage."""
    limiter.reset()
    limiter.enabled = True
    try:
        yield limiter
    finally:
        limiter.enabled = False
        limiter.reset()


class TestRateLimitEnforcement:
    async def test_tightened_login_returns_429(self, api_client, enabled_limiter, monkeypatch):
        monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", "3/minute")
        body = {"email": "nobody@example.com", "password": "wrong-password-123"}
        for _ in range(3):
            response = await api_client.post("/api/v1/auth/login", json=body)
            assert response.status_code != 429
        response = await api_client.post("/api/v1/auth/login", json=body)
        assert response.status_code == 429
        assert "Too many requests" in response.json()["detail"]

    async def test_default_reads_limit_applies_to_undecorated_routes(self, api_client, enabled_limiter, monkeypatch):
        monkeypatch.setattr(settings, "RATE_LIMIT_READS", "2/minute")
        url = f"/api/v1/jobs/build/{uuid.uuid4()}"
        for _ in range(2):
            response = await api_client.get(url)
            assert response.status_code != 429
        response = await api_client.get(url)
        assert response.status_code == 429

    async def test_valid_worker_key_exempt_from_limits(self, api_client, enabled_limiter, monkeypatch):
        monkeypatch.setattr(settings, "RATE_LIMIT_READS", "2/minute")
        url = f"/api/v1/jobs/build/{uuid.uuid4()}"
        headers = {"x-api-key": settings.WORKER_API_KEY}
        for _ in range(10):
            response = await api_client.get(url, headers=headers)
            # Job does not exist -> 404, but never throttled.
            assert response.status_code == 404

    async def test_disabled_limiter_allows_unlimited_requests(self, api_client, monkeypatch):
        # conftest disables the limiter session-wide (RATE_LIMITING_ENABLED=false path).
        assert limiter.enabled is False
        monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", "1/minute")
        body = {"email": "nobody@example.com", "password": "wrong-password-123"}
        for _ in range(5):
            response = await api_client.post("/api/v1/auth/login", json=body)
            assert response.status_code != 429
