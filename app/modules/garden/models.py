import enum
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RelationshipTag(str, enum.Enum):
    PARTNER = "partner"
    FAMILY = "family"
    CLOSE_FRIEND = "close_friend"
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    MENTOR = "mentor"
    COMMUNITY = "community"
    CUSTOM = "custom"


class Plot(Base):
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
        Enum(RelationshipTag, name="relationship_tag_enum"),
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


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    plot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("plots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
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
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    plot: Mapped["Plot"] = relationship(back_populates="details")


class Curiosity(Base):
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
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plot: Mapped["Plot"] = relationship(back_populates="milestones")
