from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JournalEntryCreate(BaseModel):
    content: str = Field(min_length=1)
    plot_id: UUID | None = None
    mood_tag: str | None = Field(default=None, max_length=50)
    media_urls: list[str] = []


class JournalEntryUpdate(BaseModel):
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
    plot_id: UUID | None = None
    mood_tag: str | None = None
    before: datetime | None = None
    after: datetime | None = None
