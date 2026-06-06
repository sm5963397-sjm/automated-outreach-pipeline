from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.contact import Contact
from app.repositories.base import BaseRepository


class ContactRepository(BaseRepository[Contact]):
    model = Contact

    def __init__(self, db: Session):
        super().__init__(db)

    def list(self, limit: int = 100, offset: int = 0) -> list[Contact]:
        stmt = (
            select(Contact)
            .options(joinedload(Contact.company))
            .order_by(Contact.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_linkedin(self, linkedin_url: str) -> Contact | None:
        return self.db.scalar(select(Contact).where(Contact.linkedin_url == linkedin_url))

    def upsert_decision_maker(
        self,
        *,
        company_id: uuid.UUID,
        name: str,
        title: str,
        linkedin_url: str | None,
    ) -> Contact:
        contact = self.get_by_linkedin(linkedin_url) if linkedin_url else None
        if contact is None:
            stmt = select(Contact).where(
                Contact.company_id == company_id,
                Contact.name == name,
                Contact.title == title,
            )
            contact = self.db.scalar(stmt)
        if contact:
            contact.linkedin_url = linkedin_url or contact.linkedin_url
            contact.title = title or contact.title
            self.db.flush()
            return contact
        return self.add(
            Contact(
                company_id=company_id,
                name=name,
                title=title,
                linkedin_url=linkedin_url,
            )
        )

    def set_verified_email(
        self, contact_id: uuid.UUID, email: str, verified: bool = True
    ) -> Contact:
        contact = self.get(contact_id)
        if contact is None:
            raise ValueError(f"contact not found: {contact_id}")
        contact.email = email
        contact.verified = verified
        self.db.flush()
        return contact
