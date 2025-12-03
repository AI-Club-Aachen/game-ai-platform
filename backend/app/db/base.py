# Import SQLModel for Alembic autogeneration

# Import all models here for Alembic to detect them
from sqlmodel import SQLModel  # noqa: F401

from app.models.user import User  # noqa: F401
