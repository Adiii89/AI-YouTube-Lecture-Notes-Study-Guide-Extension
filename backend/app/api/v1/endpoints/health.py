from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Application health status")
    project_name: str = Field(..., description="Name of the application")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Runtime environment")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    services: Dict[str, str] = Field(
        default_factory=lambda: {"api": "up"},
        description="Individual service component statuses"
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health Check",
    description="Returns the operational status, version, and environment of the API backend."
)
async def check_health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat(),
        services={
            "api": "up",
            "cors": "configured"
        }
    )
