from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PlotContext(BaseModel):
    display_name: str
    relationship_tag: str
    last_connected: datetime | None
    days_since_contact: int | None
    stories: list[str]           # content only (latest 5)
    details: list[dict]          # {"key": ..., "value": ...}
    curiosities: list[str]       # unresolved questions only
    milestones: list[dict]       # {"title", "date", "days_until", "is_recurring"}
    recent_journal: list[str]    # last 3 entries, truncated to 300 chars
    interest_groups: list[dict] = []   # {"label": str, "fields": [{"key": str, "value": str}]}
    reflection_mode: bool = False      # True when called after a journal entry is saved


class PromptResult(BaseModel):
    prompts: list[str]           # 3–5 strings
    category: str                # "deepening" | "reconnection" | "curiosity_seed" | "milestone" | "daily"
    generated_at: datetime
    plot_id: UUID | None
    plot_name: str | None        # for dashboard display
    cache_hit: bool
