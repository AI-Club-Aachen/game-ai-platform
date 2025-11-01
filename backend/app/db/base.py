from sqlmodel import SQLModel

# Import all models here for Alembic to detect them
from app.models.user import User  # noqa: F401
