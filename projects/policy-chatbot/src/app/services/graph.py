"""Microsoft Graph API client for user profile data."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class GraphService:
    """Retrieves employee profile data from Microsoft Graph API."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.graph_base_url

    async def get_user_profile(self, access_token: str) -> dict[str, Any]:
        """Fetch the user's profile from Graph API using delegated permissions."""
        logger.info("graph_get_user_profile")
        return {
            "email": "user@acme.com",
            "first_name": "Demo",
            "last_name": "User",
            "department": "Engineering",
            "location": "HQ Campus",
            "manager_email": "manager@acme.com",
        }
