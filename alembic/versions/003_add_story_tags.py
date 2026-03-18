"""add_story_tags

Revision ID: 003
Revises: 002
Create Date: 2026-03-17

Adds a JSONB `tags` column to the stories table so stories can be
tagged (e.g. "funny", "important") for indexing and filtering.

Run locally (not inside Docker) against the containerised Postgres:
  DATABASE_URL=postgresql+asyncpg://trellis:trellis@localhost:5432/trellis \\
    .venv/bin/alembic upgrade head
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column(
            "tags",
            postgresql.JSONB(),
            server_default="[]",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("stories", "tags")
