"""
Tests for product CRUD endpoints.
"""

import pytest
from httpx import AsyncClient


async def _get_auth_header(client: AsyncClient) -> dict:
    """Helper: register a user and return auth headers."""
    response = await client.post("/v1/auth/register", json={
        "email": "product_test@example.com",
        "password": "password123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_product_manual(client: AsyncClient):
    """Create a product with manual entry."""
    headers = await _get_auth_header(client)
    response = await client.post("/v1/products", json={
        "title": "Test Product",
        "brand": "Test Brand",
        "price_current": 999.99,
        "currency": "INR",
        "source": "manual",
        "notes": "Great product!",
    }, headers=headers)
    assert response.status_code == 202
    data = response.json()
    assert data["title"] == "Test Product"
    assert data["brand"] == "Test Brand"
    assert data["status"] == "enriched"  # manual entries are immediately enriched


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient):
    """List products returns paginated results."""
    headers = await _get_auth_header(client)

    # Create a few products
    for i in range(3):
        await client.post("/v1/products", json={
            "title": f"Product {i}",
            "source": "manual",
        }, headers=headers)

    response = await client.get("/v1/products", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_get_product(client: AsyncClient):
    """Get a specific product by ID."""
    headers = await _get_auth_header(client)
    create_resp = await client.post("/v1/products", json={
        "title": "Detail Product",
        "price_current": 500,
    }, headers=headers)
    product_id = create_resp.json()["id"]

    response = await client.get(f"/v1/products/{product_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Detail Product"


@pytest.mark.asyncio
async def test_update_product(client: AsyncClient):
    """Update product fields."""
    headers = await _get_auth_header(client)
    create_resp = await client.post("/v1/products", json={
        "title": "Old Title",
    }, headers=headers)
    product_id = create_resp.json()["id"]

    response = await client.put(f"/v1/products/{product_id}", json={
        "title": "New Title",
        "price_current": 1499.00,
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient):
    """Soft-delete a product."""
    headers = await _get_auth_header(client)
    create_resp = await client.post("/v1/products", json={
        "title": "To Delete",
    }, headers=headers)
    product_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/v1/products/{product_id}", headers=headers)
    assert delete_resp.status_code == 204

    # Should not appear in list
    list_resp = await client.get("/v1/products", headers=headers)
    ids = [p["id"] for p in list_resp.json()["items"]]
    assert product_id not in ids


@pytest.mark.asyncio
async def test_toggle_favorite(client: AsyncClient):
    """Toggle a product's favorite status."""
    headers = await _get_auth_header(client)
    create_resp = await client.post("/v1/products", json={
        "title": "Fav Product",
    }, headers=headers)
    product_id = create_resp.json()["id"]
    assert create_resp.json()["is_favorite"] is False

    # Toggle on
    fav_resp = await client.post(f"/v1/products/{product_id}/favorite", headers=headers)
    assert fav_resp.json()["is_favorite"] is True

    # Toggle off
    fav_resp2 = await client.post(f"/v1/products/{product_id}/favorite", headers=headers)
    assert fav_resp2.json()["is_favorite"] is False
