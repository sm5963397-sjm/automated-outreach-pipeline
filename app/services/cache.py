from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisCache:
    """JSON Redis cache with graceful degradation when Redis is unavailable."""

    def __init__(self, redis_url: str, default_ttl_seconds: int):
        self.default_ttl_seconds = default_ttl_seconds
        self._client: Any | None = None
        try:
            from redis import Redis

            self._client = Redis.from_url(redis_url, decode_responses=True)
        except Exception as exc:  # pragma: no cover - import/runtime defensive path
            logger.warning("redis_cache_disabled", extra={"error": str(exc)})

    def get_json(self, key: str) -> Any | None:
        if self._client is None:
            return None
        try:
            value = self._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as exc:
            logger.warning("redis_cache_get_failed", extra={"cache_key": key, "error": str(exc)})
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        if self._client is None:
            return
        try:
            self._client.setex(
                key,
                ttl_seconds or self.default_ttl_seconds,
                json.dumps(value, default=str),
            )
        except Exception as exc:
            logger.warning("redis_cache_set_failed", extra={"cache_key": key, "error": str(exc)})
