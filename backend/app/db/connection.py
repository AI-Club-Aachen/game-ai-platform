from sqlmodel import create_engine
from app.core.config import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
)
