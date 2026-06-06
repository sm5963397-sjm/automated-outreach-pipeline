from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    model = Company

    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_domain(self, domain: str) -> Company | None:
        return self.db.scalar(select(Company).where(Company.domain == domain))

    def upsert(self, *, name: str, domain: str, industry: str | None = None) -> Company:
        company = self.get_by_domain(domain)
        if company:
            company.name = name or company.name
            company.industry = industry or company.industry
            self.db.flush()
            return company
        return self.add(Company(name=name, domain=domain, industry=industry))

    def ids_for_domains(self, domains: list[str]) -> list[uuid.UUID]:
        stmt = select(Company.id).where(Company.domain.in_(domains))
        return list(self.db.scalars(stmt).all())
