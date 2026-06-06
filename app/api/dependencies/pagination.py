from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from app.core.config import Settings, get_settings


def pagination(
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = Query(default=100, ge=1),
    offset: int = Query(default=0, ge=0),
) -> tuple[int, int]:
    return min(limit, settings.MAX_PAGE_LIMIT), offset
