from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enums import CampaignStatus, EmailStatus
from app.repositories import CampaignRepository, EmailRepository
from app.services.dto import (
    CompanyLead,
    DecisionMaker,
    EmailDraft,
    EmailLookupResult,
    EmailSendResult,
)
from app.workflows import OutreachPipelineWorkflow


class FakeOcean:
    def find_similar_companies(self, domain: str) -> list[CompanyLead]:
        return [CompanyLead(name="Anthropic", domain="anthropic.com", industry="AI")]


class FakeProspeo:
    def find_decision_makers(self, company_domain: str) -> list[DecisionMaker]:
        return [
            DecisionMaker(
                name="Jane Doe",
                title="CTO",
                linkedin_url="https://www.linkedin.com/in/jane-doe",
            )
        ]


class FakeEazyreach:
    def find_verified_email(
        self,
        *,
        linkedin_url: str | None,
        contact_name: str,
        company_domain: str,
    ) -> EmailLookupResult:
        return EmailLookupResult(email="jane@anthropic.com", verified=True)


class FakeAI:
    def generate(
        self,
        *,
        company_name: str,
        company_domain: str,
        contact_name: str,
        role: str,
    ) -> EmailDraft:
        return EmailDraft(
            subject=f"Quick idea for {company_name}",
            body=f"Hi {contact_name}, noticed your work as {role}. Open to a quick chat?",
        )


class FakeBrevo:
    def send_email(
        self,
        *,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        params: dict,
    ) -> EmailSendResult:
        return EmailSendResult(message_id="brevo-message-1")


def test_pipeline_prepare_and_send(db_session: Session) -> None:
    campaign = CampaignRepository(db_session).create("openai.com")
    db_session.commit()
    workflow = OutreachPipelineWorkflow(
        db=db_session,
        ocean=FakeOcean(),
        prospeo=FakeProspeo(),
        eazyreach=FakeEazyreach(),
        ai=FakeAI(),
        brevo=FakeBrevo(),
    )

    summary = workflow.prepare_campaign(campaign.id, "openai.com")
    assert summary.companies_found == 1
    assert summary.contacts_found == 1
    assert summary.verified_emails == 1
    assert summary.emails_generated == 1
    assert campaign.status == CampaignStatus.AWAITING_APPROVAL.value

    final_summary = workflow.send_campaign(campaign.id)
    emails = EmailRepository(db_session).for_campaign(campaign.id)
    assert final_summary.emails_sent == 1
    assert emails[0].status == EmailStatus.SENT.value
    assert campaign.status == CampaignStatus.SENT.value
