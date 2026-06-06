from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import Settings, get_secret_value
from app.core.errors import ConfigurationError, ExternalServiceError
from app.core.logging import get_logger
from app.services.dto import EmailDraft

logger = get_logger(__name__)


class EmailDraftSchema(BaseModel):
    subject: str = Field(..., min_length=3, max_length=90)
    body: str = Field(..., min_length=20, max_length=1400)


class AIEmailGenerator:
    def __init__(self, settings: Settings, client: object | None = None):
        self.settings = settings
        self._client: Any | None = client

    @property
    def client(self) -> Any:
        if self._client is None:
            api_key = get_secret_value(self.settings.OPENAI_API_KEY)
            if not api_key:
                raise ConfigurationError("OPENAI_API_KEY is required")
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)
        return self._client

    def generate(
        self,
        *,
        company_name: str,
        company_domain: str,
        contact_name: str,
        role: str,
    ) -> EmailDraft:
        prompt = self._build_prompt(
            company_name=company_name,
            company_domain=company_domain,
            contact_name=contact_name,
            role=role,
        )
        try:
            responses = self.client.responses
            if hasattr(responses, "parse"):
                response = responses.parse(
                    model=self.settings.OPENAI_MODEL,
                    input=prompt,
                    text_format=EmailDraftSchema,
                )
                parsed = response.output_parsed
            else:
                response = responses.create(
                    model=self.settings.OPENAI_MODEL,
                    input=prompt,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "cold_email",
                            "strict": True,
                            "schema": EmailDraftSchema.model_json_schema(),
                        }
                    },
                )
                parsed = EmailDraftSchema.model_validate_json(response.output_text)
        except Exception as exc:
            logger.error("ai_email_generation_failed", extra={"error": str(exc)})
            raise ExternalServiceError(f"AI email generation failed: {exc}") from exc

        if isinstance(parsed, EmailDraftSchema):
            draft = parsed
        elif isinstance(parsed, dict):
            draft = EmailDraftSchema.model_validate(parsed)
        else:
            draft = EmailDraftSchema.model_validate(json.loads(str(parsed)))
        return EmailDraft(subject=draft.subject.strip(), body=draft.body.strip())

    def _build_prompt(
        self,
        *,
        company_name: str,
        company_domain: str,
        contact_name: str,
        role: str,
    ) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You write concise B2B sales outreach emails. Return only the "
                    "requested structured fields. Be professional, specific to the "
                    "recipient's company and role, and avoid unsupported claims."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Product: {self.settings.OUTREACH_PRODUCT_NAME}\n"
                    f"Value proposition: {self.settings.OUTREACH_VALUE_PROP}\n"
                    f"Call to action: {self.settings.OUTREACH_CALL_TO_ACTION}\n\n"
                    f"Recipient company: {company_name}\n"
                    f"Company domain: {company_domain}\n"
                    f"Contact name: {contact_name}\n"
                    f"Role: {role}\n\n"
                    "Write a short personalized cold email. Requirements: subject "
                    "under 70 characters, body under 120 words, no fake metrics, "
                    "plain text, and include dynamic variables naturally."
                ),
            },
        ]
