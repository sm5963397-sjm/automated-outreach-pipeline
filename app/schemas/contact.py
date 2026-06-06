from __future__ import annotations

import uuid
from datetime import datetime

from app.schemas.base import ORMModel
from app.schemas.company import CompanyRead


class ContactRead(ORMModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    title: str
    linkedin_url: str | None = None
    email: str | None = None
    verified: bool
    created_at: datetime
    company: CompanyRead | None = None
