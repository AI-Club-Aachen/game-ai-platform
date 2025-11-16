"""Application settings with security validation and environment configuration"""

import os
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables with validation"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        json_schema_extra={
            "ALLOW_ORIGINS": {
                "description": "Comma-separated list of allowed CORS origins"
            }
        },
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

    # CORS/Security
    ALLOW_ORIGINS: list[str] = Field(
        default=["http://localhost:3000"],
        description="Comma-separated list of allowed CORS origins (NOT JSON!)",
    )
    LOG_LEVEL: str = "info"
    ENVIRONMENT: str = Field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )

    # Frontend Configuration
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend base URL for email verification links",
    )

    # SMTP Configuration (optional in dev)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 465
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_ADDRESS: Optional[str] = None
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

    @field_validator("ALLOW_ORIGINS", mode="before")
    @classmethod
    def parse_allow_origins(cls, v: Optional[str | list]) -> list[str]:
        # unchanged...
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip().strip("[]").strip()
            if not v:
                return ["http://localhost:3000"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return ["http://localhost:3000"]

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS")
    @classmethod
    def validate_email_token_expiry(cls, v: int) -> int:
        if not (1 <= v <= 168):
            raise ValueError(
                "EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS must be between 1 and 168"
            )
        return v

    @field_validator("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_password_reset_expiry(cls, v: int) -> int:
        if not (5 <= v <= 1440):
            raise ValueError(
                "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES must be between 5 and 1440"
            )
        return v

    @field_validator("ALLOW_ORIGINS", mode="after")
    @classmethod
    def validate_origins_production(cls, v: list[str], info) -> list[str]:
        if info.data.get("ENVIRONMENT", "").lower() == "production":
            invalid_origins = [o for o in v if not o.startswith("https://")]
            if invalid_origins:
                raise ValueError(
                    f"In production, ALLOW_ORIGINS must use https://. Found: {invalid_origins}"
                )
        return v

    @field_validator("SMTP_PORT")
    @classmethod
    def validate_smtp_port(cls, v: Optional[int]) -> Optional[int]:
        """Validate SMTP port is valid when provided"""
        if v is None:
            return v
        if not (1 <= v <= 65535):
            raise ValueError("SMTP_PORT must be between 1 and 65535")
        return v

    @model_validator(mode="after")
    def validate_smtp_required_in_production(self) -> "Settings":
        """
        In staging/production, all SMTP fields must be set;
        in development they may be omitted.
        """
        if self.smtp_required and not self.smtp_configured:
            missing = []
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
                raise ValueError(
                    f"Missing SMTP configuration in {self.ENVIRONMENT}: {', '.join(missing)}"
                )
        return self


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
