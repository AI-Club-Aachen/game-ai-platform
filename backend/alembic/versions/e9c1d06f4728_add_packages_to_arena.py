"""add packages to arena

Revision ID: e9c1d06f4728
Revises: d06f47280c3d
Create Date: 2026-07-19 01:29:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e9c1d06f4728"
down_revision: str | None = "d06f47280c3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add packages column to arenas with default value of 'numpy'
    op.add_column(
        "arenas",
        sa.Column("packages", sqlmodel.sql.sqltypes.AutoString(), server_default="numpy", nullable=False)
    )


def downgrade() -> None:
    op.drop_column("arenas", "packages")
