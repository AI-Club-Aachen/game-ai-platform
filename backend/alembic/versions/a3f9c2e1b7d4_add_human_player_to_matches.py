"""add human player to matches

Revision ID: a3f9c2e1b7d4
Revises: e9c1d06f4728
Create Date: 2026-11-09 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a3f9c2e1b7d4"
down_revision: str | None = "e9c1d06f4728"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Human-vs-agent matches: who plays by hand, in which seat, and their display name.
    op.add_column("matches", sa.Column("human_user_id", sa.Uuid(), nullable=True))
    op.add_column("matches", sa.Column("human_player_index", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("human_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_index(op.f("ix_matches_human_user_id"), "matches", ["human_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_matches_human_user_id"), table_name="matches")
    op.drop_column("matches", "human_name")
    op.drop_column("matches", "human_player_index")
    op.drop_column("matches", "human_user_id")
