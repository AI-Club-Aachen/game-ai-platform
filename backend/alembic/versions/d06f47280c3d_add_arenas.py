"""add arenas

Revision ID: d06f47280c3d
Revises: e8c4a1b9f2d3
Create Date: 2026-07-04 14:50:14.103852

"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d06f47280c3d"
down_revision: str | None = "e8c4a1b9f2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("COMMIT")
    op.create_table("arenas",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column(
        "game_type",
        postgresql.ENUM("TICTACTOE", "CHESS", "CONNECT_FOUR", "HEX", name="gametype", create_type=False),
        nullable=False,
    ),
    sa.Column("config", sa.JSON(), nullable=True),
    sa.Column("password", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(), nullable=False),
    sa.Column("updated_at", sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_arenas_game_type"), "arenas", ["game_type"], unique=False)
    op.create_index(op.f("ix_arenas_id"), "arenas", ["id"], unique=False)

    # Add columns as nullable first
    op.add_column("agents", sa.Column("arena_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_agents_arena_id"), "agents", ["arena_id"], unique=False)
    op.create_foreign_key(None, "agents", "arenas", ["arena_id"], ["id"])

    op.add_column("matches", sa.Column("arena_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_matches_arena_id"), "matches", ["arena_id"], unique=False)
    op.create_foreign_key(None, "matches", "arenas", ["arena_id"], ["id"])

    op.add_column("submissions", sa.Column("arena_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_submissions_arena_id"), "submissions", ["arena_id"], unique=False)
    op.create_foreign_key(None, "submissions", "arenas", ["arena_id"], ["id"])

    op.add_column("tournaments", sa.Column("arena_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_tournaments_arena_id"), "tournaments", ["arena_id"], unique=False)
    op.create_foreign_key(None, "tournaments", "arenas", ["arena_id"], ["id"])

    # Seed default arenas
    tictactoe_arena_id = str(uuid.uuid4())
    chess_arena_id = str(uuid.uuid4())
    connect_four_arena_id = str(uuid.uuid4())
    hex_11_arena_id = str(uuid.uuid4())

    now = datetime.now(UTC)

    op.execute(
        "INSERT INTO arenas (id, name, description, game_type, config, is_active, created_at, updated_at) VALUES "
        f"('{tictactoe_arena_id}', 'Tic-Tac-Toe Arena', 'Classic 3x3 Tic-Tac-Toe', "
        f"'TICTACTOE', '{{\"turn_time_limit\": 5.0}}', true, '{now}', '{now}'),"
        f"('{chess_arena_id}', 'Chess Arena', 'Classic Strategy Chess', "
        f"'CHESS', '{{}}', true, '{now}', '{now}'),"
        f"('{connect_four_arena_id}', 'Connect Four Arena', 'Connect 4 in a row', "
        f"'CONNECT_FOUR', '{{}}', true, '{now}', '{now}'),"
        f"('{hex_11_arena_id}', 'Hex 11x11 Arena', 'Standard 11x11 Hex board', "
        f"'HEX', '{{\"board_size\": 11}}', true, '{now}', '{now}')"
    )

    # Migrate existing rows to default arenas
    op.execute(f"UPDATE agents SET arena_id = '{tictactoe_arena_id}' WHERE game_type = 'TICTACTOE'")
    op.execute(f"UPDATE agents SET arena_id = '{chess_arena_id}' WHERE game_type = 'CHESS'")
    op.execute(f"UPDATE agents SET arena_id = '{connect_four_arena_id}' WHERE game_type = 'CONNECT_FOUR'")
    op.execute(f"UPDATE agents SET arena_id = '{hex_11_arena_id}' WHERE game_type = 'HEX'")

    op.execute(f"UPDATE submissions SET arena_id = '{tictactoe_arena_id}' WHERE game_type = 'TICTACTOE'")
    op.execute(f"UPDATE submissions SET arena_id = '{chess_arena_id}' WHERE game_type = 'CHESS'")
    op.execute(f"UPDATE submissions SET arena_id = '{connect_four_arena_id}' WHERE game_type = 'CONNECT_FOUR'")
    op.execute(f"UPDATE submissions SET arena_id = '{hex_11_arena_id}' WHERE game_type = 'HEX'")

    op.execute(f"UPDATE matches SET arena_id = '{tictactoe_arena_id}' WHERE game_type = 'TICTACTOE'")
    op.execute(f"UPDATE matches SET arena_id = '{chess_arena_id}' WHERE game_type = 'CHESS'")
    op.execute(f"UPDATE matches SET arena_id = '{connect_four_arena_id}' WHERE game_type = 'CONNECT_FOUR'")
    op.execute(f"UPDATE matches SET arena_id = '{hex_11_arena_id}' WHERE game_type = 'HEX'")

    op.execute(f"UPDATE tournaments SET arena_id = '{tictactoe_arena_id}' WHERE game_type = 'TICTACTOE'")
    op.execute(f"UPDATE tournaments SET arena_id = '{chess_arena_id}' WHERE game_type = 'CHESS'")
    op.execute(f"UPDATE tournaments SET arena_id = '{connect_four_arena_id}' WHERE game_type = 'CONNECT_FOUR'")
    op.execute(f"UPDATE tournaments SET arena_id = '{hex_11_arena_id}' WHERE game_type = 'HEX'")

    # Set non-nullable constraints
    op.alter_column("agents", "arena_id", nullable=False)
    op.alter_column("submissions", "arena_id", nullable=False)
    op.alter_column("matches", "arena_id", nullable=False)
    op.alter_column("tournaments", "arena_id", nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "tournaments", type_="foreignkey")
    op.drop_index(op.f("ix_tournaments_arena_id"), table_name="tournaments")
    op.drop_column("tournaments", "arena_id")
    op.drop_constraint(None, "submissions", type_="foreignkey")
    op.drop_index(op.f("ix_submissions_arena_id"), table_name="submissions")
    op.drop_column("submissions", "arena_id")
    op.drop_constraint(None, "matches", type_="foreignkey")
    op.drop_index(op.f("ix_matches_arena_id"), table_name="matches")
    op.drop_column("matches", "arena_id")
    op.drop_constraint(None, "agents", type_="foreignkey")
    op.drop_index(op.f("ix_agents_arena_id"), table_name="agents")
    op.drop_column("agents", "arena_id")
    op.drop_index(op.f("ix_arenas_id"), table_name="arenas")
    op.drop_index(op.f("ix_arenas_game_type"), table_name="arenas")
    op.drop_table("arenas")
    # ### end Alembic commands ###
