from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.security import require_api_key
from app.database.session import get_db
from app.models.enums import CampaignStatus
from app.repositories import CampaignRepository, EmailRepository
from app.schemas.campaign import (
    CampaignRead,
    PipelineStartRequest,
    PipelineStartResponse,
    PipelineStatusResponse,
    PipelineSummary,
)
from app.schemas.email import EmailRead
from app.tasks.pipeline import run_pipeline_task, send_campaign_task

router = APIRouter(prefix="/pipeline", tags=["pipeline"], dependencies=[Depends(require_api_key)])


@router.post("/start", response_model=PipelineStartResponse, status_code=status.HTTP_202_ACCEPTED)
def start_pipeline(
    payload: PipelineStartRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PipelineStartResponse:
    campaign_repo = CampaignRepository(db)
    campaign = campaign_repo.create(payload.domain)
    db.commit()
    run_pipeline_task.delay(str(campaign.id), payload.domain, payload.auto_send)
    message = (
        "Pipeline queued. It will send automatically after discovery."
        if payload.auto_send
        else "Pipeline queued. Review summary, then approve sending with POST /pipeline/{id}/send."
    )
    return PipelineStartResponse(
        campaign_id=campaign.id,
        status=CampaignStatus(campaign.status),
        message=message,
    )


@router.get("/{campaign_id}", response_model=PipelineStatusResponse)
def pipeline_status(
    campaign_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PipelineStatusResponse:
    campaign = CampaignRepository(db).get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="campaign not found")
    emails = EmailRepository(db).for_campaign(campaign_id)
    summary_data = PipelineSummary().model_dump()
    summary_data.update(campaign.summary or {})
    return PipelineStatusResponse(
        campaign=CampaignRead.model_validate(campaign),
        summary=PipelineSummary.model_validate(summary_data),
        emails=[EmailRead.model_validate(email) for email in emails],
    )


@router.post(
    "/{campaign_id}/send",
    response_model=PipelineStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def approve_send(
    campaign_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PipelineStartResponse:
    campaign = CampaignRepository(db).get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="campaign not found")
    if campaign.status not in {
        CampaignStatus.AWAITING_APPROVAL.value,
        CampaignStatus.PARTIAL_FAILURE.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"campaign is not ready to send; current status is {campaign.status}",
        )
    send_campaign_task.delay(str(campaign_id))
    return PipelineStartResponse(
        campaign_id=campaign_id,
        status=CampaignStatus(campaign.status),
        message="Campaign send queued.",
    )
