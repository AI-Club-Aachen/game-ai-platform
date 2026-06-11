"""add_token_version_to_users

Session invalidation on password change/reset (M-11): a per-user counter that is
embedded in JWTs and bumped on password change/reset so older tokens are rejected.

Revision ID: c7d2f9a4e1b3
Revises: b3a3db84af20
Create Date: 2026-06-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c7d2f9a4e1b3"
down_revision: str | None = "b3a3db84af20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
