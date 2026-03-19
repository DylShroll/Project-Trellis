from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery = Celery(
    "trellis",
    broker=settings.celery_broker_url,   # Redis db1 — keeps tasks separate from app cache (db0)
    backend=settings.celery_result_backend,  # Redis db2 — result storage
    # Explicit include list avoids auto-discovery scanning all modules on worker start
    include=["app.workers.tasks.notifications"],
)

celery.conf.update(
    # JSON serialisation is safe across Python versions and languages; avoid pickle
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,  # all datetimes in task payloads are UTC
    beat_schedule={
        # Both tasks run once a day; beat_schedule uses seconds as the unit
        "daily-nudge-check": {
            "task": "app.workers.tasks.notifications.check_reconnection_nudges",
            "schedule": 86400.0,  # 24 h
        },
        "milestone-reminder-check": {
            "task": "app.workers.tasks.notifications.check_milestone_reminders",
            "schedule": 86400.0,  # 24 h
        },
    },
)
