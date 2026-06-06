from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.security import normalize_domain
from app.models.enums import CampaignStatus
from app.schemas.base import ORMModel
from app.schemas.email import EmailRead


class PipelineSummary(BaseModel):
    companies_found: int = 0
    contacts_found: int = 0
    verified_emails: int = 0
    emails_generated: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
    emails_bounced: int = 0


class PipelineStartRequest(BaseModel):
    domain: str = Field(..., examples=["openai.com"])
    auto_send: bool = False

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        return normalize_domain(value)


class PipelineStartResponse(BaseModel):
    campaign_id: uuid.UUID
    status: CampaignStatus
    message: str


class CampaignRead(ORMModel):
    id: uuid.UUID
    source_domain: str
    status: CampaignStatus
    summary: dict[str, Any]
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class PipelineStatusResponse(BaseModel):
    campaign: CampaignRead
    summary: PipelineSummary
    emails: list[EmailRead] = []
