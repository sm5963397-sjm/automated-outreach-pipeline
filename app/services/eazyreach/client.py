from __future__ import annotations

import re
from typing import Any

from app.core.config import Settings, get_secret_value
from app.core.errors import ConfigurationError
from app.services.cache import RedisCache
from app.services.dto import EmailLookupResult
from app.services.http import RetryingHTTPClient

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EazyreachClient:
    def __init__(
        self,
        settings: Settings,
        cache: RedisCache | None = None,
        http_client: RetryingHTTPClient | None = None,
    ):
        self.settings = settings
        self.cache = cache
        api_key = get_secret_value(settings.EAZYREACH_API_KEY)
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["x-api-key"] = api_key
        self.http = http_client or RetryingHTTPClient(
            service_name="eazyreach",
            base_url=settings.EAZYREACH_BASE_URL,
            settings=settings,
            default_headers=headers,
        )

    def find_verified_email(
        self,
        *,
        linkedin_url: str | None,
        contact_name: str,
        company_domain: str,
    ) -> EmailLookupResult:
        api_key = get_secret_value(self.settings.EAZYREACH_API_KEY)
        if not api_key and "Authorization" not in self.http.default_headers:
            raise ConfigurationError("EAZYREACH_API_KEY is required")
        if not linkedin_url:
            return EmailLookupResult(email=None, verified=False)

        cache_key = f"eazyreach:email:{linkedin_url}"
        if self.cache:
            cached = self.cache.get_json(cache_key)
            if cached is not None:
                return EmailLookupResult(**cached)

        payload = {
            "linkedin_url": linkedin_url,
            "name": contact_name,
            "company_domain": company_domain,
        }
        data = self.http.request_json(
            "POST",
            self.settings.EAZYREACH_EMAIL_LOOKUP_PATH,
            json_body=payload,
        )
        result = self._normalize_email_response(data)
        if self.cache:
            self.cache.set_json(cache_key, result.__dict__)
        return result

    def _normalize_email_response(self, data: Any) -> EmailLookupResult:
        candidate = self._find_email_object(data)
        if not candidate:
            return EmailLookupResult(email=None, verified=False)
        email = str(candidate.get("email") or "").strip().lower()
        if not EMAIL_RE.match(email):
            return EmailLookupResult(email=None, verified=False)
        verified_value = candidate.get("verified")
        status = str(candidate.get("status") or candidate.get("verification_status") or "").lower()
        verified = verified_value is True or status in {"verified", "valid", "deliverable"}
        return EmailLookupResult(email=email, verified=verified)

    def _find_email_object(self, value: Any) -> dict[str, Any] | None:
        if isinstance(value, dict):
            if value.get("email"):
                return value
            for key in ("result", "data", "contact", "profile", "lead"):
                nested = self._find_email_object(value.get(key))
                if nested:
                    return nested
            emails = value.get("emails")
            if isinstance(emails, list):
                for item in emails:
                    nested = self._find_email_object(item)
                    if nested:
                        return nested
        elif isinstance(value, list):
            for item in value:
                nested = self._find_email_object(item)
                if nested:
                    return nested
        return None
