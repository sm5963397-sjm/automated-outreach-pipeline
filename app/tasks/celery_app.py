from __future__ import annotations

from celery import Celery

from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings)

celery_app = Celery(
    "outreach_pipeline",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.pipeline"],
)
celery_app.conf.update(
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_EAGER_PROPAGATES,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
)
