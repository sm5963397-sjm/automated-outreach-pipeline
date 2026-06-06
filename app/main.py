from __future__ import annotations

from fastapi import FastAPI

from app.api.middleware.request_context import RequestContextMiddleware
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Automated outbound discovery, email generation, and campaign sending pipeline.",
)
app.add_middleware(RequestContextMiddleware)
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
