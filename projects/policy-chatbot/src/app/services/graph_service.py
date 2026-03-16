"""Microsoft Graph API client for employee profile data (FR-011)."""

import logging

import httpx
from azure.identity import DefaultAzureCredential

from app.config import Settings

logger = logging.getLogger(__name__)


class GraphService:
    """Wraps Microsoft Graph API to retrieve employee directory info."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.graph_api_base_url.rstrip("/")
        self._credential = DefaultAzureCredential()

    async def get_user_profile(self, user_id: str) -> dict[str, str]:
        """Retrieve display name, department, and office location for a user.

        Falls back to defaults if Graph API is unreachable — the chatbot should
        still function without personalization.
        """
        token = self._credential.get_token("https://graph.microsoft.com/.default")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self._base_url}/users/{user_id}",
                    params={"$select": "displayName,department,officeLocation,jobTitle"},
                    headers={"Authorization": f"Bearer {token.token}"},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            logger.warning(
                "Failed to fetch user profile from Graph API",
                extra={"user_id": user_id},
            )
            return {
                "display_name": "there",
                "department": "",
                "location": "",
                "role": "Employee",
            }

        return {
            "display_name": data.get("displayName", "there"),
            "department": data.get("department", ""),
            "location": data.get("officeLocation", ""),
            "role": "Employee",
        }
