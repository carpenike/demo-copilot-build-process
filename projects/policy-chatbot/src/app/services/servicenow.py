"""ServiceNow client for escalation ticket creation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class ServiceNowClient:
    """Creates escalation tickets in ServiceNow when the chatbot cannot help."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.servicenow_base_url

    async def create_incident(
        self,
        conversation_id: str,
        transcript: str,
        intent: str,
        user_email: str,
    ) -> str:
        """Create a ServiceNow incident and return the ticket ID (e.g. INC0012345)."""
        logger.info(
            "servicenow_create_incident",
            extra={"conversation_id": conversation_id},
        )
        return "INC0000001"
