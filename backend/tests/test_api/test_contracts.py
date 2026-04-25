"""Tests for contract upload and retrieval endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

# --- Authentication-required behavior ---------------------------------------
# These tests assert that unauthenticated requests are rejected with 401.
# They use the plain `client` fixture (no auth override) on purpose.


@pytest.mark.asyncio
async def test_upload_requires_authentication(client: AsyncClient) -> None:
    """POST /contracts/upload returns 401 without a session."""
    response = await client.post(
        "/api/v1/contracts/upload",
        files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_contracts_requires_authentication(client: AsyncClient) -> None:
    """GET /contracts returns 401 without a session."""
    response = await client.get("/api/v1/contracts")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_contract_requires_authentication(client: AsyncClient) -> None:
    """GET /contracts/{id} returns 401 without a session."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/contracts/{fake_id}")
    assert response.status_code == 401


# --- Authenticated behavior ------------------------------------------------
# These tests use `authenticated_client` which overrides get_current_user
# to return a fixed test_user, isolating endpoint logic from auth concerns.


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_type(authenticated_client: AsyncClient) -> None:
    """Uploading a non-PDF/DOCX file should return 415."""
    response = await authenticated_client.post(
        "/api/v1/contracts/upload",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(authenticated_client: AsyncClient) -> None:
    """Uploading an empty PDF should return 400."""
    response = await authenticated_client.post(
        "/api/v1/contracts/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.db
@pytest.mark.asyncio
async def test_list_contracts_returns_200(authenticated_client: AsyncClient) -> None:
    """Listing contracts should return 200 with pagination structure."""
    response = await authenticated_client.get("/api/v1/contracts")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data


@pytest.mark.db
@pytest.mark.asyncio
async def test_get_contract_not_found(authenticated_client: AsyncClient) -> None:
    """Getting a non-existent contract should return 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await authenticated_client.get(f"/api/v1/contracts/{fake_id}")
    assert response.status_code == 404
