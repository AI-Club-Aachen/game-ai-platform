from sqlmodel import create_engine

from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.is_development,  # SQL logs only in dev
    pool_pre_ping=True,
)
