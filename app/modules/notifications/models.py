import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NotificationType(str, enum.Enum):
    # String enum values stored in Postgres — adding a new type only requires a migration if
    # the DB enum column is used; currently the column is a raw Enum type so values must match.
    MILESTONE_REMINDER = "milestone_reminder"
    RECONNECTION_NUDGE = "reconnection_nudge"
    DAILY_PROMPT = "daily_prompt"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type_enum"), nullable=False
    )
    # Flexible JSONB bag for type-specific data (e.g. plot_id, milestone title)
    # avoids a separate table per notification type
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # scheduled_at: when the Celery task planned to deliver it
    # sent_at: when it was actually persisted / delivered to the user
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="notifications")  # type: ignore[name-defined]
