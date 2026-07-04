"""add HEX_5X5 to gametype enum

Revision ID: f20d83768be4
Revises: e8c4a1b9f2d3
Create Date: 2026-07-04 14:14:00.063422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f20d83768be4'
down_revision: Union[str, None] = 'e8c4a1b9f2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL requires it to be outside a transaction or auto-commit,
    # but Alembic usually handles commit if we execute directly or we can use generic ALTER TYPE
    op.execute("ALTER TYPE gametype ADD VALUE IF NOT EXISTS 'HEX_5X5'")


def downgrade() -> None:
    # Removing a value from a PostgreSQL ENUM is complex (requires recreating the type).
    pass
