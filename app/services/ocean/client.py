from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_secret_value
from app.core.errors import ConfigurationError
from app.core.security import normalize_domain
from app.services.cache import RedisCache
from app.services.dto import CompanyLead
from app.services.http import RetryingHTTPClient


class OceanClient:
    def __init__(
        self,
        settings: Settings,
        cache: RedisCache | None = None,
        http_client: RetryingHTTPClient | None = None,
    ):
        self.settings = settings
        self.cache = cache
        api_key = get_secret_value(settings.OCEAN_API_KEY)
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-Api-Token"] = api_key
        self.http = http_client or RetryingHTTPClient(
            service_name="ocean",
            base_url=settings.OCEAN_BASE_URL,
            settings=settings,
            default_headers=headers,
        )

    def find_similar_companies(self, domain: str, limit: int | None = None) -> list[CompanyLead]:
        api_key = get_secret_value(self.settings.OCEAN_API_KEY)
        if not api_key and self.http.default_headers.get("X-Api-Token") is None:
            raise ConfigurationError("OCEAN_API_KEY is required")

        normalized_domain = normalize_domain(domain)
        size = limit or self.settings.OCEAN_COMPANY_LIMIT
        cache_key = f"ocean:similar:{normalized_domain}:{size}"
        if self.cache:
            cached = self.cache.get_json(cache_key)
            if cached is not None:
                return [CompanyLead(**item) for item in cached]

        payload = {
            "size": size,
            "companiesFilters": {
                "lookalikeDomains": [normalized_domain],
                "excludeDomains": [normalized_domain],
            },
            "fields": ["name", "legalName", "domain", "industries", "industryCategories"],
        }
        data = self.http.request_json("POST", "/search/companies", json_body=payload)
        companies = self._normalize_companies(data)
        if self.cache:
            self.cache.set_json(cache_key, [company.__dict__ for company in companies])
        return companies

    def _normalize_companies(self, data: dict[str, Any]) -> list[CompanyLead]:
        seen: set[str] = set()
        normalized: list[CompanyLead] = []
        for item in data.get("companies", []):
            company = item.get("company", item) if isinstance(item, dict) else {}
            domain = company.get("domain")
            if not domain:
                continue
            try:
                domain = normalize_domain(domain)
            except Exception:
                continue
            if domain in seen:
                continue
            seen.add(domain)
            industries = company.get("industries") or company.get("industryCategories") or []
            industry = industries[0] if isinstance(industries, list) and industries else None
            name = company.get("name") or company.get("legalName") or domain
            normalized.append(CompanyLead(name=name, domain=domain, industry=industry))
        return normalized
