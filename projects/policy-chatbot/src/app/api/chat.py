"""Chat API endpoints.

POST /api/v1/chat                           — send message, get RAG response
POST /api/v1/chat/{conversation_id}/escalate — escalate to live agent
POST /api/v1/chat/{conversation_id}/feedback — submit feedback
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import (
    ConvServiceDep,
    CurrentUserDep,
    DbDep,
    FeedbackServiceDep,
    LLMDep,
    SearchDep,
    SettingsDep,
)
from app.core import rag_pipeline
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    EscalateRequest,
    EscalationInfo,
    EscalationResponse,
    FeedbackRating,
    FeedbackRequest,
    FeedbackResponse,
    ProblemDetail,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    responses={
        400: {"model": ProblemDetail},
        401: {"model": ProblemDetail},
        429: {"model": ProblemDetail},
    },
)
async def chat(
    body: ChatRequest,
    user: CurrentUserDep,
    db: DbDep,
    settings: SettingsDep,
    conv_service: ConvServiceDep,
    llm_service: LLMDep,
    search_service: SearchDep,
    feedback_service: FeedbackServiceDep,
) -> ChatResponse:
    """Send a message and receive a chatbot response."""
    user_id = str(user.get("sub") or user.get("oid") or "unknown")
    user_name = str(user.get("name") or user.get("preferred_username") or "User")

    conversation = await conv_service.get_or_create_conversation(
        db,
        conversation_id=body.conversation_id,
        user_entra_id=user_id,
        user_display_name=user_name,
        channel="webchat",
    )

    # Save the user message
    await conv_service.save_message(
        db, conversation_id=conversation.id, role="user", content=body.message
    )

    # Get conversation context for follow-up question support
    context = await conv_service.get_conversation_context(conversation.id)

    # Run the RAG pipeline
    result = await rag_pipeline.run_pipeline(
        query=body.message,
        llm_service=llm_service,
        search_service=search_service,
        conversation_context=context,
        confidence_threshold=settings.rag_confidence_threshold,
        top_k=settings.rag_top_k,
    )

    # Check for auto-escalation after consecutive low-confidence answers
    if result.should_escalate and result.escalation_reason == "low_confidence":
        count = await conv_service.increment_low_confidence_count(conversation.id)
        if count >= settings.rag_max_escalation_attempts:
            result.response_body.escalated = True
            result.response_body.content += (
                "\n\nI'm having difficulty finding a confident answer. "
                "Would you like me to connect you with a support team member?"
            )
    elif not result.should_escalate:
        await conv_service.reset_low_confidence_count(conversation.id)

    # Save the assistant message
    citations_raw = [c.model_dump() for c in result.response_body.citations]
    checklist_raw = (
        result.response_body.checklist.model_dump() if result.response_body.checklist else None
    )

    assistant_msg = await conv_service.save_message(
        db,
        conversation_id=conversation.id,
        role="assistant",
        content=result.response_body.content,
        citations=citations_raw,
        checklist=checklist_raw,
        intent_domain=result.intent.domain,
        intent_type=result.intent.intent_type,
        confidence_score=result.response_body.confidence,
        escalated=result.response_body.escalated,
    )

    # Update conversation context cache
    await conv_service.update_conversation_context(conversation.id, "user", body.message)
    await conv_service.update_conversation_context(
        conversation.id, "assistant", result.response_body.content
    )

    # Record analytics event
    await feedback_service.record_analytics_event(
        db,
        event_type="query",
        conversation_id=conversation.id,
        intent_domain=result.intent.domain,
        metadata={"intent_type": result.intent.intent_type},
    )

    await db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
        response=result.response_body,
    )


@router.post(
    "/{conversation_id}/escalate",
    response_model=EscalationResponse,
    responses={404: {"model": ProblemDetail}},
)
async def escalate(
    conversation_id: uuid.UUID,
    body: EscalateRequest,
    user: CurrentUserDep,
    db: DbDep,
    conv_service: ConvServiceDep,
    feedback_service: FeedbackServiceDep,
) -> EscalationResponse:
    """Explicitly escalate a conversation to a live service desk agent."""
    transcript = await conv_service.get_transcript(db, conversation_id)
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or not owned by this user",
        )

    # In production, this would call the ServiceNow API to create an incident
    incident_id = f"INC-2026-{uuid.uuid4().hex[:4].upper()}"

    await conv_service.mark_escalated(db, conversation_id)

    await conv_service.save_message(
        db,
        conversation_id=conversation_id,
        role="system",
        content=f"Conversation escalated to live agent. Incident: {incident_id}",
        escalated=True,
    )

    await feedback_service.record_analytics_event(
        db,
        event_type="escalation",
        conversation_id=conversation_id,
        metadata={"reason": body.reason or "user_requested", "incident_id": incident_id},
    )

    await db.commit()

    logger.info(
        "conversation_escalated",
        conversation_id=str(conversation_id),
        incident_id=incident_id,
    )

    return EscalationResponse(
        conversation_id=conversation_id,
        escalation=EscalationInfo(
            reason=body.reason or "user_requested",
            servicenow_incident_id=incident_id,
        ),
    )


@router.post(
    "/{conversation_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ProblemDetail},
        404: {"model": ProblemDetail},
        409: {"model": ProblemDetail},
    },
)
async def feedback(
    conversation_id: uuid.UUID,
    body: FeedbackRequest,
    user: CurrentUserDep,
    db: DbDep,
    feedback_service: FeedbackServiceDep,
) -> FeedbackResponse:
    """Submit feedback on a specific assistant message."""
    user_id = str(user.get("sub") or user.get("oid") or "unknown")

    try:
        fb = await feedback_service.submit_feedback(
            db,
            conversation_id=conversation_id,
            message_id=body.message_id,
            rating=body.rating.value,
            comment=body.comment,
            user_entra_id=user_id,
        )
    except ValueError as e:
        error_msg = str(e)
        if "already submitted" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        ) from e

    return FeedbackResponse(
        feedback_id=fb.id,
        message_id=fb.message_id,
        rating=FeedbackRating(fb.rating),
        comment=fb.comment,
    )
