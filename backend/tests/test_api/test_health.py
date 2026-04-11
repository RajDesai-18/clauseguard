"""Health endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client):
    """Health endpoint should return 200 with service statuses.

    Note: Returns 'degraded' status locally when services are not running.
    The important thing is it responds 200 and does not crash.
    """
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "services" in data
    assert data["status"] in ("healthy", "degraded")
