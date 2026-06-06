from __future__ import annotations

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies.security import require_api_key
from app.api.routes import pipeline as pipeline_routes
from app.core.config import Settings
from app.models.enums import CampaignStatus, EmailStatus
from app.repositories import (
    CampaignRepository,
    CompanyRepository,
    ContactRepository,
    EmailRepository,
)


def test_health_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_approve_send_endpoint_queues_task(
    api_client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    campaign = CampaignRepository(db_session).create("openai.com")
    campaign.status = CampaignStatus.AWAITING_APPROVAL.value
    db_session.commit()
    queued: dict[str, tuple] = {}

    def fake_delay(*args, **kwargs):
        queued["args"] = args
        queued["kwargs"] = kwargs

    monkeypatch.setattr(pipeline_routes.send_campaign_task, "delay", fake_delay)
    response = api_client.post(f"/api/v1/pipeline/{campaign.id}/send")

    assert response.status_code == 202
    assert queued["args"] == (str(campaign.id),)


def test_approve_send_rejects_pending_campaign(api_client: TestClient, db_session: Session) -> None:
    campaign = CampaignRepository(db_session).create("openai.com")
    db_session.commit()

    response = api_client.post(f"/api/v1/pipeline/{campaign.id}/send")

    assert response.status_code == 409


def test_brevo_webhook_marks_email_bounced(api_client: TestClient, db_session: Session) -> None:
    companies = CompanyRepository(db_session)
    contacts = ContactRepository(db_session)
    campaigns = CampaignRepository(db_session)
    emails = EmailRepository(db_session)

    company = companies.upsert(name="Anthropic", domain="anthropic.com")
    contact = contacts.upsert_decision_maker(
        company_id=company.id,
        name="Jane Doe",
        title="CTO",
        linkedin_url="https://www.linkedin.com/in/jane-doe",
    )
    contacts.set_verified_email(contact.id, "jane@anthropic.com")
    campaign = campaigns.create("openai.com")
    email = emails.create_for_contact(
        campaign_id=campaign.id,
        contact_id=contact.id,
        subject="Quick idea",
        body="Hi Jane.",
    )
    email.provider_message_id = "message-1"
    email.status = EmailStatus.SENT.value
    db_session.commit()

    response = api_client.post(
        "/api/v1/webhooks/brevo",
        json={"event": "hard_bounce", "message-id": "message-1"},
    )

    assert response.status_code == 202
    assert email.status == EmailStatus.BOUNCED.value


def test_require_api_key_rejects_invalid_key() -> None:
    try:
        require_api_key(Settings(APP_API_KEY="secret"), x_api_key="wrong")
    except HTTPException as exc:
        assert exc.status_code == 401
    else:  # pragma: no cover
        raise AssertionError("expected HTTPException")
