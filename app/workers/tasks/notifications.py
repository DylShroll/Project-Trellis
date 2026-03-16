"""
Notification tasks — check reconnection nudges and milestone reminders.
Each task runs asyncio.run() over an async implementation that uses AsyncSessionLocal.
"""
import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.modules.garden.models import Milestone, Plot
from app.modules.notifications.models import Notification, NotificationType
from app.modules.notifications.repository import NotificationRepository
from app.workers.celery_app import celery


# ── Reconnection nudges ───────────────────────────────────────────────────────

async def _check_reconnection_nudges_async() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    cooldown = datetime.now(timezone.utc) - timedelta(days=7)

    async with AsyncSessionLocal() as db:
        # Fetch all non-archived plots where last_connected is stale or null
        result = await db.execute(
            select(Plot).where(
                Plot.is_archived == False,  # noqa: E712
                (Plot.last_connected == None) | (Plot.last_connected < cutoff),  # noqa: E711
            )
        )
        plots = list(result.scalars().all())

        repo = NotificationRepository()
        for plot in plots:
            # Cooldown: skip if a RECONNECTION_NUDGE was created in the last 7 days
            recent_check = await db.execute(
                select(Notification).where(
                    Notification.user_id == plot.user_id,
                    Notification.type == NotificationType.RECONNECTION_NUDGE,
                    Notification.created_at >= cooldown,
                )
            )
            recent_notifications = list(recent_check.scalars().all())
            already_notified = any(
                str(n.payload.get("plot_id")) == str(plot.id)
                for n in recent_notifications
            )
            if already_notified:
                continue

            if plot.last_connected:
                if plot.last_connected.tzinfo is None:
                    lc = plot.last_connected.replace(tzinfo=timezone.utc)
                else:
                    lc = plot.last_connected
                days_since = (datetime.now(timezone.utc) - lc).days
            else:
                days_since = None

            message = (
                f"You haven't connected with {plot.display_name} in {days_since} days."
                if days_since is not None
                else f"You haven't logged a connection with {plot.display_name} yet."
            )

            await repo.create(
                db,
                user_id=plot.user_id,
                notification_type=NotificationType.RECONNECTION_NUDGE,
                payload={
                    "plot_id": str(plot.id),
                    "plot_name": plot.display_name,
                    "days_since": days_since,
                    "message": message,
                },
            )


@celery.task(name="app.workers.tasks.notifications.check_reconnection_nudges")
def check_reconnection_nudges() -> None:
    asyncio.run(_check_reconnection_nudges_async())


# ── Milestone reminders ───────────────────────────────────────────────────────

def _project_milestone_date(milestone_date: date) -> date:
    today = date.today()
    projected = milestone_date.replace(year=today.year)
    if projected < today:
        try:
            projected = milestone_date.replace(year=today.year + 1)
        except ValueError:
            projected = projected.replace(day=28)
    return projected


async def _check_milestone_reminders_async() -> None:
    today = date.today()
    window_end = today + timedelta(days=7)
    current_year = today.year

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Milestone).join(Plot).where(
                Plot.is_archived == False  # noqa: E712
            )
        )
        milestones = list(result.scalars().all())

        repo = NotificationRepository()
        for milestone in milestones:
            effective_date = (
                _project_milestone_date(milestone.date)
                if milestone.is_recurring
                else milestone.date
            )

            if not (today <= effective_date <= window_end):
                continue

            # De-duplicate: skip if a MILESTONE_REMINDER already exists this year
            year_start = datetime(current_year, 1, 1, tzinfo=timezone.utc)
            year_end = datetime(current_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            existing_check = await db.execute(
                select(Notification).where(
                    Notification.type == NotificationType.MILESTONE_REMINDER,
                    Notification.created_at >= year_start,
                    Notification.created_at <= year_end,
                )
            )
            existing = list(existing_check.scalars().all())
            already_notified = any(
                str(n.payload.get("milestone_id")) == str(milestone.id)
                for n in existing
            )
            if already_notified:
                continue

            # Fetch plot for user_id and name
            plot_result = await db.execute(
                select(Plot).where(Plot.id == milestone.plot_id)
            )
            plot = plot_result.scalar_one_or_none()
            if not plot:
                continue

            days_until = (effective_date - today).days
            message = (
                f"{milestone.title} for {plot.display_name} is in {days_until} days."
                if days_until > 0
                else f"Today is {milestone.title} for {plot.display_name}."
            )

            await repo.create(
                db,
                user_id=plot.user_id,
                notification_type=NotificationType.MILESTONE_REMINDER,
                payload={
                    "milestone_id": str(milestone.id),
                    "plot_id": str(plot.id),
                    "plot_name": plot.display_name,
                    "milestone_title": milestone.title,
                    "effective_date": effective_date.isoformat(),
                    "days_until": days_until,
                    "message": message,
                },
            )


@celery.task(name="app.workers.tasks.notifications.check_milestone_reminders")
def check_milestone_reminders() -> None:
    asyncio.run(_check_milestone_reminders_async())
