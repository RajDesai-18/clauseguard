"""Health endpoint tests."""

import pytest


@pytest.mark.anyio
async def test_health_endpoint_returns_200(client):
    """Health endpoint should return 200 with service statuses."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "services" in data
