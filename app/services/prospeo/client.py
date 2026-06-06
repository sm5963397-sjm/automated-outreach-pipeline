from __future__ import annotations

import re
from typing import Any

from app.core.config import Settings, get_secret_value
from app.core.errors import ConfigurationError
from app.core.security import normalize_domain
from app.services.cache import RedisCache
from app.services.dto import DecisionMaker
from app.services.http import RetryingHTTPClient

DECISION_MAKER_TITLES = [
    "Founder",
    "Co-Founder",
    "CEO",
    "Chief Executive Officer",
    "CTO",
    "Chief Technology Officer",
    "VP Engineering",
    "Vice President of Engineering",
    "Head of Engineering",
    "Director of Engineering",
]

TITLE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bfounder\b",
        r"\bco[- ]?founder\b",
        r"\bceo\b",
        r"\bchief executive officer\b",
        r"\bcto\b",
        r"\bchief technology officer\b",
        r"\bvp engineering\b",
        r"\bvice president of engineering\b",
        r"\bhead of engineering\b",
        r"\bdirector of engineering\b",
    ]
]


def is_decision_maker_title(title: str | None) -> bool:
    if not title:
        return False
    return any(pattern.search(title) for pattern in TITLE_PATTERNS)


class ProspeoClient:
    def __init__(
        self,
        settings: Settings,
        cache: RedisCache | None = None,
        http_client: RetryingHTTPClient | None = None,
    ):
        self.settings = settings
        self.cache = cache
        api_key = get_secret_value(settings.PROSPEO_API_KEY)
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-KEY"] = api_key
        self.http = http_client or RetryingHTTPClient(
            service_name="prospeo",
            base_url=settings.PROSPEO_BASE_URL,
            settings=settings,
            default_headers=headers,
        )

    def find_decision_makers(self, company_domain: str) -> list[DecisionMaker]:
        api_key = get_secret_value(self.settings.PROSPEO_API_KEY)
        if not api_key and self.http.default_headers.get("X-KEY") is None:
            raise ConfigurationError("PROSPEO_API_KEY is required")

        domain = normalize_domain(company_domain)
        cache_key = f"prospeo:decision-makers:{domain}:{self.settings.PROSPEO_PAGE_LIMIT}"
        if self.cache:
            cached = self.cache.get_json(cache_key)
            if cached is not None:
                return [DecisionMaker(**item) for item in cached]

        decision_makers: list[DecisionMaker] = []
        for page in range(1, self.settings.PROSPEO_PAGE_LIMIT + 1):
            payload = {
                "page": page,
                "filters": {
                    "company": {"websites": {"include": [domain]}},
                    "person_job_title": {"include": DECISION_MAKER_TITLES},
                },
            }
            data = self.http.request_json("POST", "/search-person", json_body=payload)
            decision_makers.extend(self._normalize_people(data))
            pagination = data.get("pagination") or {}
            total_pages = int(pagination.get("total_page") or page)
            if page >= total_pages:
                break

        unique = self._dedupe(decision_makers)
        if self.cache:
            self.cache.set_json(cache_key, [person.__dict__ for person in unique])
        return unique

    def _normalize_people(self, data: dict[str, Any]) -> list[DecisionMaker]:
        people: list[DecisionMaker] = []
        for row in data.get("results", []):
            person = row.get("person", row) if isinstance(row, dict) else {}
            name = person.get("full_name") or " ".join(
                part for part in [person.get("first_name"), person.get("last_name")] if part
            )
            title = (
                person.get("current_job_title")
                or person.get("headline")
                or self._title_from_job_history(person)
            )
            linkedin_url = person.get("linkedin_url")
            if name and is_decision_maker_title(title):
                people.append(
                    DecisionMaker(
                        name=str(name),
                        title=str(title),
                        linkedin_url=linkedin_url,
                    )
                )
        return people

    def _title_from_job_history(self, person: dict[str, Any]) -> str | None:
        for job in person.get("job_history") or []:
            if job.get("current") and job.get("title"):
                return str(job["title"])
        return None

    def _dedupe(self, people: list[DecisionMaker]) -> list[DecisionMaker]:
        seen: set[tuple[str | None, str, str]] = set()
        unique: list[DecisionMaker] = []
        for person in people:
            key = (person.linkedin_url, person.name.lower(), person.title.lower())
            if key not in seen:
                seen.add(key)
                unique.append(person)
        return unique
