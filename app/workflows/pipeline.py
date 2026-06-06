from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import normalize_domain
from app.models.campaign import Campaign
from app.models.email import Email
from app.models.enums import CampaignStatus, EmailStatus
from app.repositories import (
    CampaignRepository,
    CompanyRepository,
    ContactRepository,
    EmailRepository,
)
from app.schemas.campaign import PipelineSummary
from app.services.ai import AIEmailGenerator
from app.services.brevo import BrevoClient
from app.services.dto import CompanyLead, DecisionMaker
from app.services.eazyreach import EazyreachClient
from app.services.ocean import OceanClient
from app.services.prospeo import ProspeoClient

logger = get_logger(__name__)


class OutreachPipelineWorkflow:
    def __init__(
        self,
        *,
        db: Session,
        ocean: OceanClient,
        prospeo: ProspeoClient,
        eazyreach: EazyreachClient,
        ai: AIEmailGenerator,
        brevo: BrevoClient,
    ):
        self.db = db
        self.campaigns = CampaignRepository(db)
        self.companies = CompanyRepository(db)
        self.contacts = ContactRepository(db)
        self.emails = EmailRepository(db)
        self.ocean = ocean
        self.prospeo = prospeo
        self.eazyreach = eazyreach
        self.ai = ai
        self.brevo = brevo

    def run(
        self, campaign_id: uuid.UUID, domain: str, *, auto_send: bool = False
    ) -> PipelineSummary:
        summary = self.prepare_campaign(campaign_id, domain)
        if auto_send:
            summary = self.send_campaign(campaign_id)
        return summary

    def prepare_campaign(self, campaign_id: uuid.UUID, domain: str) -> PipelineSummary:
        normalized_domain = normalize_domain(domain)
        campaign = self.campaigns.require(campaign_id)
        summary = PipelineSummary()
        self.campaigns.update_status(
            campaign,
            CampaignStatus.DISCOVERING,
            summary=summary.model_dump(),
            error_message=None,
        )
        self.db.commit()

        logger.info(
            "pipeline_discovery_started",
            extra={"campaign_id": str(campaign_id), "domain": normalized_domain},
        )
        try:
            company_leads = self.ocean.find_similar_companies(normalized_domain)
            summary.companies_found = len(company_leads)
            for company_lead in company_leads:
                self._process_company(campaign, company_lead, summary)
            self.campaigns.update_status(
                campaign,
                CampaignStatus.AWAITING_APPROVAL,
                summary=summary.model_dump(),
                error_message=None,
            )
            self.db.commit()
            logger.info(
                "pipeline_discovery_completed",
                extra={"campaign_id": str(campaign_id), "summary": summary.model_dump()},
            )
            return summary
        except Exception as exc:
            self.db.rollback()
            campaign = self.campaigns.require(campaign_id)
            self.campaigns.update_status(
                campaign,
                CampaignStatus.FAILED,
                summary=summary.model_dump(),
                error_message=str(exc),
            )
            self.db.commit()
            logger.exception(
                "pipeline_discovery_failed",
                extra={"campaign_id": str(campaign_id), "error": str(exc)},
            )
            raise

    def send_campaign(self, campaign_id: uuid.UUID) -> PipelineSummary:
        campaign = self.campaigns.require(campaign_id)
        self.campaigns.update_status(campaign, CampaignStatus.SENDING, error_message=None)
        self.db.commit()

        logger.info("campaign_send_started", extra={"campaign_id": str(campaign_id)})
        for email in self.emails.pending_for_campaign(campaign_id):
            self._send_single_email(email)
            self.db.commit()

        campaign = self.campaigns.require(campaign_id)
        summary = self._summarize_campaign(campaign)
        status = self._final_campaign_status(self.emails.for_campaign(campaign_id))
        self.campaigns.update_status(campaign, status, summary=summary.model_dump())
        self.db.commit()
        logger.info(
            "campaign_send_completed",
            extra={
                "campaign_id": str(campaign_id),
                "status": status.value,
                "summary": summary.model_dump(),
            },
        )
        return summary

    def _process_company(
        self, campaign: Campaign, company_lead: CompanyLead, summary: PipelineSummary
    ) -> None:
        company = self.companies.upsert(
            name=company_lead.name,
            domain=company_lead.domain,
            industry=company_lead.industry,
        )
        self.db.commit()

        try:
            decision_makers = self.prospeo.find_decision_makers(company.domain)
        except Exception as exc:
            logger.exception(
                "prospeo_company_lookup_failed",
                extra={"company_domain": company.domain, "error": str(exc)},
            )
            return

        summary.contacts_found += len(decision_makers)
        for decision_maker in decision_makers:
            self._process_contact(
                campaign, company.id, company.name, company.domain, decision_maker, summary
            )
        campaign.summary = summary.model_dump()
        self.db.commit()

    def _process_contact(
        self,
        campaign: Campaign,
        company_id: uuid.UUID,
        company_name: str,
        company_domain: str,
        decision_maker: DecisionMaker,
        summary: PipelineSummary,
    ) -> None:
        contact = self.contacts.upsert_decision_maker(
            company_id=company_id,
            name=decision_maker.name,
            title=decision_maker.title,
            linkedin_url=decision_maker.linkedin_url,
        )
        self.db.commit()

        try:
            lookup = self.eazyreach.find_verified_email(
                linkedin_url=decision_maker.linkedin_url,
                contact_name=decision_maker.name,
                company_domain=company_domain,
            )
        except Exception as exc:
            logger.exception(
                "eazyreach_email_lookup_failed",
                extra={"contact_id": str(contact.id), "error": str(exc)},
            )
            return
        if not lookup.verified or not lookup.email:
            return

        self.contacts.set_verified_email(contact.id, lookup.email, verified=True)
        summary.verified_emails += 1

        try:
            draft = self.ai.generate(
                company_name=company_name,
                company_domain=company_domain,
                contact_name=decision_maker.name,
                role=decision_maker.title,
            )
        except Exception as exc:
            logger.exception(
                "email_draft_generation_failed",
                extra={"contact_id": str(contact.id), "error": str(exc)},
            )
            return

        self.emails.create_for_contact(
            campaign_id=campaign.id,
            contact_id=contact.id,
            subject=draft.subject,
            body=draft.body,
        )
        summary.emails_generated += 1
        campaign.summary = summary.model_dump()
        self.db.commit()

    def _send_single_email(self, email: Email) -> None:
        contact = email.contact
        if contact.email is None:
            self.emails.mark_failed(email, "contact has no verified email")
            return

        params = {
            "company_name": contact.company.name,
            "company_domain": contact.company.domain,
            "contact_name": contact.name,
            "role": contact.title,
        }
        try:
            result = self.brevo.send_email(
                to_email=contact.email,
                to_name=contact.name,
                subject=email.subject,
                body=email.body,
                params=params,
            )
            self.emails.mark_sent(email, result.message_id)
            logger.info(
                "email_sent",
                extra={
                    "email_id": str(email.id),
                    "contact_id": str(contact.id),
                    "provider_message_id": result.message_id,
                },
            )
        except Exception as exc:
            self.emails.mark_failed(email, str(exc))
            logger.exception(
                "email_send_failed",
                extra={"email_id": str(email.id), "error": str(exc)},
            )

    def _summarize_campaign(self, campaign: Campaign) -> PipelineSummary:
        summary_data = PipelineSummary().model_dump()
        summary_data.update(campaign.summary or {})
        for email in self.emails.for_campaign(campaign.id):
            if email.status == EmailStatus.SENT.value:
                summary_data["emails_sent"] += 1
            elif email.status == EmailStatus.FAILED.value:
                summary_data["emails_failed"] += 1
            elif email.status == EmailStatus.BOUNCED.value:
                summary_data["emails_bounced"] += 1
        return PipelineSummary.model_validate(summary_data)

    def _final_campaign_status(self, emails: Iterable[Email]) -> CampaignStatus:
        statuses = [email.status for email in emails]
        if not statuses:
            return CampaignStatus.FAILED
        if all(status == EmailStatus.SENT.value for status in statuses):
            return CampaignStatus.SENT
        if any(status == EmailStatus.SENT.value for status in statuses):
            return CampaignStatus.PARTIAL_FAILURE
        return CampaignStatus.FAILED
