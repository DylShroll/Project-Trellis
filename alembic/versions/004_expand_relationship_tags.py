"""expand_relationship_tags

Revision ID: 004
Revises: 003
Create Date: 2026-03-20

Adds 8 new values to the relationship_tag_enum PostgreSQL type:
  acquaintance, childhood_friend, online_friend, neighbour,
  collaborator, mentee, ex_partner, inspiration

PostgreSQL allows adding values to an existing enum with ALTER TYPE … ADD VALUE.
These operations are not transactional (they auto-commit), so they are issued
individually and wrapped in DO blocks to skip gracefully if the value already exists.

Run locally against the containerised Postgres:
  DATABASE_URL=postgresql+asyncpg://trellis:trellis@localhost:5432/trellis \\
    .venv/bin/alembic upgrade head
"""
from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# New values to add in the order they should appear in the enum
_NEW_VALUES = [
    "acquaintance",
    "childhood_friend",
    "online_friend",
    "neighbour",
    "collaborator",
    "mentee",
    "ex_partner",
    "inspiration",
]


def upgrade() -> None:
    # ALTER TYPE … ADD VALUE cannot run inside a transaction block, so each
    # statement is executed with op.execute() which issues it outside of the
    # Alembic-managed transaction.  The IF NOT EXISTS guard makes each
    # statement idempotent so re-running the migration is safe.
    for value in _NEW_VALUES:
        op.execute(
            f"ALTER TYPE relationship_tag_enum ADD VALUE IF NOT EXISTS '{value}'"
        )


def downgrade() -> None:
    # PostgreSQL does not support removing individual values from an enum type.
    # A full downgrade would require recreating the type and migrating all
    # existing rows — out of scope for this migration.  Raise to make the
    # limitation explicit rather than silently doing nothing.
    raise NotImplementedError(
        "Downgrading enum values is not supported by PostgreSQL. "
        "Remove the new relationship_tag values manually if needed."
    )
