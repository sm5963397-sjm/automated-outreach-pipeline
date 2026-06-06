from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_secret_value
from app.core.errors import ConfigurationError
from app.services.dto import EmailSendResult
from app.services.http import RetryingHTTPClient


class BrevoClient:
    def __init__(
        self,
        settings: Settings,
        http_client: RetryingHTTPClient | None = None,
    ):
        self.settings = settings
        api_key = get_secret_value(settings.BREVO_API_KEY)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if api_key:
            headers["api-key"] = api_key
        self.http = http_client or RetryingHTTPClient(
            service_name="brevo",
            base_url=settings.BREVO_BASE_URL,
            settings=settings,
            default_headers=headers,
        )

    def send_email(
        self,
        *,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        params: dict[str, Any] | None = None,
    ) -> EmailSendResult:
        api_key = get_secret_value(self.settings.BREVO_API_KEY)
        if not api_key and "api-key" not in self.http.default_headers:
            raise ConfigurationError("BREVO_API_KEY is required")
        payload: dict[str, Any] = {
            "sender": {
                "name": self.settings.BREVO_SENDER_NAME,
                "email": self.settings.BREVO_SENDER_EMAIL,
            },
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "textContent": body,
            "params": params or {},
        }
        if self.settings.BREVO_REPLY_TO_EMAIL:
            payload["replyTo"] = {"email": self.settings.BREVO_REPLY_TO_EMAIL}
        data = self.http.request_json("POST", "/smtp/email", json_body=payload)
        return EmailSendResult(message_id=data.get("messageId") or data.get("message_id"))
