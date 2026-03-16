from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery = Celery(
    "trellis",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks.notifications"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "daily-nudge-check": {
            "task": "app.workers.tasks.notifications.check_reconnection_nudges",
            "schedule": 86400.0,  # daily
        },
        "milestone-reminder-check": {
            "task": "app.workers.tasks.notifications.check_milestone_reminders",
            "schedule": 86400.0,  # daily
        },
    },
)
