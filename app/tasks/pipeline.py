from __future__ import annotations

import uuid

from app.database.session import SessionLocal
from app.services.factory import build_workflow
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.pipeline.run_pipeline")  # type: ignore[untyped-decorator]
def run_pipeline_task(campaign_id: str, domain: str, auto_send: bool = False) -> dict[str, object]:
    with SessionLocal() as db:
        workflow = build_workflow(db)
        summary = workflow.run(uuid.UUID(campaign_id), domain, auto_send=auto_send)
        return summary.model_dump()


@celery_app.task(name="app.tasks.pipeline.send_campaign")  # type: ignore[untyped-decorator]
def send_campaign_task(campaign_id: str) -> dict[str, object]:
    with SessionLocal() as db:
        workflow = build_workflow(db)
        summary = workflow.send_campaign(uuid.UUID(campaign_id))
        return summary.model_dump()
