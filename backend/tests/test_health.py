from fastapi import status
from starlette.testclient import TestClient
from app.core.config import settings


def test_root_endpoint(client: TestClient):
    """Test the root index endpoint."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "message" in data
    assert data["docs_url"] == "/docs"
    assert data["version"] == settings.VERSION


def test_health_check_endpoint(client: TestClient):
    """Test the /api/v1/health endpoint returns 200 and valid schema."""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["project_name"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION
    assert data["environment"] == settings.ENVIRONMENT
    assert "timestamp" in data
    assert "services" in data
    assert data["services"]["api"] == "up"


def test_cors_headers(client: TestClient):
    """Test CORS headers on health check endpoint."""
    response = client.get(
        f"{settings.API_V1_STR}/health",
        headers={"Origin": "http://localhost:8000"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access-control-allow-origin" in response.headers
