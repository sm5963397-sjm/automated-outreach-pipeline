from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.enums import CampaignStatus
from app.repositories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    model = Campaign

    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, source_domain: str) -> Campaign:
        return self.add(
            Campaign(
                source_domain=source_domain,
                status=CampaignStatus.PENDING.value,
                summary={},
            )
        )

    def list(self, limit: int = 100, offset: int = 0) -> list[Campaign]:
        stmt = select(Campaign).order_by(Campaign.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def update_status(
        self,
        campaign: Campaign,
        status: CampaignStatus,
        *,
        summary: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> Campaign:
        campaign.status = status.value
        if summary is not None:
            campaign.summary = summary
        campaign.error_message = error_message
        self.db.flush()
        return campaign

    def require(self, campaign_id: uuid.UUID) -> Campaign:
        campaign = self.get(campaign_id)
        if campaign is None:
            raise LookupError(f"campaign not found: {campaign_id}")
        return campaign
