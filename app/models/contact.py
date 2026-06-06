from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.email import Email


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("company_id", "name", "title", name="uq_contacts_company_name_title"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    linkedin_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, unique=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company: Mapped[Company] = relationship("Company", back_populates="contacts")
    emails: Mapped[list[Email]] = relationship(
        "Email", back_populates="contact", cascade="all, delete-orphan"
    )
