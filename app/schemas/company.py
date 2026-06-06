from __future__ import annotations

import uuid
from datetime import datetime

from app.schemas.base import ORMModel


class CompanyRead(ORMModel):
    id: uuid.UUID
    name: str
    domain: str
    industry: str | None = None
    created_at: datetime
