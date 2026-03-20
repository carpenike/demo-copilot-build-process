"""Feedback endpoint — POST /v1/feedback."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.chat import _ensure_user, _get_db
from app.core.auth import CurrentUser, get_current_user
from app.models.database import Feedback as FeedbackModel
from app.models.database import Message
from app.models.schemas import FeedbackRequest, FeedbackResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    body: FeedbackRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Submit thumbs-up/thumbs-down feedback on a chatbot response."""
    user = await _ensure_user(db, current_user)

    # Verify the message exists
    msg_result = await db.execute(select(Message).where(Message.id == body.message_id))
    message = msg_result.scalar_one_or_none()
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    # Check for duplicate feedback
    existing = await db.execute(
        select(FeedbackModel).where(FeedbackModel.message_id == body.message_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback already submitted for this message",
        )

    feedback = FeedbackModel(
        message_id=body.message_id,
        user_id=user.id,
        rating=body.rating,
        comment=body.comment,
    )
    db.add(feedback)
    await db.flush()

    return FeedbackResponse(
        id=feedback.id,
        message_id=feedback.message_id,
        rating=feedback.rating,
        comment=feedback.comment,
        created_at=feedback.created_at,
    )
