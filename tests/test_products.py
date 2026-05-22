from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.crud.category import create_category
from app.crud.product import create_product, get_product_by_id, update_product
from app.models.user import User
from app.schemas.category import CategoryCreate
from app.schemas.product import ProductCreate, ProductUpdate

from tests.conftest import TestSessionLocal

PRODUCTS_URL = "/api/v1/products"


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _make_active_product(
    db: AsyncSession,
    seller_id,
    title: str = "Test Product",
    price: str = "999.00",
    stock: int = 10,
    category_id=None,
) -> object:
    schema = ProductCreate(
        title=title,
        price=Decimal(price),
        stock=stock,
        category_id=category_id,
    )
    product = await create_product(db, schema, seller_id=seller_id, images=[])
    return await update_product(db, product.id, ProductUpdate(status="active"))


# ── List products ─────────────────────────────────────────────────────────────

async def test_list_products_empty_returns_paginated(async_client: AsyncClient):
    resp = await async_client.get(PRODUCTS_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert "pages" in data


async def test_list_products_filters_by_category(
    async_client: AsyncClient, seller_user: User, test_db: AsyncSession
):
    cat = await create_category(test_db, CategoryCreate(name="Electronics"))
    await _make_active_product(test_db, seller_user.id, title="Laptop", category_id=cat.id)

    resp = await async_client.get(PRODUCTS_URL, params={"category": cat.slug})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Laptop"


async def test_list_products_filters_by_price_range(
    async_client: AsyncClient, seller_user: User, test_db: AsyncSession
):
    await _make_active_product(test_db, seller_user.id, title="Mid-range", price="500.00")

    resp = await async_client.get(PRODUCTS_URL, params={"min_price": "400", "max_price": "600"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Mid-range"


# ── Get product by slug ───────────────────────────────────────────────────────

async def test_get_product_by_slug_success(
    async_client: AsyncClient, seller_user: User, test_db: AsyncSession
):
    product = await _make_active_product(test_db, seller_user.id, title="My Active Phone")

    resp = await async_client.get(f"{PRODUCTS_URL}/{product.slug}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "My Active Phone"


async def test_get_product_not_found(async_client: AsyncClient):
    resp = await async_client.get(f"{PRODUCTS_URL}/no-such-product-slug")
    assert resp.status_code == 404


async def test_get_draft_product_as_buyer(
    async_client: AsyncClient, seller_user: User, test_db: AsyncSession
):
    schema = ProductCreate(title="Draft Item", price=Decimal("200.00"), stock=5)
    product = await create_product(test_db, schema, seller_id=seller_user.id, images=[])
    # status remains "draft" — do NOT activate

    resp = await async_client.get(f"{PRODUCTS_URL}/{product.slug}")
    assert resp.status_code == 404


# ── Create product ────────────────────────────────────────────────────────────

async def test_create_product_as_seller(
    async_client: AsyncClient, seller_token: str, test_db: AsyncSession
):
    cat = await create_category(test_db, CategoryCreate(name="Gadgets"))
    resp = await async_client.post(
        PRODUCTS_URL,
        data={
            "title": "New Gadget",
            "price": "1299.00",
            "stock": "5",
            "category_id": str(cat.id),
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "New Gadget"
    assert resp.json()["status"] == "draft"


async def test_create_product_as_buyer(async_client: AsyncClient, buyer_token: str):
    resp = await async_client.post(
        PRODUCTS_URL,
        data={"title": "Buyer Attempt", "price": "100.00", "stock": "1"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 403


async def test_create_product_unauthenticated(async_client: AsyncClient):
    resp = await async_client.post(
        PRODUCTS_URL,
        data={"title": "Unauth Attempt", "price": "100.00", "stock": "1"},
    )
    assert resp.status_code == 401


# ── Update product ────────────────────────────────────────────────────────────

async def test_update_product_own(
    async_client: AsyncClient, seller_user: User, seller_token: str, test_db: AsyncSession
):
    product = await _make_active_product(test_db, seller_user.id, title="Original Title")

    resp = await async_client.put(
        f"{PRODUCTS_URL}/{product.id}",
        json={"title": "Updated Title"},
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


async def test_update_product_another_sellers(
    async_client: AsyncClient, seller_token: str, test_db: AsyncSession
):
    # Create a second seller who owns the product
    other_seller = User(
        email="other_seller@test.com",
        hashed_password=hash_password("TestPass123!"),
        full_name="Other Seller",
        role="seller",
    )
    test_db.add(other_seller)
    await test_db.commit()
    await test_db.refresh(other_seller)

    product = await _make_active_product(test_db, other_seller.id, title="Other Product")

    resp = await async_client.put(
        f"{PRODUCTS_URL}/{product.id}",
        json={"title": "Hijacked"},
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert resp.status_code == 403


# ── Status change ─────────────────────────────────────────────────────────────

async def test_activate_product_no_stock(
    async_client: AsyncClient, seller_user: User, seller_token: str, test_db: AsyncSession
):
    cat = await create_category(test_db, CategoryCreate(name="No-stock Cat"))
    schema = ProductCreate(title="Zero Stock Item", price=Decimal("50.00"), stock=0, category_id=cat.id)
    product = await create_product(test_db, schema, seller_id=seller_user.id, images=[])

    resp = await async_client.patch(
        f"{PRODUCTS_URL}/{product.id}/status",
        json={"status": "active"},
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert resp.status_code == 400


# ── Delete product ────────────────────────────────────────────────────────────

async def test_delete_product_sets_archived(
    async_client: AsyncClient, seller_user: User, seller_token: str, test_db: AsyncSession
):
    product = await _make_active_product(test_db, seller_user.id, title="To Delete")

    resp = await async_client.delete(
        f"{PRODUCTS_URL}/{product.id}",
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Product deleted"

    # Use a fresh session to avoid identity-map staleness
    async with TestSessionLocal() as fresh_db:
        refreshed = await get_product_by_id(fresh_db, product.id, load_relations=False)
    assert refreshed.status == "archived"
