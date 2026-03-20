"""Chat, escalation, conversation history, and user profile endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.rag import DISCLAIMER, orchestrate_chat
from app.models.database import Conversation, Message, User
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatResponseBody,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    EscalateRequest,
    EscalateResponse,
    EscalationResult,
    MessageItem,
    UserProfileResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["chat"])


async def _get_db(request: Request) -> Any:
    """Yield a DB session from app state."""
    async with request.app.state.db_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _ensure_user(
    db: AsyncSession,
    current_user: CurrentUser,
) -> User:
    """Get or create the User record for the authenticated user."""
    result = await db.execute(select(User).where(User.email == current_user.email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=current_user.email,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            role="Admin" if current_user.is_admin else "Employee",
        )
        db.add(user)
        await db.flush()
    return user


# ---------------------------------------------------------------------------
# POST /v1/chat
# ---------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Send a message and receive a policy-grounded response."""
    user = await _ensure_user(db, current_user)

    # Resolve or create conversation
    if body.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == body.conversation_id,
                Conversation.user_id == user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
    else:
        conversation = Conversation(user_id=user.id)
        db.add(conversation)
        await db.flush()

    # Persist user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)

    # Run RAG pipeline
    rag_result = await orchestrate_chat(
        message=body.message,
        conversation_id=str(conversation.id),
        user_id=str(user.id),
        user_email=user.email,
        search_service=request.app.state.search_service,
        openai_service=request.app.state.openai_service,
        redis_service=request.app.state.redis_service,
    )

    # Persist assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=rag_result.get("content", ""),
        citations=rag_result.get("citations"),
        intent=rag_result.get("intent"),
        response_type=rag_result.get("response_type"),
        checklist=rag_result.get("checklist"),
        wayfinding=rag_result.get("wayfinding"),
    )
    db.add(assistant_msg)

    # Update conversation counters
    conversation.message_count = (conversation.message_count or 0) + 2
    conversation.last_message_at = datetime.now(UTC)
    await db.flush()

    # Update Redis session
    await request.app.state.redis_service.set_session(
        str(conversation.id),
        {
            "user_id": str(user.id),
            "user_email": user.email,
            "messages": [{"role": "user", "content": body.message}],
        },
    )

    response_body = ChatResponseBody(
        type=rag_result.get("response_type", "answer"),
        content=rag_result.get("content", ""),
        citations=rag_result.get("citations", []),
        disclaimer=DISCLAIMER,
        intent=rag_result.get("intent"),
        checklist=rag_result.get("checklist"),
        wayfinding=rag_result.get("wayfinding"),
        suggested_escalation=rag_result.get("suggested_escalation"),
        escalation=rag_result.get("escalation"),
        search_results=rag_result.get("search_results"),
    )

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
        response=response_body,
    )


# ---------------------------------------------------------------------------
# POST /v1/chat/escalate
# ---------------------------------------------------------------------------
@router.post("/chat/escalate", response_model=EscalateResponse)
async def escalate(
    body: EscalateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Initiate a handoff to a live service desk agent."""
    user = await _ensure_user(db, current_user)

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == body.conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    # Create ServiceNow ticket
    ticket_id = await request.app.state.servicenow_client.create_incident(
        conversation_id=str(conversation.id),
        transcript="[conversation transcript]",
        intent="escalation_requested",
        user_email=user.email,
    )

    conversation.status = "escalated"
    conversation.escalation_ticket_id = ticket_id

    return EscalateResponse(
        conversation_id=conversation.id,
        escalation=EscalationResult(
            status="initiated",
            ticket_id=ticket_id,
            team="HR Service Desk",
            message=(
                "I've created a support ticket and shared our conversation with the "
                "service desk. A team member will reach out shortly."
            ),
        ),
    )


# ---------------------------------------------------------------------------
# GET /v1/conversations
# ---------------------------------------------------------------------------
@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    request: Request,
    cursor: str | None = None,
    limit: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """List the current user's recent conversations."""
    user = await _ensure_user(db, current_user)
    limit = min(limit, 100)

    query = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .limit(limit + 1)
    )

    if cursor:
        try:
            cursor_id = uuid.UUID(cursor)
            query = query.where(Conversation.id < cursor_id)
        except ValueError:
            pass

    result = await db.execute(query)
    convos = list(result.scalars().all())
    has_more = len(convos) > limit
    if has_more:
        convos = convos[:limit]

    data = []
    for c in convos:
        # Fetch first user message as preview
        msg_result = await db.execute(
            select(Message.content)
            .where(Message.conversation_id == c.id, Message.role == "user")
            .order_by(Message.created_at.asc())
            .limit(1)
        )
        preview = msg_result.scalar_one_or_none()
        data.append(
            ConversationSummary(
                id=c.id,
                started_at=c.started_at,
                last_message_at=c.last_message_at,
                message_count=c.message_count,
                preview=preview,
            )
        )

    return ConversationListResponse(
        data=data,
        next_cursor=str(convos[-1].id) if has_more else None,
    )


# ---------------------------------------------------------------------------
# GET /v1/conversations/{conversation_id}
# ---------------------------------------------------------------------------
@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Retrieve full conversation history."""
    user = await _ensure_user(db, current_user)

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conversation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return ConversationDetailResponse(
        id=conversation.id,
        started_at=conversation.started_at,
        messages=[
            MessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                citations=m.citations,
                timestamp=m.created_at,
            )
            for m in messages
        ],
    )


# ---------------------------------------------------------------------------
# GET /v1/me
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Retrieve the authenticated user's profile for personalization."""
    user = await _ensure_user(db, current_user)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        department=user.department,
        location=user.location,
        role=user.role,
        manager=user.manager_email,
    )
