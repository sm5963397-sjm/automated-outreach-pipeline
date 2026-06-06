from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.pagination import pagination
from app.api.dependencies.security import require_api_key
from app.database.session import get_db
from app.repositories import ContactRepository
from app.schemas.contact import ContactRead

router = APIRouter(prefix="/contacts", tags=["contacts"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[ContactRead])
def list_contacts(
    db: Annotated[Session, Depends(get_db)],
    paging: Annotated[tuple[int, int], Depends(pagination)],
) -> list[Any]:
    limit, offset = paging
    return ContactRepository(db).list(limit=limit, offset=offset)
