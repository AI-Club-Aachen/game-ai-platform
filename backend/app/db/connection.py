from sqlmodel import create_engine

from app.core.config import settings

# Determine if we should echo SQL based on DB_ECHO env var or fallback to is_development
should_echo = settings.DB_ECHO if settings.DB_ECHO is not None else settings.is_development

engine = create_engine(
    settings.DATABASE_URL,
    echo=should_echo,
    pool_pre_ping=True,
)
