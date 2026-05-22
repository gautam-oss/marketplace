import pytest
from httpx import AsyncClient

CATEGORIES_URL = "/api/v1/categories"


# ── List ─────────────────────────────────────────────────────────────────────

async def test_list_categories_empty(async_client: AsyncClient):
    resp = await async_client.get(CATEGORIES_URL)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_categories_after_create(async_client: AsyncClient, admin_token: str):
    await async_client.post(
        CATEGORIES_URL,
        json={"name": "Electronics", "slug": "electronics"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await async_client.get(CATEGORIES_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Electronics"


# ── Create ───────────────────────────────────────────────────────────────────

async def test_create_category_as_admin(async_client: AsyncClient, admin_token: str):
    resp = await async_client.post(
        CATEGORIES_URL,
        json={"name": "Books", "slug": "books"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Books"
    assert data["slug"] == "books"
    assert "id" in data


async def test_create_category_as_buyer_forbidden(async_client: AsyncClient, buyer_token: str):
    resp = await async_client.post(
        CATEGORIES_URL,
        json={"name": "Clothing", "slug": "clothing"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 403


async def test_create_category_unauthenticated(async_client: AsyncClient):
    resp = await async_client.post(
        CATEGORIES_URL,
        json={"name": "Toys", "slug": "toys"},
    )
    assert resp.status_code == 401


async def test_create_subcategory(async_client: AsyncClient, admin_token: str):
    parent = await async_client.post(
        CATEGORIES_URL,
        json={"name": "Sports", "slug": "sports"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    parent_id = parent.json()["id"]

    resp = await async_client.post(
        CATEGORIES_URL,
        json={"name": "Football", "slug": "football", "parent_id": parent_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["parent_id"] == parent_id


# ── Get by slug ───────────────────────────────────────────────────────────────

async def test_get_category_by_slug(async_client: AsyncClient, admin_token: str):
    await async_client.post(
        CATEGORIES_URL,
        json={"name": "Home", "slug": "home-appliances"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await async_client.get(f"{CATEGORIES_URL}/home-appliances")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "home-appliances"


async def test_get_category_by_slug_not_found(async_client: AsyncClient):
    resp = await async_client.get(f"{CATEGORIES_URL}/nonexistent-slug")
    assert resp.status_code == 404


# ── Update ───────────────────────────────────────────────────────────────────

async def test_update_category_as_admin(async_client: AsyncClient, admin_token: str):
    created = await async_client.post(
        CATEGORIES_URL,
        json={"name": "Gadgets", "slug": "gadgets"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    cat_id = created.json()["id"]

    resp = await async_client.put(
        f"{CATEGORIES_URL}/{cat_id}",
        json={"name": "Gadgets & Tech"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Gadgets & Tech"


async def test_update_category_not_found(async_client: AsyncClient, admin_token: str):
    import uuid
    resp = await async_client.put(
        f"{CATEGORIES_URL}/{uuid.uuid4()}",
        json={"name": "Ghost"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ── Delete ───────────────────────────────────────────────────────────────────

async def test_delete_category_as_admin(async_client: AsyncClient, admin_token: str):
    created = await async_client.post(
        CATEGORIES_URL,
        json={"name": "ToDelete", "slug": "to-delete"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    cat_id = created.json()["id"]

    resp = await async_client.delete(
        f"{CATEGORIES_URL}/{cat_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"].lower()


async def test_delete_category_not_found(async_client: AsyncClient, admin_token: str):
    import uuid
    resp = await async_client.delete(
        f"{CATEGORIES_URL}/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
