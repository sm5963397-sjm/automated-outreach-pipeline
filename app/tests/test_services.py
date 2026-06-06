from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import CircuitBreakerOpenError
from app.services.eazyreach import EazyreachClient
from app.services.http import CircuitBreaker, RetryingHTTPClient
from app.services.prospeo import is_decision_maker_title


def test_retrying_http_client_retries_429_then_succeeds() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(200, json={"ok": True})

    settings = Settings(RETRY_BACKOFF_BASE_SECONDS=0, RETRY_MAX_RETRIES=3)
    client = RetryingHTTPClient(
        service_name="test",
        base_url="https://example.com",
        settings=settings,
        transport=httpx.MockTransport(handler),
    )

    assert client.request_json("GET", "/resource") == {"ok": True}
    assert calls["count"] == 2


def test_circuit_breaker_opens_after_threshold() -> None:
    breaker = CircuitBreaker("provider", failure_threshold=1, recovery_seconds=60)
    breaker.record_failure()
    with pytest.raises(CircuitBreakerOpenError):
        breaker.before_request()


def test_decision_maker_title_filter() -> None:
    assert is_decision_maker_title("VP Engineering")
    assert is_decision_maker_title("Co-Founder and CEO")
    assert not is_decision_maker_title("Account Executive")


def test_eazyreach_response_normalization() -> None:
    settings = Settings(EAZYREACH_API_KEY="test")
    client = EazyreachClient(settings)
    result = client._normalize_email_response(
        {"data": {"email": "FOO@example.com", "status": "deliverable"}}
    )
    assert result.verified is True
    assert result.email == "foo@example.com"
