"""initial_schema

Revision ID: 001
Revises:
Create Date: 2026-03-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgcrypto for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Enums — use DO block for idempotent creation
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE relationship_tag_enum AS ENUM (
                'partner', 'family', 'close_friend', 'friend',
                'colleague', 'mentor', 'community', 'custom'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notification_type_enum AS ENUM (
                'milestone_reminder', 'reconnection_nudge', 'daily_prompt'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(200), nullable=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("preferences", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # plots
    op.create_table(
        "plots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("relationship_tag", postgresql.ENUM("partner", "family", "close_friend", "friend", "colleague", "mentor", "community", "custom", name="relationship_tag_enum", create_type=False), nullable=False, server_default="friend"),
        sa.Column("custom_tag", sa.String(50), nullable=True),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("last_connected", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_plots_user_id", "plots", ["user_id"])

    # stories
    op.create_table(
        "stories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("plot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_stories_plot_id", "stories", ["plot_id"])

    # details
    op.create_table(
        "details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("plot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
    )
    op.create_index("ix_details_plot_id", "details", ["plot_id"])

    # curiosities
    op.create_table(
        "curiosities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("plot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_curiosities_plot_id", "curiosities", ["plot_id"])

    # milestones
    op.create_table(
        "milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("plot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_recurring", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_milestones_plot_id", "milestones", ["plot_id"])

    # journal_entries
    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("mood_tag", sa.String(50), nullable=True),
        sa.Column("media_urls", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_journal_entries_user_id", "journal_entries", ["user_id"])
    op.create_index("ix_journal_entries_plot_id", "journal_entries", ["plot_id"])

    # notifications
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", postgresql.ENUM("milestone_reminder", "reconnection_nudge", "daily_prompt", name="notification_type_enum", create_type=False), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("journal_entries")
    op.drop_table("milestones")
    op.drop_table("curiosities")
    op.drop_table("details")
    op.drop_table("stories")
    op.drop_table("plots")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS notification_type_enum")
    op.execute("DROP TYPE IF EXISTS relationship_tag_enum")
