"""decouple submissions from agents

Revision ID: 8b7a2c3f1d4e
Revises: 3c1df0b8d7b4
Create Date: 2026-03-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8b7a2c3f1d4e"
down_revision: str | Sequence[str] | None = "3c1df0b8d7b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "game_type",
            postgresql.ENUM("TICTACTOE", "CHESS", "CONNECT_FOUR", name="gametype", create_type=False),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_agents_game_type"), "agents", ["game_type"], unique=False)
    op.create_foreign_key(
        "fk_agents_active_submission_id_submissions",
        "agents",
        "submissions",
        ["active_submission_id"],
        ["id"],
    )

    op.execute("UPDATE agents SET game_type = 'CHESS' WHERE game_type IS NULL")
    op.alter_column("agents", "game_type", nullable=False)

    op.drop_index(op.f("ix_submissions_agent_id"), table_name="submissions")
    op.drop_column("submissions", "agent_id")


def downgrade() -> None:
    op.add_column("submissions", sa.Column("agent_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_submissions_agent_id"), "submissions", ["agent_id"], unique=False)

    op.drop_constraint("fk_agents_active_submission_id_submissions", "agents", type_="foreignkey")
    op.drop_index(op.f("ix_agents_game_type"), table_name="agents")
    op.drop_column("agents", "game_type")
