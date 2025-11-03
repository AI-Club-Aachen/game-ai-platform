"""Application settings with security validation and environment configuration"""

import os
from typing import Optional
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables with validation"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars for flexibility
        # CRITICAL: Tell Pydantic NOT to auto-parse complex types from env
        json_schema_extra={
            "ALLOW_ORIGINS": {
                "description": "Comma-separated list of allowed CORS origins"
            }
        }
    )

    # Database
    DATABASE_URL: str

    # JWT Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "AI Game Competition Platform"

    # CORS/Security - will be parsed by validator from comma-separated string
    ALLOW_ORIGINS: list[str] = Field(
        default=["http://localhost:3000"],
        description="Comma-separated list of allowed CORS origins (NOT JSON!)"
    )
    LOG_LEVEL: str = "info"
    ENVIRONMENT: str = Field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )

    # Frontend Configuration
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend base URL for email verification links"
    )

    # SMTP Configuration
    SMTP_HOST: str
    SMTP_PORT: int = 465
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_ADDRESS: str
    SMTP_FROM_NAME: str = "AI Game Platform"
    SMTP_USE_TLS: bool = True

    # Email Verification
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT.lower() == "development"

    @field_validator("ALLOW_ORIGINS", mode="before")
    @classmethod
    def parse_allow_origins(cls, v: Optional[str | list]) -> list[str]:
        """
        Parse ALLOW_ORIGINS from comma-separated string.

        Accepts:
        - Comma-separated string: "http://localhost:3000,https://example.com"
        - Already a list: ["http://localhost:3000", "https://example.com"]
        """
        # If already a list, pass through
        if isinstance(v, list):
            return v

        # If string, split by comma
        if isinstance(v, str):
            # Remove any brackets if present (for invalid JSON attempts)
            v = v.strip().strip("[]").strip()

            if not v:
                return ["http://localhost:3000"]  # Default

            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(",") if origin.strip()]

        return ["http://localhost:3000"]  # Fallback default

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Ensure JWT secret is at least 32 characters"""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS")
    @classmethod
    def validate_email_token_expiry(cls, v: int) -> int:
        """Email tokens must expire between 1-168 hours (1 week)"""
        if not (1 <= v <= 168):
            raise ValueError(
                "EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS must be between 1 and 168"
            )
        return v

    @field_validator("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_password_reset_expiry(cls, v: int) -> int:
        """Password reset tokens must expire between 5-1440 minutes (24 hours)"""
        if not (5 <= v <= 1440):
            raise ValueError(
                "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES must be between 5 and 1440"
            )
        return v

    @field_validator("ALLOW_ORIGINS", mode="after")
    @classmethod
    def validate_origins_production(cls, v: list[str], info) -> list[str]:
        """In production, enforce https:// for all origins"""
        if info.data.get("ENVIRONMENT", "").lower() == "production":
            invalid_origins = [o for o in v if not o.startswith("https://")]
            if invalid_origins:
                raise ValueError(
                    f"In production, ALLOW_ORIGINS must use https://. Found: {invalid_origins}"
                )
        return v

    @field_validator("SMTP_PORT")
    @classmethod
    def validate_smtp_port(cls, v: int) -> int:
        """Validate SMTP port is valid"""
        if not (1 <= v <= 65535):
            raise ValueError("SMTP_PORT must be between 1 and 65535")
        return v


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create singleton settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Global settings instance for direct import
settings = get_settings()
