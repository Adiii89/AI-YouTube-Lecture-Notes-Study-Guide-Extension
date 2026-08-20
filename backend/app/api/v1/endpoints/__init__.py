"""API v1 Endpoints."""
from app.api.v1.endpoints.health import router as health_router

__all__ = ["health_router"]
