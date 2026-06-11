"""add tournaments

Revision ID: d7e1f3a9b2c5
Revises: c7d2f9a4e1b3
Create Date: 2026-06-11 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d7e1f3a9b2c5"
down_revision: str | None = "c7d2f9a4e1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum types manually for PostgreSQL
    bind = op.get_bind()

    sa.Enum("PENDING", "RUNNING", "COMPLETED", "CANCELLED", "NEEDS_ATTENTION", name="tournamentstatus").create(
        bind, checkfirst=True
    )
    sa.Enum("WINNERS", "LOSERS", "GRAND_FINAL", "GRAND_FINAL_RESET", name="bracketside").create(bind, checkfirst=True)
    sa.Enum("PENDING", "IN_PROGRESS", "COMPLETED", "NEEDS_ATTENTION", "CANCELLED", name="matchupstatus").create(
        bind, checkfirst=True
    )
    sa.Enum("WINNER", "LOSER", name="slotsourcerole").create(bind, checkfirst=True)
    sa.Enum("PLAYED", "DRAW_COIN_FLIP", "FORFEIT_CLIENT_ERROR", "ADMIN_RESOLVED", name="gameresolution").create(
        bind, checkfirst=True
    )

    op.create_table(
        "tournaments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "game_type",
            postgresql.ENUM("TICTACTOE", "CHESS", "CONNECT_FOUR", "HEX", name="gametype", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING", "RUNNING", "COMPLETED", "CANCELLED", "NEEDS_ATTENTION",
                name="tournamentstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("winner_agent_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tournaments_id"), "tournaments", ["id"], unique=False)
    op.create_index(op.f("ix_tournaments_game_type"), "tournaments", ["game_type"], unique=False)
    op.create_index(op.f("ix_tournaments_status"), "tournaments", ["status"], unique=False)

    op.create_table(
        "tournament_entrants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tournament_entrants_id"), "tournament_entrants", ["id"], unique=False)
    op.create_index(
        op.f("ix_tournament_entrants_tournament_id"), "tournament_entrants", ["tournament_id"], unique=False
    )
    op.create_index(op.f("ix_tournament_entrants_agent_id"), "tournament_entrants", ["agent_id"], unique=False)

    op.create_table(
        "tournament_matchups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column(
            "bracket",
            postgresql.ENUM(
                "WINNERS", "LOSERS", "GRAND_FINAL", "GRAND_FINAL_RESET", name="bracketside", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("agent1_id", sa.Uuid(), nullable=True),
        sa.Column("agent2_id", sa.Uuid(), nullable=True),
        sa.Column("slot1_source_matchup_id", sa.Uuid(), nullable=True),
        sa.Column(
            "slot1_source_role",
            postgresql.ENUM("WINNER", "LOSER", name="slotsourcerole", create_type=False),
            nullable=True,
        ),
        sa.Column("slot2_source_matchup_id", sa.Uuid(), nullable=True),
        sa.Column(
            "slot2_source_role",
            postgresql.ENUM("WINNER", "LOSER", name="slotsourcerole", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING", "IN_PROGRESS", "COMPLETED", "NEEDS_ATTENTION", "CANCELLED",
                name="matchupstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("winner_agent_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tournament_matchups_id"), "tournament_matchups", ["id"], unique=False)
    op.create_index(
        op.f("ix_tournament_matchups_tournament_id"), "tournament_matchups", ["tournament_id"], unique=False
    )
    op.create_index(op.f("ix_tournament_matchups_stage"), "tournament_matchups", ["stage"], unique=False)
    op.create_index(op.f("ix_tournament_matchups_status"), "tournament_matchups", ["status"], unique=False)

    op.create_table(
        "tournament_games",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("matchup_id", sa.Uuid(), nullable=False),
        sa.Column("game_index", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("winner_agent_id", sa.Uuid(), nullable=True),
        sa.Column(
            "resolution",
            postgresql.ENUM(
                "PLAYED", "DRAW_COIN_FLIP", "FORFEIT_CLIENT_ERROR", "ADMIN_RESOLVED",
                name="gameresolution",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.ForeignKeyConstraint(["matchup_id"], ["tournament_matchups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tournament_games_id"), "tournament_games", ["id"], unique=False)
    op.create_index(op.f("ix_tournament_games_tournament_id"), "tournament_games", ["tournament_id"], unique=False)
    op.create_index(op.f("ix_tournament_games_matchup_id"), "tournament_games", ["matchup_id"], unique=False)
    op.create_index(op.f("ix_tournament_games_match_id"), "tournament_games", ["match_id"], unique=False)

    # Tag matches played as part of a tournament (NULL for normal matches)
    op.add_column("matches", sa.Column("tournament_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_matches_tournament_id"), "matches", ["tournament_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_matches_tournament_id_tournaments"), "matches", "tournaments", ["tournament_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_matches_tournament_id_tournaments"), "matches", type_="foreignkey")
    op.drop_index(op.f("ix_matches_tournament_id"), table_name="matches")
    op.drop_column("matches", "tournament_id")

    op.drop_index(op.f("ix_tournament_games_match_id"), table_name="tournament_games")
    op.drop_index(op.f("ix_tournament_games_matchup_id"), table_name="tournament_games")
    op.drop_index(op.f("ix_tournament_games_tournament_id"), table_name="tournament_games")
    op.drop_index(op.f("ix_tournament_games_id"), table_name="tournament_games")
    op.drop_table("tournament_games")

    op.drop_index(op.f("ix_tournament_matchups_status"), table_name="tournament_matchups")
    op.drop_index(op.f("ix_tournament_matchups_stage"), table_name="tournament_matchups")
    op.drop_index(op.f("ix_tournament_matchups_tournament_id"), table_name="tournament_matchups")
    op.drop_index(op.f("ix_tournament_matchups_id"), table_name="tournament_matchups")
    op.drop_table("tournament_matchups")

    op.drop_index(op.f("ix_tournament_entrants_agent_id"), table_name="tournament_entrants")
    op.drop_index(op.f("ix_tournament_entrants_tournament_id"), table_name="tournament_entrants")
    op.drop_index(op.f("ix_tournament_entrants_id"), table_name="tournament_entrants")
    op.drop_table("tournament_entrants")

    op.drop_index(op.f("ix_tournaments_status"), table_name="tournaments")
    op.drop_index(op.f("ix_tournaments_game_type"), table_name="tournaments")
    op.drop_index(op.f("ix_tournaments_id"), table_name="tournaments")
    op.drop_table("tournaments")

    bind = op.get_bind()
    sa.Enum(name="gameresolution").drop(bind, checkfirst=True)
    sa.Enum(name="slotsourcerole").drop(bind, checkfirst=True)
    sa.Enum(name="matchupstatus").drop(bind, checkfirst=True)
    sa.Enum(name="bracketside").drop(bind, checkfirst=True)
    sa.Enum(name="tournamentstatus").drop(bind, checkfirst=True)
