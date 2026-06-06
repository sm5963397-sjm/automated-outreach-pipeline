from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.pagination import pagination
from app.api.dependencies.security import require_api_key
from app.database.session import get_db
from app.repositories import CompanyRepository
from app.schemas.company import CompanyRead

router = APIRouter(prefix="/companies", tags=["companies"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[CompanyRead])
def list_companies(
    db: Annotated[Session, Depends(get_db)],
    paging: Annotated[tuple[int, int], Depends(pagination)],
) -> list[Any]:
    limit, offset = paging
    return CompanyRepository(db).list(limit=limit, offset=offset)
