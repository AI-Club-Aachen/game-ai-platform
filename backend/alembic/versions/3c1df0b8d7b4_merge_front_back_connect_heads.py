"""merge front back connect heads

Revision ID: 3c1df0b8d7b4
Revises: ef450c3b7b81, ec3ce9a59142
Create Date: 2026-03-29 19:20:00.000000

"""

from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "3c1df0b8d7b4"
down_revision: tuple[str, str] = ("ef450c3b7b81", "ec3ce9a59142")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
