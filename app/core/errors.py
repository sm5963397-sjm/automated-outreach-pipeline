from __future__ import annotations


class AppError(Exception):
    """Base application exception."""


class ConfigurationError(AppError):
    """Raised when required runtime configuration is missing."""


class ExternalServiceError(AppError):
    """Raised when an external provider returns an unrecoverable error."""


class RateLimitError(ExternalServiceError):
    """Raised when a provider keeps rate limiting after retries."""


class CircuitBreakerOpenError(ExternalServiceError):
    """Raised when the circuit breaker is open for a provider."""


class WorkflowError(AppError):
    """Raised for pipeline orchestration failures."""
