"""add names to agents and submissions

Revision ID: c1f2d3e4a5b6
Revises: 8b7a2c3f1d4e
Create Date: 2026-03-30 13:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c1f2d3e4a5b6"
down_revision: str | Sequence[str] | None = "8b7a2c3f1d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("name", sa.String(), nullable=True))
    op.add_column("submissions", sa.Column("name", sa.String(), nullable=True))

    op.execute("UPDATE agents SET name = CAST(id AS TEXT) WHERE name IS NULL OR name = ''")
    op.execute("UPDATE submissions SET name = CAST(id AS TEXT) WHERE name IS NULL OR name = ''")

    op.alter_column("agents", "name", nullable=False)
    op.alter_column("submissions", "name", nullable=False)


def downgrade() -> None:
    op.drop_column("submissions", "name")
    op.drop_column("agents", "name")
