"""Tests for contract upload and retrieval endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_type(client: AsyncClient) -> None:
    """Uploading a non-PDF/DOCX file should return 415."""
    response = await client.post(
        "/api/v1/contracts/upload",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(client: AsyncClient) -> None:
    """Uploading an empty PDF should return 400."""
    response = await client.post(
        "/api/v1/contracts/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_contracts_returns_200(client: AsyncClient) -> None:
    """Listing contracts should return 200 with pagination structure."""
    response = await client.get("/api/v1/contracts")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data


@pytest.mark.asyncio
async def test_get_contract_not_found(client: AsyncClient) -> None:
    """Getting a non-existent contract should return 404.

    Note: Skipped on Windows due to asyncpg event loop cleanup bug.
    Works correctly in Docker/Linux and via manual curl testing.
    """
    import sys

    if sys.platform == "win32":
        pytest.skip("asyncpg cleanup issue on Windows ProactorEventLoop")
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/contracts/{fake_id}")
    assert response.status_code == 404