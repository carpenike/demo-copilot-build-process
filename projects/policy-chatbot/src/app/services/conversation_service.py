"""Conversation service for managing chat sessions and message history.

Handles conversation lifecycle, message persistence in PostgreSQL, and
conversation context caching in Redis for follow-up question support (FR-009).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Conversation, Message

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.config import Settings

logger = structlog.get_logger()


class ConversationService:
    """Manages conversation lifecycle and context caching."""

    def __init__(self, settings: Settings, redis: Redis) -> None:
        self._settings = settings
        self._redis = redis

    async def get_or_create_conversation(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID | None,
        user_entra_id: str,
        user_display_name: str,
        channel: str,
    ) -> Conversation:
        """Resume an existing conversation or start a new one."""
        if conversation_id:
            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_entra_id == user_entra_id,
                )
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                conversation.last_activity_at = datetime.now(UTC)
                await db.flush()
                return conversation

        conversation = Conversation(
            user_entra_id=user_entra_id,
            user_display_name=user_display_name,
            channel=channel,
        )
        db.add(conversation)
        await db.flush()
        logger.info("conversation_created", conversation_id=str(conversation.id))
        return conversation

    async def save_message(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        citations: list[dict[str, str]] | None = None,
        checklist: dict[str, Any] | None = None,
        intent_domain: str | None = None,
        intent_type: str | None = None,
        confidence_score: float | None = None,
        escalated: bool = False,
    ) -> Message:
        """Persist a message to the database."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations,
            checklist=checklist,
            intent_domain=intent_domain,
            intent_type=intent_type,
            confidence_score=confidence_score,
            escalated=escalated,
        )
        db.add(message)

        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_activity_at=datetime.now(UTC))
        )

        await db.flush()
        return message

    async def mark_escalated(self, db: AsyncSession, conversation_id: uuid.UUID) -> None:
        """Mark a conversation as escalated to a live agent."""
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(status="escalated", last_activity_at=datetime.now(UTC))
        )
        await db.flush()

    async def get_conversation_context(self, conversation_id: uuid.UUID) -> list[dict[str, str]]:
        """Retrieve cached conversation context from Redis for follow-up questions."""
        cache_key = f"conv_context:{conversation_id}"
        data = await self._redis.get(cache_key)
        if data:
            return json.loads(data)  # type: ignore[no-any-return]
        return []

    async def update_conversation_context(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
    ) -> None:
        """Append a message to the cached conversation context in Redis.

        Keeps a sliding window of messages with a TTL for session expiration.
        """
        cache_key = f"conv_context:{conversation_id}"
        context = await self.get_conversation_context(conversation_id)
        context.append({"role": role, "content": content})

        # Keep only the last 10 messages for context window
        context = context[-10:]

        await self._redis.set(
            cache_key,
            json.dumps(context),
            ex=self._settings.redis_session_ttl_seconds,
        )

    async def get_low_confidence_count(self, conversation_id: uuid.UUID) -> int:
        """Get the count of consecutive low-confidence answers from Redis cache."""
        cache_key = f"low_conf_count:{conversation_id}"
        count = await self._redis.get(cache_key)
        return int(count) if count else 0

    async def increment_low_confidence_count(self, conversation_id: uuid.UUID) -> int:
        """Increment and return the low-confidence counter."""
        cache_key = f"low_conf_count:{conversation_id}"
        new_count = await self._redis.incr(cache_key)
        await self._redis.expire(cache_key, self._settings.redis_session_ttl_seconds)
        return int(new_count)

    async def reset_low_confidence_count(self, conversation_id: uuid.UUID) -> None:
        """Reset the low-confidence counter when a good answer is given."""
        cache_key = f"low_conf_count:{conversation_id}"
        await self._redis.delete(cache_key)

    async def get_transcript(
        self, db: AsyncSession, conversation_id: uuid.UUID
    ) -> list[dict[str, str]]:
        """Get the full conversation transcript for escalation handoff."""
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()

        return [{"role": msg.role, "content": msg.content} for msg in messages]
