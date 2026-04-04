"""add game type to submissions

Revision ID: b7a1c9e4d2f0
Revises: c1f2d3e4a5b6
Create Date: 2026-04-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7a1c9e4d2f0"
down_revision: str | None = "c1f2d3e4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column(
            "game_type",
            postgresql.ENUM("TICTACTOE", "CHESS", "CONNECT_FOUR", name="gametype", create_type=False),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_submissions_game_type"), "submissions", ["game_type"], unique=False)

    op.execute(
        """
        UPDATE submissions
        SET game_type = agents.game_type
        FROM agents
        WHERE agents.active_submission_id = submissions.id
          AND submissions.game_type IS NULL
        """
    )
    op.execute("UPDATE submissions SET game_type = 'CHESS' WHERE game_type IS NULL")

    op.alter_column("submissions", "game_type", nullable=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_submissions_game_type"), table_name="submissions")
    op.drop_column("submissions", "game_type")
