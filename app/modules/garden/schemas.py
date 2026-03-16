from datetime import date as Date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.garden.models import RelationshipTag


class StoryCreate(BaseModel):
    content: str = Field(min_length=1)


class StoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plot_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime


class DetailCreate(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)
    category: str | None = Field(default=None, max_length=50)


class DetailUpdate(BaseModel):
    key: str | None = Field(default=None, max_length=100)
    value: str | None = Field(default=None, max_length=500)
    category: str | None = None


class DetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plot_id: UUID
    key: str
    value: str
    category: str | None


class CuriosityCreate(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class CuriosityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plot_id: UUID
    question: str
    is_resolved: bool
    created_at: datetime


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    date: Date
    notes: str | None = None
    is_recurring: bool = False


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    date: Date | None = None
    notes: str | None = None
    is_recurring: bool | None = None


class MilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plot_id: UUID
    title: str
    date: Date
    notes: str | None
    is_recurring: bool
    created_at: datetime


class PlotCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    relationship_tag: RelationshipTag = RelationshipTag.FRIEND
    custom_tag: str | None = Field(default=None, max_length=50)


class PlotUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    relationship_tag: RelationshipTag | None = None
    custom_tag: str | None = None
    last_connected: datetime | None = None
    is_archived: bool | None = None


class PlotListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    relationship_tag: RelationshipTag
    custom_tag: str | None
    photo_url: str | None
    last_connected: datetime | None
    is_archived: bool
    created_at: datetime


class PlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    relationship_tag: RelationshipTag
    custom_tag: str | None
    photo_url: str | None
    last_connected: datetime | None
    is_archived: bool
    stories: list[StoryRead] = []
    details: list[DetailRead] = []
    curiosities: list[CuriosityRead] = []
    milestones: list[MilestoneRead] = []
    created_at: datetime
    updated_at: datetime
