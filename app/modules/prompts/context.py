import random
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.garden.service import GardenService
from app.modules.journal.repository import JournalRepository
from app.modules.journal.schemas import JournalEntryFilters
from app.modules.prompts.schemas import PlotContext


def _project_milestone_date(milestone_date: date) -> date:
    """Project a (possibly recurring) milestone date to this or next year."""
    today = date.today()
    projected = milestone_date.replace(year=today.year)
    if projected < today:
        try:
            projected = milestone_date.replace(year=today.year + 1)
        except ValueError:
            # Feb 29 on a non-leap year — clamp to Feb 28 to stay valid
            projected = projected.replace(day=28)
    return projected


def _days_since(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    # Naive datetimes from the DB are assumed UTC; make them aware before differencing
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).days


class ContextAssembler:
    async def for_plot(
        self, db: AsyncSession, plot_id: UUID, user_id: UUID
    ) -> PlotContext:
        plot = await GardenService().get_plot(db, plot_id, user_id)
        # Fetch only the most recent 3 entries to keep the prompt payload small
        journal_entries = await JournalRepository().list_for_user(
            db, user_id, JournalEntryFilters(plot_id=plot_id), limit=3
        )

        # Cap stories at 5 so the assembled context doesn't overwhelm the LLM context window
        stories = [s.content for s in plot.stories[:5]]
        details = [{"key": d.key, "value": d.value} for d in plot.details]
        # Only surface unresolved curiosities — resolved ones are no longer relevant to prompts
        curiosities = [c.question for c in plot.curiosities if not c.is_resolved]

        milestones = []
        for m in plot.milestones:
            # Recurring milestones need their year projected forward before computing days_until
            effective = _project_milestone_date(m.date) if m.is_recurring else m.date
            days_until = (effective - date.today()).days
            milestones.append({
                "title": m.title,
                "date": effective.isoformat(),
                "days_until": days_until,
                "is_recurring": m.is_recurring,
            })

        # Truncate each entry to 300 chars so journal snippets hint at context without dominating it
        recent_journal = [e.content[:300] for e in journal_entries]

        # Skip interest groups with no fields — they carry no useful signal for the prompt
        interest_groups = [
            {
                "label": g.custom_label or g.group_type,  # prefer user-supplied label over enum value
                "fields": list(g.fields or []),
            }
            for g in plot.interest_groups
            if g.fields
        ]

        return PlotContext(
            display_name=plot.display_name,
            relationship_tag=plot.relationship_tag.replace("_", " "),  # normalise enum slug for human-readable display
            last_connected=plot.last_connected,
            days_since_contact=_days_since(plot.last_connected),
            stories=stories,
            details=details,
            curiosities=curiosities,
            milestones=milestones,
            recent_journal=recent_journal,
            interest_groups=interest_groups,
        )

    async def for_daily(
        self, db: AsyncSession, user_id: UUID
    ) -> tuple[PlotContext, UUID, str] | None:
        plots = await GardenService().list_plots(db, user_id)
        if not plots:
            return None

        # Prefer plots not connected in the last 14 days
        stale = [
            p for p in plots
            # Fallback of 999 treats never-contacted plots as maximally stale
            if not p.is_archived and (_days_since(p.last_connected) or 999) > 14
        ]
        # Fall back to any active plot if all were recently contacted
        candidates = stale if stale else [p for p in plots if not p.is_archived]
        if not candidates:
            # Last resort: include archived plots rather than returning nothing
            candidates = plots

        chosen = random.choice(candidates)
        context = await self.for_plot(db, chosen.id, user_id)
        return context, chosen.id, chosen.display_name
