from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.pagination import pagination
from app.api.dependencies.security import require_api_key
from app.database.session import get_db
from app.repositories import EmailRepository
from app.schemas.email import BrevoWebhookEvent, EmailRead

router = APIRouter(tags=["emails"], dependencies=[Depends(require_api_key)])


@router.get("/emails", response_model=list[EmailRead])
def list_emails(
    db: Annotated[Session, Depends(get_db)],
    paging: Annotated[tuple[int, int], Depends(pagination)],
) -> list[Any]:
    limit, offset = paging
    return EmailRepository(db).list(limit=limit, offset=offset)


@router.post("/webhooks/brevo", status_code=status.HTTP_202_ACCEPTED)
def brevo_webhook(
    payload: BrevoWebhookEvent,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    event = payload.event.lower()
    message_id = payload.normalized_message_id
    if event not in {"hard_bounce", "soft_bounce", "blocked", "invalid_email"}:
        return {"status": "ignored"}
    if not message_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing message id")
    email = EmailRepository(db).mark_bounced_by_message_id(message_id)
    if email is None:
        return {"status": "not_found"}
    db.commit()
    return {"status": "updated"}
