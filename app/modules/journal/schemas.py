from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JournalEntryCreate(BaseModel):
    content: str = Field(min_length=1)
    # Linking to a plot is optional — entries can be standalone reflections
    plot_id: UUID | None = None
    mood_tag: str | None = Field(default=None, max_length=50)
    # media_urls is populated server-side after S3 upload; clients send an empty list
    media_urls: list[str] = []


class JournalEntryUpdate(BaseModel):
    # All optional — PATCH semantics
    content: str | None = Field(default=None, min_length=1)
    mood_tag: str | None = None
    media_urls: list[str] | None = None


class JournalEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    plot_id: UUID | None
    content: str
    mood_tag: str | None
    media_urls: list[str]
    created_at: datetime
    updated_at: datetime


class JournalEntryFilters(BaseModel):
    """Optional query filters passed to JournalRepository.list_for_user.

    Unset fields are ignored — callers only provide the filters they need.
    """
    plot_id: UUID | None = None
    mood_tag: str | None = None
    # Inclusive date range — useful for timeline views
    before: datetime | None = None
    after: datetime | None = None
