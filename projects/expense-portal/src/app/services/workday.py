"""Workday API client for employee/hierarchy/cost center sync (FR-016).

This module provides the integration interface. The actual Workday API
endpoints and authentication will be configured per the integration
design with the HR / Workday Admin team.
"""

from dataclasses import dataclass

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class WorkdayEmployee:
    workday_id: str
    email: str
    full_name: str
    manager_workday_id: str | None
    cost_center_code: str | None


@dataclass
class WorkdayCostCenter:
    workday_id: str
    code: str
    name: str


async def fetch_employees() -> list[WorkdayEmployee]:
    """Fetch all active employees from the Workday REST API.

    The Workday integration team will provide the actual endpoint,
    authentication, and schema by Week 3 (assumption #3).
    """
    logger.info("workday_fetch_employees_start")
    # Integration stub — replace with actual Workday API call
    # async with httpx.AsyncClient() as client:
    #     response = await client.get(
    #         f"{workday_base_url}/employees",
    #         headers={"Authorization": f"Bearer {workday_token}"},
    #     )
    #     response.raise_for_status()
    #     data = response.json()
    logger.warning("workday_integration_stub", message="Using stub — replace with real API call")
    return []


async def fetch_cost_centers() -> list[WorkdayCostCenter]:
    """Fetch all active cost centers from Workday."""
    logger.info("workday_fetch_cost_centers_start")
    logger.warning("workday_integration_stub", message="Using stub — replace with real API call")
    return []
