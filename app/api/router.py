from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import campaigns, companies, contacts, emails, pipeline

api_router = APIRouter()
api_router.include_router(pipeline.router)
api_router.include_router(companies.router)
api_router.include_router(contacts.router)
api_router.include_router(campaigns.router)
api_router.include_router(emails.router)
