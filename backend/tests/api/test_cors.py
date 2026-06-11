"""Regression tests for CORS configuration and response headers."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.main import _apply_cors_headers


REQUIRED_SETTINGS = {
    "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/test",
    "JWT_SECRET_KEY": "x" * 32,
}


class TestAllowOriginsRejectsWildcard:
    def test_bare_wildcard_rejected(self):
        with pytest.raises(ValidationError, match="must not contain '\\*'"):
            Settings(_env_file=None, **REQUIRED_SETTINGS, ALLOW_ORIGINS="*")

    def test_wildcard_mixed_with_explicit_origin_rejected(self):
        with pytest.raises(ValidationError, match="must not contain '\\*'"):
            Settings(_env_file=None, **REQUIRED_SETTINGS, ALLOW_ORIGINS="https://app.example.com,*")

    def test_explicit_origins_accepted(self):
        s = Settings(_env_file=None, **REQUIRED_SETTINGS, ALLOW_ORIGINS="https://app.example.com")
        assert s.allow_origins_list == ["https://app.example.com"]


class _Resp:
    """Minimal stand-in for a response object exposing a headers dict."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}


class _Req:
    def __init__(self, origin: str | None) -> None:
        self.headers = {"origin": origin} if origin is not None else {}


class TestApplyCorsHeadersNeverWildcardWithCredentials:
    def test_wildcard_config_reflects_origin_without_credentials(self, monkeypatch):
        # Force the (config-rejected) "*" state to prove the error path is safe.

        monkeypatch.setattr(settings, "ALLOW_ORIGINS", "*")
        resp = _apply_cors_headers(_Req("https://evil.example.com"), _Resp())  # type: ignore[arg-type]

        assert resp.headers.get("Access-Control-Allow-Origin") != "*"
        assert resp.headers.get("Access-Control-Allow-Origin") == "https://evil.example.com"
        assert "Access-Control-Allow-Credentials" not in resp.headers

    def test_listed_origin_gets_credentials(self, monkeypatch):

        monkeypatch.setattr(settings, "ALLOW_ORIGINS", "https://app.example.com")
        resp = _apply_cors_headers(_Req("https://app.example.com"), _Resp())  # type: ignore[arg-type]

        assert resp.headers["Access-Control-Allow-Origin"] == "https://app.example.com"
        assert resp.headers["Access-Control-Allow-Credentials"] == "true"

    def test_unlisted_origin_gets_no_header(self, monkeypatch):

        monkeypatch.setattr(settings, "ALLOW_ORIGINS", "https://app.example.com")
        resp = _apply_cors_headers(_Req("https://other.example.com"), _Resp())  # type: ignore[arg-type]

        assert "Access-Control-Allow-Origin" not in resp.headers
