# Import SQLModel for Alembic autogeneration

# Import all models here for Alembic to detect them
from sqlmodel import SQLModel  # noqa: F401

from app.models.agent import Agent  # noqa: F401
from app.models.job import BuildJob, MatchJob  # noqa: F401
from app.models.match import Match  # noqa: F401
from app.models.submission import Submission  # noqa: F401
from app.models.user import User  # noqa: F401
