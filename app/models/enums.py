from __future__ import annotations

from enum import StrEnum


class CampaignStatus(StrEnum):
    PENDING = "PENDING"
    DISCOVERING = "DISCOVERING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"


class EmailStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    BOUNCED = "BOUNCED"
