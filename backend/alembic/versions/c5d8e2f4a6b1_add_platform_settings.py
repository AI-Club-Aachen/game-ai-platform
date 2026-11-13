"""add platform settings

Revision ID: c5d8e2f4a6b1
Revises: a3f9c2e1b7d4
Create Date: 2026-11-11 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c5d8e2f4a6b1"
down_revision: str | None = "a3f9c2e1b7d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("platform_settings")
