from __future__ import annotations

import re
from urllib.parse import urlparse

from app.core.errors import AppError

DOMAIN_RE = re.compile(r"^(?!-)(?:[a-z0-9-]{1,63}\.)+[a-z]{2,63}$")


class InvalidDomainError(AppError, ValueError):
    """Raised when user input is not a valid company domain."""


def normalize_domain(value: str) -> str:
    domain = value.strip().lower()
    if not domain:
        raise InvalidDomainError("domain is required")
    if "://" not in domain:
        domain = f"https://{domain}"
    parsed = urlparse(domain)
    host = parsed.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    if not DOMAIN_RE.match(host):
        raise InvalidDomainError("domain must be a valid hostname, for example openai.com")
    return host
