from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories import (
    CampaignRepository,
    CompanyRepository,
    ContactRepository,
    EmailRepository,
)


def test_company_contact_email_repository_round_trip(db_session: Session) -> None:
    companies = CompanyRepository(db_session)
    contacts = ContactRepository(db_session)
    campaigns = CampaignRepository(db_session)
    emails = EmailRepository(db_session)

    company = companies.upsert(name="Anthropic", domain="anthropic.com", industry="AI")
    same_company = companies.upsert(name="Anthropic Inc", domain="anthropic.com")
    assert same_company.id == company.id
    assert same_company.name == "Anthropic Inc"

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
        body="Hi Jane, short note.",
    )
    db_session.commit()

    assert companies.get_by_domain("anthropic.com") is not None
    assert contacts.get_by_linkedin("https://www.linkedin.com/in/jane-doe") is not None
    assert emails.get_by_campaign_contact(campaign.id, contact.id).id == email.id
