from __future__ import annotations

import builtins
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.contact import Contact
from app.models.email import Email
from app.models.enums import EmailStatus
from app.repositories.base import BaseRepository


class EmailRepository(BaseRepository[Email]):
    model = Email

    def __init__(self, db: Session):
        super().__init__(db)

    def list(self, limit: int = 100, offset: int = 0) -> list[Email]:
        stmt = (
            select(Email)
            .options(joinedload(Email.contact).joinedload(Contact.company))
            .order_by(Email.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_campaign_contact(
        self, campaign_id: uuid.UUID, contact_id: uuid.UUID
    ) -> Email | None:
        stmt = select(Email).where(
            Email.campaign_id == campaign_id,
            Email.contact_id == contact_id,
        )
        return self.db.scalar(stmt)

    def create_for_contact(
        self,
        *,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        subject: str,
        body: str,
    ) -> Email:
        existing = self.get_by_campaign_contact(campaign_id, contact_id)
        if existing:
            existing.subject = subject
            existing.body = body
            self.db.flush()
            return existing
        return self.add(
            Email(
                campaign_id=campaign_id,
                contact_id=contact_id,
                subject=subject,
                body=body,
                status=EmailStatus.PENDING.value,
            )
        )

    def for_campaign(self, campaign_id: uuid.UUID) -> builtins.list[Email]:
        stmt = (
            select(Email)
            .options(joinedload(Email.contact).joinedload(Contact.company))
            .where(Email.campaign_id == campaign_id)
            .order_by(Email.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def pending_for_campaign(self, campaign_id: uuid.UUID) -> builtins.list[Email]:
        stmt = (
            select(Email)
            .options(joinedload(Email.contact).joinedload(Contact.company))
            .where(Email.campaign_id == campaign_id, Email.status == EmailStatus.PENDING.value)
            .order_by(Email.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def mark_sent(self, email: Email, provider_message_id: str | None) -> Email:
        email.status = EmailStatus.SENT.value
        email.provider_message_id = provider_message_id
        email.sent_at = datetime.now(UTC)
        email.error_message = None
        email.attempts += 1
        self.db.flush()
        return email

    def mark_failed(self, email: Email, error_message: str) -> Email:
        email.status = EmailStatus.FAILED.value
        email.error_message = error_message
        email.attempts += 1
        self.db.flush()
        return email

    def mark_bounced_by_message_id(self, provider_message_id: str) -> Email | None:
        email = self.db.scalar(
            select(Email).where(Email.provider_message_id == provider_message_id)
        )
        if email is None:
            return None
        email.status = EmailStatus.BOUNCED.value
        self.db.flush()
        return email
