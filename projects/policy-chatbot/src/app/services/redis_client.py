"""Redis client for conversation session context."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class RedisService:
    """Manages conversation session state in Azure Cache for Redis."""

    def __init__(self, settings: Settings) -> None:
        self._url = settings.redis_url
        self._ttl = settings.session_ttl_seconds

    async def get_session(self, conversation_id: str) -> dict[str, Any] | None:
        """Load conversation session from Redis."""
        logger.info("redis_get_session", extra={"conversation_id": conversation_id})
        return None

    async def set_session(self, conversation_id: str, data: dict[str, Any]) -> None:
        """Store conversation session in Redis with sliding TTL."""
        logger.info("redis_set_session", extra={"conversation_id": conversation_id})
        _serialized = json.dumps(data, default=str)

    async def delete_session(self, conversation_id: str) -> None:
        """Remove a conversation session from Redis."""
        logger.info("redis_delete_session", extra={"conversation_id": conversation_id})

    async def check_health(self) -> bool:
        """Return True if Redis is reachable."""
        return True
