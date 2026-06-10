"""Application settings with security validation and environment configuration"""

import os
from typing import ClassVar
from urllib.parse import urlsplit

from limits import parse_many
from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables with validation"""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        json_schema_extra={"ALLOW_ORIGINS": {"description": "Comma-separated list of allowed CORS origins"}},
    )

    # Validation constants
    MIN_JWT_SECRET_LENGTH: ClassVar[int] = 32
    MIN_WORKER_API_KEY_LENGTH: ClassVar[int] = 32
    DEFAULT_WORKER_API_KEY: ClassVar[str] = "dev-worker-key-12345"
    MIN_EMAIL_TOKEN_HOURS: ClassVar[int] = 1
    MAX_EMAIL_TOKEN_HOURS: ClassVar[int] = 168
    MIN_PASSWORD_RESET_MINUTES: ClassVar[int] = 5
    MAX_PASSWORD_RESET_MINUTES: ClassVar[int] = 1440
    MIN_PORT: ClassVar[int] = 1
    MAX_PORT: ClassVar[int] = 65535
    MIN_TURN_TIME_LIMIT_SECONDS: ClassVar[float] = 0.1

    # Database
    DATABASE_URL: str
    DB_ECHO: bool | None = Field(
        default=None,
        description="Override default DB SQL echoing behavior. Defaults to True in dev environment, False otherwise.",
    )
    REDIS_URL: str = "redis://redis:6379/0"

    # Rate limiting (H-3). Limit strings use the slowapi/limits format,
    # multiple limits separated by ";" (e.g. "10/minute;60/hour").
    RATE_LIMITING_ENABLED: bool = Field(
        default=True,
        description="Master rate-limiting switch. Disable only for dev/test; MUST be true in production.",
    )
    DISABLE_IP_RATE_LIMITING: bool = Field(
        default=False,
        description=(
            "Shared-IP (hackathon) mode: drop IP-keyed limits for anonymous requests "
            "while keeping per-user-id limits for authenticated requests."
        ),
    )
    TRUST_PROXY_HEADERS: bool = Field(
        default=False,
        description=(
            "Trust X-Forwarded-For for the client IP. Enable only behind a reverse proxy "
            "that overwrites/appends the header; the proxy-adjacent (right-most) hop is used."
        ),
    )
    RATE_LIMIT_LOGIN: str = "10/minute;60/hour"
    RATE_LIMIT_REGISTER: str = "6/minute;40/hour"
    RATE_LIMIT_EMAIL_TOKEN: str = Field(
        default="6/minute;20/hour",
        description="Email verification and password-reset token endpoints.",
    )
    RATE_LIMIT_READS: str = Field(
        default="600/minute;10000/hour",
        description="Global default applied to all routes without an explicit category.",
    )
    RATE_LIMIT_PROFILE: str = "120/minute"
    RATE_LIMIT_MUTATIONS: str = "120/minute;2000/hour"
    RATE_LIMIT_UPLOAD: str = "10/minute;60/hour"
    RATE_LIMIT_MATCH_CREATE: str = "20/minute;200/hour"
    RATE_LIMIT_STREAM: str = Field(
        default="60/minute",
        description="SSE match-stream connection attempts.",
    )
    RATE_LIMIT_ADMIN: str = "20000/minute"

    # JWT Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "AI Game Competition Platform"
    WORKER_API_KEY: str = DEFAULT_WORKER_API_KEY
    MAX_TURN_TIME_LIMIT_SECONDS: float = Field(
        default=120.0,
        description="Maximum allowed per-turn time limit in seconds for match config.",
    )
    MATCH_STALE_TIMEOUT_SECONDS: float = Field(
        default=60.0,
        description=(
            "How long a match may remain in running state without worker updates before the scheduler "
            "marks it as failed. This recovers matches abandoned by killed/restarted workers."
        ),
    )
    # Untrusted match-init bounds (M-10): user-supplied state_init_data reaches the
    # game engine in the privileged worker, so per-game init input is whitelisted and
    # bounded in the backend before queueing. board_size drives O(n^2) board allocation.
    MAX_HEX_BOARD_SIZE: int = Field(
        default=26,
        description="Maximum allowed Hex board_size in match state_init_data (DoS guard).",
    )

    # Filesystem Paths
    UPLOAD_DIR: str = "uploads"
    SUBMISSIONS_DIR: str = "uploads/submissions"
    MAX_AGENTS_PER_GAME: int = Field(
        default=0,
        description="Maximum number of agents a user can create per game. 0 disables the limit.",
    )

    # Upload limits (H-4)
    MAX_UPLOAD_BYTES: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum accepted submission upload size in bytes. 0 disables the limit.",
    )
    MAX_SUBMISSIONS_PER_USER: int = Field(
        default=0,
        description="Maximum number of submissions a user may store. 0 disables the quota.",
    )

    # Worker payload limits (M-3): bound the log/result/game-state that worker
    # callbacks store on build jobs and matches. Logs are truncated server-side;
    # oversized result/game-state payloads are rejected.
    MAX_LOG_APPEND_BYTES: int = Field(
        default=64 * 1024,
        description="Maximum size of a single worker log append (characters). 0 disables the cap.",
    )
    MAX_TOTAL_LOG_BYTES: int = Field(
        default=1024 * 1024,
        description="Maximum total stored log size; the oldest content is truncated. 0 disables the cap.",
    )
    MAX_RESULT_BYTES: int = Field(
        default=256 * 1024,
        description="Maximum serialized size of a match result payload in bytes. 0 disables the cap.",
    )
    MAX_GAME_STATE_BYTES: int = Field(
        default=1024 * 1024,
        description="Maximum serialized size of a match game-state payload in bytes. 0 disables the cap.",
    )

    # CORS/Security
    ALLOW_ORIGINS: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )
    TRUSTED_HOSTS: str = Field(
        default="",
        description=(
            "Comma-separated list of public/backend hostnames accepted by TrustedHostMiddleware, "
            "for example api.example.com"
        ),
    )
    LOG_LEVEL: str = "info"
    ENVIRONMENT: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))

    # Frontend Configuration
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend base URL for email verification links",
    )

    # SMTP Configuration (optional in dev)
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = 465
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_ADDRESS: str | None = None
    SMTP_FROM_NAME: str = "AI Game Platform"
    SMTP_USE_TLS: bool = True

    # Email Verification
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # Development Feature Flags
    BYPASS_EMAIL_VERIFICATION: bool = Field(
        default=False,
        description="Bypasses email verification. MUST NOT BE TRUE IN PRODUCTION.",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT.lower() == "staging"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def docs_enabled(self) -> bool:
        return self.is_development or self.is_staging

    @property
    def rate_limiting_active(self) -> bool:
        """Effective rate-limiting switch."""
        return self.RATE_LIMITING_ENABLED

    @property
    def smtp_required(self) -> bool:
        # Only require SMTP in staging and production
        return self.is_staging or self.is_production

    @property
    def smtp_configured(self) -> bool:
        """
        True if all required SMTP fields are set.
        Used by EmailService to decide whether to actually send.
        """
        return all(
            [
                self.SMTP_HOST,
                self.SMTP_PORT,
                self.SMTP_USERNAME,
                self.SMTP_PASSWORD,
                self.SMTP_FROM_ADDRESS,
            ]
        )

    @staticmethod
    def _parse_csv(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @staticmethod
    def _redis_has_auth(redis_url: str) -> bool:
        """True if REDIS_URL carries a password or uses TLS (M-7)."""
        parsed = urlsplit(redis_url)
        if parsed.scheme == "rediss":
            return True
        return bool(parsed.password)

    @staticmethod
    def _reject_json_style_list(value: str, field_name: str) -> None:
        stripped = value.strip()
        if stripped.startswith("[") or stripped.endswith("]") or '"' in stripped or "'" in stripped:
            raise ValueError(
                f"{field_name} must be a comma-separated list without JSON brackets or quotes. "
                f"Example: {field_name}=https://example.com,https://www.example.com"
            )

    @property
    def allow_origins_list(self) -> list[str]:
        return self._parse_csv(self.ALLOW_ORIGINS) or ["http://localhost:3000"]

    @property
    def trusted_hosts_list(self) -> list[str]:
        return self._parse_csv(self.TRUSTED_HOSTS)

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < cls.MIN_JWT_SECRET_LENGTH:
            raise ValueError(f"JWT_SECRET_KEY must be at least {cls.MIN_JWT_SECRET_LENGTH} characters long")
        return v

    @field_validator("EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS")
    @classmethod
    def validate_email_token_expiry(cls, v: int) -> int:
        if not (cls.MIN_EMAIL_TOKEN_HOURS <= v <= cls.MAX_EMAIL_TOKEN_HOURS):
            raise ValueError(
                "EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS must be between "
                f"{cls.MIN_EMAIL_TOKEN_HOURS} and {cls.MAX_EMAIL_TOKEN_HOURS}"
            )
        return v

    @field_validator("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_password_reset_expiry(cls, v: int) -> int:
        if not (cls.MIN_PASSWORD_RESET_MINUTES <= v <= cls.MAX_PASSWORD_RESET_MINUTES):
            raise ValueError(
                "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES must be between "
                f"{cls.MIN_PASSWORD_RESET_MINUTES} and {cls.MAX_PASSWORD_RESET_MINUTES}"
            )
        return v

    @field_validator("ALLOW_ORIGINS")
    @classmethod
    def validate_origins_production(cls, v: str, info: ValidationInfo) -> str:
        cls._reject_json_style_list(v, "ALLOW_ORIGINS")
        # The app always runs CORSMiddleware with allow_credentials=True, so a
        # literal "*" origin combined with credentials is invalid and unsafe
        # (M-6). Reject it at config load regardless of environment.
        if "*" in cls._parse_csv(v):
            raise ValueError(
                "ALLOW_ORIGINS must not contain '*' because credentials are enabled. "
                "List explicit origins, e.g. ALLOW_ORIGINS=https://example.com"
            )
        # ValidationInfo.data is the already-validated field values. [web:33][web:34]
        if info.data.get("ENVIRONMENT", "").lower() == "production":
            invalid_origins = [o for o in cls._parse_csv(v) if not o.startswith("https://")]
            if invalid_origins:
                raise ValueError(f"In production, ALLOW_ORIGINS must use https://. Found: {invalid_origins}")
        return v

    @field_validator("TRUSTED_HOSTS")
    @classmethod
    def validate_trusted_hosts_format(cls, v: str) -> str:
        cls._reject_json_style_list(v, "TRUSTED_HOSTS")
        return v

    @field_validator(
        "RATE_LIMIT_LOGIN",
        "RATE_LIMIT_REGISTER",
        "RATE_LIMIT_EMAIL_TOKEN",
        "RATE_LIMIT_READS",
        "RATE_LIMIT_PROFILE",
        "RATE_LIMIT_MUTATIONS",
        "RATE_LIMIT_UPLOAD",
        "RATE_LIMIT_MATCH_CREATE",
        "RATE_LIMIT_STREAM",
        "RATE_LIMIT_ADMIN",
    )
    @classmethod
    def validate_rate_limit_format(cls, v: str, info: ValidationInfo) -> str:
        try:
            parse_many(v)
        except ValueError as e:
            raise ValueError(
                f"{info.field_name} is not a valid rate limit string. "
                f'Use the limits format, e.g. "10/minute;60/hour". Got: {v!r}'
            ) from e
        return v

    @field_validator("SMTP_PORT")
    @classmethod
    def validate_smtp_port(cls, v: int | None) -> int | None:
        """Validate SMTP port is valid when provided"""
        if v is None:
            return v
        if not (cls.MIN_PORT <= v <= cls.MAX_PORT):
            raise ValueError(f"SMTP_PORT must be between {cls.MIN_PORT} and {cls.MAX_PORT}")
        return v

    @field_validator("MAX_TURN_TIME_LIMIT_SECONDS")
    @classmethod
    def validate_max_turn_time_limit(cls, v: float) -> float:
        if v < cls.MIN_TURN_TIME_LIMIT_SECONDS:
            raise ValueError(f"MAX_TURN_TIME_LIMIT_SECONDS must be at least {cls.MIN_TURN_TIME_LIMIT_SECONDS}")
        return v

    @field_validator("MATCH_STALE_TIMEOUT_SECONDS")
    @classmethod
    def validate_match_stale_timeout(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("MATCH_STALE_TIMEOUT_SECONDS must be greater than 0")
        return v

    @field_validator("MAX_HEX_BOARD_SIZE")
    @classmethod
    def validate_max_hex_board_size(cls, v: int) -> int:
        if v < 2:  # noqa: PLR2004
            raise ValueError("MAX_HEX_BOARD_SIZE must be at least 2")
        return v

    @model_validator(mode="after")
    def validate_smtp_required_in_production(self) -> "Settings":
        """
        In staging/production, all SMTP fields must be set;
        in development they may be omitted.
        """
        if self.smtp_required and not self.smtp_configured:
            missing: list[str] = []
            if not self.SMTP_HOST:
                missing.append("SMTP_HOST")
            if not self.SMTP_PORT:
                missing.append("SMTP_PORT")
            if not self.SMTP_USERNAME:
                missing.append("SMTP_USERNAME")
            if not self.SMTP_PASSWORD:
                missing.append("SMTP_PASSWORD")
            if not self.SMTP_FROM_ADDRESS:
                missing.append("SMTP_FROM_ADDRESS")
            if missing:
                raise ValueError(f"Missing SMTP configuration in {self.ENVIRONMENT}: {', '.join(missing)}")
        return self

    @model_validator(mode="after")
    def validate_rate_limiting_enabled_in_production(self) -> "Settings":
        """Rate limiting must never be disabled in production."""
        if self.is_production and not self.RATE_LIMITING_ENABLED:
            raise ValueError("RATE_LIMITING_ENABLED must not be false in production")
        return self

    @model_validator(mode="after")
    def validate_production_hardening(self) -> "Settings":
        """
        Production startup guards (M-5): reject deployments that ship a
        default/short worker key, omit TRUSTED_HOSTS, or leave the email
        verification bypass on. All problems are reported together.
        """
        if not self.is_production:
            return self

        errors: list[str] = []

        if self.WORKER_API_KEY == self.DEFAULT_WORKER_API_KEY:
            errors.append("WORKER_API_KEY must not use the default development value in production")
        elif len(self.WORKER_API_KEY) < self.MIN_WORKER_API_KEY_LENGTH:
            errors.append(
                f"WORKER_API_KEY must be at least {self.MIN_WORKER_API_KEY_LENGTH} characters in production"
            )

        if not self.trusted_hosts_list:
            errors.append("TRUSTED_HOSTS must be set in production")

        if self.BYPASS_EMAIL_VERIFICATION:
            errors.append("BYPASS_EMAIL_VERIFICATION must be false in production")

        if not self._redis_has_auth(self.REDIS_URL):
            errors.append(
                "REDIS_URL must use a password (redis://:<pw>@host:6379/0) or TLS (rediss://) in production (M-7)"
            )

        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self


# Singleton instance holder
class _SettingsHolder:
    """Holder for singleton settings instance"""

    instance: Settings | None = None


def get_settings() -> Settings:
    """Get or create singleton settings instance"""
    if _SettingsHolder.instance is None:
        _SettingsHolder.instance = Settings()  # type: ignore[call-arg]
    return _SettingsHolder.instance


# Global settings instance for direct import
settings = get_settings()
