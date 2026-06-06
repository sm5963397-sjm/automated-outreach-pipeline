from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EmailStatus
from app.schemas.base import ORMModel
from app.schemas.contact import ContactRead


class EmailRead(ORMModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    subject: str
    body: str
    status: EmailStatus
    provider_message_id: str | None = None
    error_message: str | None = None
    attempts: int
    sent_at: datetime | None = None
    created_at: datetime
    contact: ContactRead | None = None


class BrevoWebhookEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    event: str
    email: str | None = None
    message_id: str | None = Field(default=None, alias="message-id")
    messageId: str | None = None

    @property
    def normalized_message_id(self) -> str | None:
        return self.message_id or self.messageId

    @property
    def raw(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)
