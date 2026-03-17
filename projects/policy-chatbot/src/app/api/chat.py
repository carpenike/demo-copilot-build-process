"""Chat API endpoints — conversation management, messaging, escalation, feedback."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    AuthenticatedUser,
    get_current_user,
    get_db,
    get_graph_service,
    get_rag_pipeline,
    get_redis,
    get_servicenow_service,
)
from app.core.rag_pipeline import RAGPipeline
from app.models.conversation import Citation, Conversation, Message
from app.models.escalation import Escalation
from app.models.feedback import Feedback, FeedbackFlag
from app.services.graph_service import GraphService
from app.services.redis_service import RedisService
from app.services.servicenow_service import ServiceNowService

router = APIRouter(prefix="/v1/chat", tags=["chat"])


# --- Request/Response schemas ---


class CreateConversationRequest(BaseModel):
    channel: str = Field(pattern=r"^(web|teams)$")


class CreateConversationResponse(BaseModel):
    conversation_id: str
    greeting: str
    user_context: dict[str, str]
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class EscalateRequest(BaseModel):
    target_team: str = Field(pattern=r"^(hr|it|facilities)$")


class EscalateResponse(BaseModel):
    escalation_id: str
    servicenow_ticket_id: str
    message: str
    created_at: datetime


class FeedbackRequest(BaseModel):
    rating: str = Field(pattern=r"^(positive|negative)$")
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    feedback_id: str
    created_at: datetime


# --- Endpoints ---


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: CreateConversationRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_service: Annotated[RedisService, Depends(get_redis)],
    graph_service: Annotated[GraphService, Depends(get_graph_service)],
) -> CreateConversationResponse:
    """Start a new conversation session (FR-007, FR-009, FR-011)."""
    # Get or cache user profile from Graph API
    profile = await redis_service.get_user_session(user.user_id)
    if not profile:
        profile = await graph_service.get_user_profile(user.user_id)
        await redis_service.set_user_session(user.user_id, profile)

    display_name = profile.get("display_name", "there")

    # Create conversation record
    now = datetime.now(tz=UTC)
    conversation = Conversation(
        user_id=user.user_id,
        channel=body.channel,
        status="active",
        started_at=now,
        last_activity_at=now,
        expires_at=now + timedelta(days=90),
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    # Initialize Redis conversation context
    await redis_service.set_conversation_meta(
        str(conversation.id),
        {"status": "active", "channel": body.channel, "user_id": user.user_id},
    )

    return CreateConversationResponse(
        conversation_id=str(conversation.id),
        greeting=f"Hi {display_name}! I'm the Policy Assistant. How can I help you today?",
        user_context={
            "display_name": display_name,
            "department": profile.get("department", ""),
            "location": profile.get("location", ""),
        },
        created_at=conversation.started_at,
    )


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_service: Annotated[RedisService, Depends(get_redis)],
    rag_pipeline: Annotated[RAGPipeline, Depends(get_rag_pipeline)],
) -> dict:  # type: ignore[type-arg]
    """Send a message and receive the chatbot's response (FR-007 to FR-021)."""
    # Verify conversation ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Rate limiting
    allowed = await redis_service.check_rate_limit(user.user_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before sending another message.",
        )

    # Store user message
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=body.content,
    )
    db.add(user_message)

    # Add to Redis conversation context
    await redis_service.add_conversation_message(str(conversation_id), "user", body.content)

    # Run RAG pipeline
    rag_result = await rag_pipeline.process_query(str(conversation_id), body.content)

    # Store assistant response
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=rag_result.get("content", ""),
        metadata_=rag_result,
    )
    db.add(assistant_message)

    # Store citations if present
    for citation_data in rag_result.get("citations", []):
        citation = Citation(
            message_id=assistant_message.id,
            document_id=None,  # type: ignore[arg-type]
            section_heading=citation_data.get("section", ""),
            source_url=citation_data.get("source_url", ""),
        )
        db.add(citation)

    # Update conversation activity timestamp
    conversation.last_activity_at = datetime.now(tz=UTC)

    await db.commit()
    await db.refresh(assistant_message)

    # Add assistant response to Redis context
    await redis_service.add_conversation_message(
        str(conversation_id), "assistant", rag_result.get("content", "")
    )

    return {
        "message_id": str(assistant_message.id),
        "role": "assistant",
        **rag_result,
        "created_at": assistant_message.created_at.isoformat(),
    }


@router.post(
    "/conversations/{conversation_id}/escalate",
    status_code=status.HTTP_201_CREATED,
)
async def escalate_conversation(
    conversation_id: uuid.UUID,
    body: EscalateRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_service: Annotated[RedisService, Depends(get_redis)],
    servicenow_service: Annotated[ServiceNowService, Depends(get_servicenow_service)],
    graph_service: Annotated[GraphService, Depends(get_graph_service)],
) -> EscalateResponse:
    """Escalate conversation to a live service desk agent (FR-025, FR-026)."""
    # Verify conversation ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Get conversation history for transcript
    history = await redis_service.get_conversation_history(str(conversation_id))
    transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)

    # Get user profile for escalation context
    profile = await redis_service.get_user_session(user.user_id)
    if not profile:
        profile = await graph_service.get_user_profile(user.user_id)

    # Create ServiceNow ticket (FR-026)
    ticket_id = await servicenow_service.create_escalation_ticket(
        target_team=body.target_team,
        transcript_summary=transcript,
        identified_intent="escalation_request",
        user_display_name=profile.get("display_name", user.name),
        user_email=user.user_id,
    )

    # Record escalation
    escalation = Escalation(
        conversation_id=conversation_id,
        user_id=user.user_id,
        target_team=body.target_team,
        servicenow_ticket_id=ticket_id,
        transcript_summary=transcript,
        identified_intent="escalation_request",
    )
    db.add(escalation)

    # Update conversation status
    conversation.status = "escalated"
    await db.commit()
    await db.refresh(escalation)

    team_name = {"hr": "HR", "it": "IT", "facilities": "Facilities"}.get(
        body.target_team, body.target_team
    )

    return EscalateResponse(
        escalation_id=str(escalation.id),
        servicenow_ticket_id=ticket_id,
        message=(
            f"I've connected you with the {team_name} support team. A representative "
            "will follow up shortly. Your conversation history has been shared so you "
            "don't need to repeat yourself."
        ),
        created_at=escalation.created_at,
    )


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/feedback",
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    body: FeedbackRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackResponse:
    """Submit feedback on a chatbot response (FR-028)."""
    # Verify the message belongs to the user's conversation
    result = await db.execute(
        select(Message)
        .join(Conversation)
        .where(
            Message.id == message_id,
            Conversation.id == conversation_id,
            Conversation.user_id == user.user_id,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    feedback = Feedback(
        message_id=message_id,
        user_id=user.user_id,
        rating=body.rating,
        comment=body.comment,
    )
    db.add(feedback)

    # Check if this topic needs flagging (FR-030)
    if body.rating == "negative":
        intent = (message.metadata_ or {}).get("intent", "unknown")
        flag_result = await db.execute(select(FeedbackFlag).where(FeedbackFlag.topic == intent))
        existing_flag = flag_result.scalar_one_or_none()

        if existing_flag:
            existing_flag.negative_count += 1
            if existing_flag.negative_count > 3 and existing_flag.status != "flagged":
                existing_flag.status = "flagged"
        else:
            new_flag = FeedbackFlag(
                topic=intent,
                negative_count=1,
                status="reviewed",
            )
            db.add(new_flag)

    await db.commit()
    await db.refresh(feedback)

    return FeedbackResponse(
        feedback_id=str(feedback.id),
        created_at=feedback.created_at,
    )
