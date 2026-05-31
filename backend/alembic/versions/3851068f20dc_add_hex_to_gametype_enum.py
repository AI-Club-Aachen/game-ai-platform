"""add HEX to gametype enum

Revision ID: 3851068f20dc
Revises: b1cb92f7e0ab
Create Date: 2026-05-29 00:33:30.078680

"""
from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3851068f20dc"
down_revision: str | None = "b1cb92f7e0ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL requires it to be outside a transaction or auto-commit,
    # but Alembic usually handles commit if we execute directly or we can use generic ALTER TYPE
    op.execute("ALTER TYPE gametype ADD VALUE IF NOT EXISTS 'HEX'")


def downgrade() -> None:
    # Removing a value from a PostgreSQL ENUM is complex (requires recreating the type).
    pass
