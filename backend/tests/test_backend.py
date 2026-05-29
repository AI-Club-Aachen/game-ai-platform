from app.core.config import Settings
from app.main import _build_allowed_hosts


def test_allow_origins_uses_comma_separated_env_string() -> None:
    settings = Settings(
        DATABASE_URL="sqlite:///test.db",
        JWT_SECRET_KEY="x" * 32,
        ENVIRONMENT="production",
        ALLOW_ORIGINS="https://game-ai.ai-club-aachen.com,https://www.example.com",
    )

    assert settings.ALLOW_ORIGINS == "https://game-ai.ai-club-aachen.com,https://www.example.com"
    assert settings.allow_origins_list == ["https://game-ai.ai-club-aachen.com", "https://www.example.com"]


def test_trusted_hosts_uses_comma_separated_env_string() -> None:
    settings = Settings(
        DATABASE_URL="sqlite:///test.db",
        JWT_SECRET_KEY="x" * 32,
        TRUSTED_HOSTS="api.ai-club-aachen.com,internal.example.com",
    )

    assert settings.trusted_hosts_list == ["api.ai-club-aachen.com", "internal.example.com"]


def test_trusted_hosts_include_public_api_hostname() -> None:
    allowed_hosts = _build_allowed_hosts(
        trusted_hosts=["api.ai-club-aachen.com"],
        allow_origins=["https://game-ai.ai-club-aachen.com"],
    )

    assert "api.ai-club-aachen.com" in allowed_hosts
    assert "game-ai.ai-club-aachen.com" in allowed_hosts


def test_trusted_hosts_do_not_implicitly_allow_unconfigured_api_hostname() -> None:
    allowed_hosts = _build_allowed_hosts(
        trusted_hosts=[],
        allow_origins=["https://game-ai.ai-club-aachen.com"],
    )

    assert "api.ai-club-aachen.com" not in allowed_hosts