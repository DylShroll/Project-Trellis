import enum
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RelationshipTag(str, enum.Enum):
    # String-valued enum so values serialize cleanly to/from the DB and JSON
    PARTNER = "partner"
    FAMILY = "family"
    CLOSE_FRIEND = "close_friend"
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    MENTOR = "mentor"
    COMMUNITY = "community"
    CUSTOM = "custom"


class Plot(Base):
    """Central entity — one Plot represents one person in the user's garden."""
    __tablename__ = "plots"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    relationship_tag: Mapped[RelationshipTag] = mapped_column(
        # values_callable ensures the DB enum uses lowercase string values, not Python names
        Enum(RelationshipTag, name="relationship_tag_enum", values_callable=lambda e: [m.value for m in e]),
        default=RelationshipTag.FRIEND,
        nullable=False,
    )
    custom_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_connected: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="plots")  # type: ignore[name-defined]
    # All child collections are eagerly loaded via selectinload in PlotRepository
    stories: Mapped[list["Story"]] = relationship(
        back_populates="plot", cascade="all, delete-orphan", order_by="Story.created_at.desc()"
    )
    details: Mapped[list["Detail"]] = relationship(
        back_populates="plot", cascade="all, delete-orphan"
    )
    curiosities: Mapped[list["Curiosity"]] = relationship(
        back_populates="plot", cascade="all, delete-orphan", order_by="Curiosity.created_at.desc()"
    )
    milestones: Mapped[list["Milestone"]] = relationship(
        back_populates="plot", cascade="all, delete-orphan", order_by="Milestone.date.asc()"
    )
    interest_groups: Mapped[list["InterestGroup"]] = relationship(
        back_populates="plot", cascade="all, delete-orphan", order_by="InterestGroup.sort_order.asc()"
    )


class Story(Base):
    """A freeform memory or narrative about the person."""
    __tablename__ = "stories"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    plot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("plots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Free-form tags for indexing/filtering stories (e.g. ["funny", "important"])
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plot: Mapped["Plot"] = relationship(back_populates="stories")


class Detail(Base):
    """A structured key-value fact about the person (e.g. "Birthday: April 15")."""
    __tablename__ = "details"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    plot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("plots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    # Optional grouping label (e.g. "Music", "Food & Drink"); drives the category accordion in the UI
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    plot: Mapped["Plot"] = relationship(back_populates="details")


class Curiosity(Base):
    """An open question the user wants to ask or explore about the person."""
    __tablename__ = "curiosities"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    plot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("plots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plot: Mapped["Plot"] = relationship(back_populates="curiosities")


class Milestone(Base):
    """A significant date or event in the relationship (birthday, anniversary, etc.)."""
    __tablename__ = "milestones"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    plot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("plots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # When True, the Celery reminder task treats this as an annual recurring event
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plot: Mapped["Plot"] = relationship(back_populates="milestones")


class InterestGroup(Base):
    """A named cluster of key-value fields (e.g. "Music → {Favourite artist: Radiohead}")."""
    __tablename__ = "interest_groups"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    plot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("plots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Canonical type from INTEREST_CATEGORIES (e.g. "Music"); drives icon and prompt generation
    group_type: Mapped[str] = mapped_column(String(50), nullable=False)
    custom_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # JSONB array of {"key": str, "value": str} dicts — avoids a separate join table
    fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plot: Mapped["Plot"] = relationship(back_populates="interest_groups")
