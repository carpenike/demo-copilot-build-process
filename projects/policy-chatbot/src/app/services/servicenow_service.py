"""ServiceNow ITSM client for escalation handoff and ticket creation."""

import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class ServiceNowService:
    """Wraps ServiceNow REST API for conversation escalation (FR-026)."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.servicenow_instance_url.rstrip("/")
        self._auth = (settings.servicenow_api_user, settings.servicenow_api_password)

    async def create_escalation_ticket(
        self,
        *,
        target_team: str,
        transcript_summary: str,
        identified_intent: str,
        user_display_name: str,
        user_email: str,
    ) -> str:
        """Create a ServiceNow incident for an escalated conversation.

        Returns the ServiceNow ticket number (e.g., 'INC0012345').
        """
        payload = {
            "short_description": f"Policy Chatbot Escalation — {identified_intent}",
            "description": (
                f"Employee: {user_display_name} ({user_email})\n"
                f"Target Team: {target_team}\n"
                f"Intent: {identified_intent}\n\n"
                f"Conversation Summary:\n{transcript_summary}"
            ),
            "assignment_group": self._resolve_assignment_group(target_team),
            "category": "inquiry",
            "urgency": "3",
            "impact": "3",
        }

        async with httpx.AsyncClient(auth=self._auth, timeout=30.0) as client:
            response = await client.post(
                f"{self._base_url}/api/now/table/incident",
                json=payload,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            result = response.json()

        ticket_number: str = result["result"]["number"]
        logger.info(
            "ServiceNow escalation ticket created",
            extra={"ticket_number": ticket_number, "target_team": target_team},
        )
        return ticket_number

    def _resolve_assignment_group(self, target_team: str) -> str:
        """Map the target team to a ServiceNow assignment group name."""
        group_map = {
            "hr": "HR Service Desk",
            "it": "IT Service Desk",
            "facilities": "Facilities Management",
        }
        return group_map.get(target_team.lower(), "HR Service Desk")
