from datetime import date as Date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.garden.models import RelationshipTag


class StoryCreate(BaseModel):
    content: str = Field(min_length=1)


class StoryUpdate(BaseModel):
    # All fields optional — callers send only what changed
    content: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None


class StoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plot_id: UUID
    content: str
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime


class DetailCreate(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)
    # category groups details into accordion sections in the UI (e.g. "Music", "Food & Drink")
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
    # When True, Celery will generate an annual reminder for this milestone
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
    # custom_tag is only used when relationship_tag == CUSTOM
    custom_tag: str | None = Field(default=None, max_length=50)


class PlotUpdate(BaseModel):
    # All fields optional — sent as PATCH; unset fields are ignored in the repository
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    relationship_tag: RelationshipTag | None = None
    custom_tag: str | None = None
    photo_url: str | None = Field(default=None, max_length=500)
    last_connected: datetime | None = None
    is_archived: bool | None = None


class PlotListItem(BaseModel):
    """Lightweight summary used by the garden list page — avoids loading child collections."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    relationship_tag: RelationshipTag
    custom_tag: str | None
    photo_url: str | None
    last_connected: datetime | None
    is_archived: bool
    created_at: datetime


class InterestGroupFieldItem(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)


class InterestGroupCreate(BaseModel):
    # group_type should match a key in INTEREST_CATEGORIES (e.g. "Music", "Books")
    group_type: str = Field(min_length=1, max_length=50)
    # custom_label overrides the group_type display name in the UI
    custom_label: str | None = Field(default=None, max_length=100)


class InterestGroupAddField(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)


class InterestGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plot_id: UUID
    group_type: str
    custom_label: str | None
    fields: list[dict]
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PlotRead(BaseModel):
    """Full plot representation including all child collections, used on the detail page."""
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
    interest_groups: list[InterestGroupRead] = []
    created_at: datetime
    updated_at: datetime
