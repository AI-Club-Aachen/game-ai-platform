"""add platform flags

Revision ID: e8c4a1b9f2d3
Revises: d7e1f3a9b2c5
Create Date: 2026-06-12 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e8c4a1b9f2d3"
down_revision: str | None = "d7e1f3a9b2c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_flags",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("platform_flags")
