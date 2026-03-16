"""Celery application configuration (ADR-0003)."""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "expense_portal",
    broker=settings.redis_url,
    backend=settings.database_url.replace("postgresql+asyncpg", "db+postgresql+psycopg2"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.ocr_tasks.*": {"queue": "ocr"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.integration_tasks.*": {"queue": "integrations"},
        "app.tasks.scheduled_tasks.*": {"queue": "scheduled"},
    },
    beat_schedule={
        "sync-workday-nightly": {
            "task": "app.tasks.scheduled_tasks.sync_workday",
            "schedule": crontab(hour=2, minute=0),
        },
        "check-stale-approvals": {
            "task": "app.tasks.scheduled_tasks.check_stale_approvals",
            "schedule": crontab(hour=8, minute=0),
        },
        "send-approval-reminders": {
            "task": "app.tasks.scheduled_tasks.send_approval_reminders",
            "schedule": crontab(hour=8, minute=0),
        },
    },
)

celery_app.autodiscover_tasks([
    "app.tasks.ocr_tasks",
    "app.tasks.notification_tasks",
    "app.tasks.integration_tasks",
    "app.tasks.scheduled_tasks",
])
