"""Redis client wrapper for session state, conversation context, and caching."""

import json
import logging

import redis.asyncio as redis

from app.config import Settings

logger = logging.getLogger(__name__)


class RedisService:
    """Wraps Azure Cache for Redis for session/cache/rate-limit operations."""

    def __init__(self, settings: Settings) -> None:
        self._redis: redis.Redis[str] = redis.from_url(  # type: ignore[assignment]
            settings.redis_url,
            decode_responses=True,
        )
        self._session_ttl = settings.session_cache_ttl_seconds
        self._conversation_ttl = settings.conversation_ttl_days * 86400

    async def set_user_session(
        self,
        user_id: str,
        profile: dict[str, str],
    ) -> None:
        """Cache user profile data from Graph API."""
        key = f"session:{user_id}"
        await self._redis.hset(key, mapping=profile)
        await self._redis.expire(key, self._session_ttl)

    async def get_user_session(self, user_id: str) -> dict[str, str] | None:
        """Retrieve cached user profile."""
        key = f"session:{user_id}"
        data = await self._redis.hgetall(key)
        return data if data else None

    async def add_conversation_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        """Append a message to the conversation context window in Redis."""
        key = f"conv:{conversation_id}"
        message = json.dumps({"role": role, "content": content})
        await self._redis.rpush(key, message)
        await self._redis.expire(key, self._conversation_ttl)

    async def get_conversation_history(
        self,
        conversation_id: str,
        max_messages: int = 10,
    ) -> list[dict[str, str]]:
        """Retrieve the most recent messages for conversation context."""
        key = f"conv:{conversation_id}"
        raw_messages = await self._redis.lrange(key, -max_messages, -1)
        return [json.loads(m) for m in raw_messages]

    async def set_conversation_meta(
        self,
        conversation_id: str,
        metadata: dict[str, str],
    ) -> None:
        """Store conversation metadata (status, channel, intent)."""
        key = f"conv:{conversation_id}:meta"
        await self._redis.hset(key, mapping=metadata)
        await self._redis.expire(key, self._conversation_ttl)

    async def get_cached_response(self, query_hash: str) -> str | None:
        """Check for a cached response for an identical query."""
        key = f"cache:query:{query_hash}"
        result: str | None = await self._redis.get(key)  # type: ignore[assignment]
        return result

    async def set_cached_response(
        self,
        query_hash: str,
        response_json: str,
        ttl: int = 3600,
    ) -> None:
        """Cache a response for identical queries (1-hour default TTL)."""
        key = f"cache:query:{query_hash}"
        await self._redis.set(key, response_json, ex=ttl)

    async def check_rate_limit(
        self,
        user_id: str,
        max_requests: int = 30,
        window_seconds: int = 60,
    ) -> bool:
        """Token bucket rate limiter — returns True if request is allowed."""
        key = f"rate:{user_id}"
        current = await self._redis.incr(key)
        if current == 1:
            await self._redis.expire(key, window_seconds)
        return current <= max_requests

    async def is_available(self) -> bool:
        """Check if Redis is reachable."""
        try:
            await self._redis.ping()  # type: ignore[misc]
        except Exception:
            logger.warning("Redis is unavailable")
            return False
        else:
            return True

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._redis.aclose()
