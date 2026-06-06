from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.services.ai.email_generator import AIEmailGenerator, EmailDraftSchema
from app.services.brevo import BrevoClient
from app.services.cache import RedisCache
from app.services.eazyreach import EazyreachClient
from app.services.ocean import OceanClient
from app.services.prospeo import ProspeoClient


class StubHTTP:
    def __init__(self, response: Any, default_headers: dict[str, str] | None = None):
        self.response = response
        self.default_headers = default_headers or {
            "api-key": "test",
            "X-KEY": "test",
            "X-Api-Token": "test",
        }
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "json_body": json_body,
                "params": params,
                "headers": headers,
            }
        )
        return self.response


def test_ocean_client_normalizes_companies() -> None:
    settings = Settings(OCEAN_API_KEY="test")
    http = StubHTTP(
        {
            "companies": [
                {
                    "company": {
                        "name": "Anthropic",
                        "domain": "https://anthropic.com",
                        "industries": ["AI"],
                    }
                },
                {"company": {"name": "Duplicate", "domain": "anthropic.com"}},
                {"company": {"name": "Bad", "domain": "not-a-domain"}},
            ]
        }
    )
    companies = OceanClient(settings, http_client=http).find_similar_companies(
        "openai.com", limit=5
    )

    assert len(companies) == 1
    assert companies[0].domain == "anthropic.com"
    assert http.calls[0]["json_body"]["size"] == 5


def test_prospeo_client_filters_decision_makers() -> None:
    settings = Settings(PROSPEO_API_KEY="test", PROSPEO_PAGE_LIMIT=1)
    http = StubHTTP(
        {
            "results": [
                {
                    "person": {
                        "full_name": "Jane Doe",
                        "current_job_title": "CTO",
                        "linkedin_url": "li1",
                    }
                },
                {
                    "person": {
                        "full_name": "Bob Rep",
                        "current_job_title": "Account Executive",
                        "linkedin_url": "li2",
                    }
                },
            ],
            "pagination": {"total_page": 1},
        }
    )
    people = ProspeoClient(settings, http_client=http).find_decision_makers("anthropic.com")

    assert len(people) == 1
    assert people[0].title == "CTO"
    assert http.calls[0]["path"] == "/search-person"


def test_eazyreach_client_handles_lookup_and_missing_linkedin() -> None:
    settings = Settings(EAZYREACH_API_KEY="test")
    http = StubHTTP({"data": {"email": "Jane@Anthropic.com", "verified": True}})
    client = EazyreachClient(settings, http_client=http)

    missing = client.find_verified_email(
        linkedin_url=None,
        contact_name="Jane Doe",
        company_domain="anthropic.com",
    )
    found = client.find_verified_email(
        linkedin_url="https://www.linkedin.com/in/jane-doe",
        contact_name="Jane Doe",
        company_domain="anthropic.com",
    )

    assert missing.verified is False
    assert found.email == "jane@anthropic.com"
    assert http.calls[0]["path"] == settings.EAZYREACH_EMAIL_LOOKUP_PATH


def test_brevo_client_sends_transactional_email() -> None:
    settings = Settings(BREVO_API_KEY="test", BREVO_REPLY_TO_EMAIL="reply@example.com")
    http = StubHTTP({"messageId": "message-1"})
    result = BrevoClient(settings, http_client=http).send_email(
        to_email="jane@anthropic.com",
        to_name="Jane Doe",
        subject="Quick idea",
        body="Hi Jane.",
        params={"company_name": "Anthropic"},
    )

    payload = http.calls[0]["json_body"]
    assert result.message_id == "message-1"
    assert payload["replyTo"]["email"] == "reply@example.com"
    assert payload["to"][0]["email"] == "jane@anthropic.com"


class FakeParsedResponses:
    def parse(self, **kwargs):
        return type(
            "ParsedResponse",
            (),
            {"output_parsed": EmailDraftSchema(subject="Quick idea", body="Hi Jane, short note.")},
        )()


class FakeOpenAIClient:
    responses = FakeParsedResponses()


def test_ai_email_generator_with_injected_client() -> None:
    settings = Settings(OPENAI_API_KEY="test")
    draft = AIEmailGenerator(settings, client=FakeOpenAIClient()).generate(
        company_name="Anthropic",
        company_domain="anthropic.com",
        contact_name="Jane Doe",
        role="CTO",
    )

    assert draft.subject == "Quick idea"
    assert "Jane" in draft.body


def test_redis_cache_no_client_paths() -> None:
    cache = RedisCache("redis://localhost:1/0", default_ttl_seconds=1)
    cache._client = None

    assert cache.get_json("missing") is None
    cache.set_json("key", {"value": 1})
