"""
Notification tasks — Phase 2 will flesh these out with real logic.
Placeholders exist here so the Celery beat schedule can reference them.
"""
import asyncio

from app.workers.celery_app import celery


@celery.task(name="app.workers.tasks.notifications.check_reconnection_nudges")
def check_reconnection_nudges() -> None:
    """
    Scan plots for users who haven't connected with someone in a while
    and create reconnection nudge notifications. Implemented in Phase 2.
    """


@celery.task(name="app.workers.tasks.notifications.check_milestone_reminders")
def check_milestone_reminders() -> None:
    """
    Find recurring milestones approaching within 7 days and create
    milestone reminder notifications. Implemented in Phase 2.
    """
