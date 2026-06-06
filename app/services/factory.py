from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.ai import AIEmailGenerator
from app.services.brevo import BrevoClient
from app.services.cache import RedisCache
from app.services.eazyreach import EazyreachClient
from app.services.ocean import OceanClient
from app.services.prospeo import ProspeoClient
from app.workflows import OutreachPipelineWorkflow


def build_workflow(db: Session) -> OutreachPipelineWorkflow:
    settings = get_settings()
    cache = RedisCache(settings.REDIS_URL, settings.CACHE_TTL_SECONDS)
    return OutreachPipelineWorkflow(
        db=db,
        ocean=OceanClient(settings, cache=cache),
        prospeo=ProspeoClient(settings, cache=cache),
        eazyreach=EazyreachClient(settings, cache=cache),
        ai=AIEmailGenerator(settings),
        brevo=BrevoClient(settings),
    )
