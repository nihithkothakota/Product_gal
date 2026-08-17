"""
Tests for authentication endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Register a new user and receive tokens."""
    response = await client.post("/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword123",
        "display_name": "Test User",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Registering with an existing email returns 409."""
    await client.post("/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "password123",
    })
    response = await client.post("/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "password456",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Login with valid credentials returns tokens."""
    await client.post("/v1/auth/register", json={
        "email": "login@example.com",
        "password": "password123",
    })
    response = await client.post("/v1/auth/login", json={
        "email": "login@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Login with wrong password returns 401."""
    await client.post("/v1/auth/register", json={
        "email": "wrong@example.com",
        "password": "password123",
    })
    response = await client.post("/v1/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    """Authenticated user can fetch their profile."""
    reg_response = await client.post("/v1/auth/register", json={
        "email": "me@example.com",
        "password": "password123",
        "display_name": "Me User",
    })
    token = reg_response.json()["access_token"]

    response = await client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
    assert response.json()["display_name"] == "Me User"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    """Unauthenticated request to /me returns 403."""
    response = await client.get("/v1/auth/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """Refresh token returns a new token pair."""
    reg_response = await client.post("/v1/auth/register", json={
        "email": "refresh@example.com",
        "password": "password123",
    })
    refresh_token = reg_response.json()["refresh_token"]

    response = await client.post("/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
