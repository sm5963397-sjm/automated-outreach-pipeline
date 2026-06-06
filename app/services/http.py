from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import CircuitBreakerOpenError, ExternalServiceError, RateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    service_name: str
    failure_threshold: int
    recovery_seconds: int
    failure_count: int = 0
    opened_at: float | None = None
    state: CircuitState = CircuitState.CLOSED

    def before_request(self) -> None:
        if self.state != CircuitState.OPEN:
            return
        if self.opened_at is None:
            raise CircuitBreakerOpenError(f"{self.service_name} circuit breaker is open")
        if time.monotonic() - self.opened_at >= self.recovery_seconds:
            self.state = CircuitState.HALF_OPEN
            return
        raise CircuitBreakerOpenError(f"{self.service_name} circuit breaker is open")

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()
            logger.error(
                "circuit_breaker_opened",
                extra={"service": self.service_name, "failures": self.failure_count},
            )


class RetryingHTTPClient:
    """HTTP client with 3 retries, exponential backoff, 429 handling, and circuit breaking."""

    retryable_statuses = {429, 500, 502, 503, 504}

    def __init__(
        self,
        *,
        service_name: str,
        base_url: str,
        settings: Settings,
        default_headers: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.service_name = service_name
        self.base_url = base_url.rstrip("/")
        self.settings = settings
        self.default_headers = default_headers or {}
        self.circuit_breaker = CircuitBreaker(
            service_name=service_name,
            failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_seconds=settings.CIRCUIT_BREAKER_RECOVERY_SECONDS,
        )
        self.client = httpx.Client(
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            transport=transport,
        )

    def request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        request_headers = {**self.default_headers, **(headers or {})}
        last_error: Exception | None = None

        for attempt in range(self.settings.RETRY_MAX_RETRIES + 1):
            self.circuit_breaker.before_request()
            started = time.perf_counter()
            try:
                response = self.client.request(
                    method,
                    url,
                    json=json_body,
                    params=params,
                    headers=request_headers,
                )
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                logger.info(
                    "external_api_call",
                    extra={
                        "service": self.service_name,
                        "method": method.upper(),
                        "path": path,
                        "status_code": response.status_code,
                        "attempt": attempt + 1,
                        "elapsed_ms": elapsed_ms,
                    },
                )
                if response.status_code in self.retryable_statuses:
                    if attempt < self.settings.RETRY_MAX_RETRIES:
                        self._sleep_before_retry(response, attempt)
                        continue
                    self.circuit_breaker.record_failure()
                    if response.status_code == 429:
                        raise RateLimitError(f"{self.service_name} rate limited after retries")
                    raise ExternalServiceError(
                        f"{self.service_name} returned {response.status_code}: "
                        f"{response.text[:500]}"
                    )
                if response.status_code >= 400:
                    self.circuit_breaker.record_failure()
                    raise ExternalServiceError(
                        f"{self.service_name} returned {response.status_code}: "
                        f"{response.text[:500]}"
                    )
                self.circuit_breaker.record_success()
                if not response.content:
                    return {}
                return response.json()
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_error = exc
                logger.warning(
                    "external_api_request_error",
                    extra={
                        "service": self.service_name,
                        "path": path,
                        "attempt": attempt + 1,
                        "error": str(exc),
                    },
                )
                if attempt < self.settings.RETRY_MAX_RETRIES:
                    self._sleep_before_retry(None, attempt)
                    continue
                self.circuit_breaker.record_failure()
                raise ExternalServiceError(f"{self.service_name} request failed: {exc}") from exc

        raise ExternalServiceError(f"{self.service_name} request failed: {last_error}")

    def _sleep_before_retry(self, response: httpx.Response | None, attempt: int) -> None:
        retry_after = response.headers.get("Retry-After") if response is not None else None
        if retry_after and retry_after.isdigit():
            delay = float(retry_after)
        else:
            delay = self.settings.retry_delays[min(attempt, len(self.settings.retry_delays) - 1)]
        logger.warning(
            "external_api_retry",
            extra={
                "service": self.service_name,
                "attempt": attempt + 1,
                "retry_in_seconds": delay,
            },
        )
        if delay > 0:
            time.sleep(delay)
