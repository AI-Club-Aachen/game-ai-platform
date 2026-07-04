from sqlmodel import create_engine

from app.core.config import settings


# Determine if we should echo SQL based on DB_ECHO env var or fallback to is_development
should_echo = settings.DB_ECHO if settings.DB_ECHO is not None else settings.is_development

engine_kwargs = {
    "echo": should_echo,
    "pool_pre_ping": True,
}

if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = settings.DATABASE_POOL_TIMEOUT

engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)
