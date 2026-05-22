import uuid
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.product import create_product, update_product
from app.crud.review import create_review
from app.crud.user import get_user_by_email
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate
from app.schemas.review import ReviewCreate

ADMIN_URL = "/api/v1/admin"


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _active_product(db: AsyncSession, seller_id, title="Widget", price="200.00", stock=10):
    schema = ProductCreate(title=title, price=Decimal(price), stock=stock)
    p = await create_product(db, schema, seller_id=seller_id, images=[])
    return await update_product(db, p.id, ProductUpdate(status="active"))


# ── Stats ─────────────────────────────────────────────────────────────────────

async def test_admin_get_stats(async_client: AsyncClient, admin_token: str):
    resp = await async_client.get(
        f"{ADMIN_URL}/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "total_sellers" in data
    assert "total_buyers" in data
    assert "total_products" in data
    assert "active_products" in data
    assert "total_orders" in data
    assert "orders_by_status" in data
    assert "revenue_this_month" in data
    assert "revenue_last_month" in data
    assert "new_users_this_week" in data


async def test_admin_stats_non_admin_forbidden(async_client: AsyncClient, buyer_token: str):
    resp = await async_client.get(
        f"{ADMIN_URL}/stats",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 403


# ── Users ─────────────────────────────────────────────────────────────────────

async def test_admin_list_users(
    async_client: AsyncClient, admin_token: str, buyer_user: User
):
    resp = await async_client.get(
        f"{ADMIN_URL}/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2  # at least admin + buyer


async def test_admin_list_users_non_admin_forbidden(
    async_client: AsyncClient, buyer_token: str
):
    resp = await async_client.get(
        f"{ADMIN_URL}/users",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 403


async def test_admin_update_user_role(
    async_client: AsyncClient, admin_token: str, buyer_user: User
):
    resp = await async_client.patch(
        f"{ADMIN_URL}/users/{buyer_user.id}",
        json={"role": "seller"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "seller"


async def test_admin_deactivate_user(
    async_client: AsyncClient, admin_token: str, buyer_user: User
):
    resp = await async_client.patch(
        f"{ADMIN_URL}/users/{buyer_user.id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_admin_cannot_change_own_role(
    async_client: AsyncClient, admin_token: str, test_db: AsyncSession
):
    admin = await get_user_by_email(test_db, "admin@test.com")
    resp = await async_client.patch(
        f"{ADMIN_URL}/users/{admin.id}",
        json={"role": "buyer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


async def test_admin_update_user_not_found(async_client: AsyncClient, admin_token: str):
    resp = await async_client.patch(
        f"{ADMIN_URL}/users/{uuid.uuid4()}",
        json={"role": "seller"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ── Products ──────────────────────────────────────────────────────────────────

async def test_admin_list_products(
    async_client: AsyncClient, admin_token: str, seller_user: User, test_db: AsyncSession
):
    await _active_product(test_db, seller_user.id, title="AdminProd")
    resp = await async_client.get(
        f"{ADMIN_URL}/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


async def test_admin_list_products_all_statuses(
    async_client: AsyncClient, admin_token: str, seller_user: User, test_db: AsyncSession
):
    # Create a draft product (not activated)
    schema = ProductCreate(title="Draft Product", price=Decimal("100.00"), stock=5)
    await create_product(test_db, schema, seller_id=seller_user.id, images=[])

    # No status filter → returns all including draft
    resp = await async_client.get(
        f"{ADMIN_URL}/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    # Status=draft filter
    resp2 = await async_client.get(
        f"{ADMIN_URL}/products?status=draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["total"] >= 1


async def test_admin_update_product_status(
    async_client: AsyncClient, admin_token: str, seller_user: User, test_db: AsyncSession
):
    schema = ProductCreate(title="Status Test", price=Decimal("50.00"), stock=3)
    product = await create_product(test_db, schema, seller_id=seller_user.id, images=[])

    resp = await async_client.patch(
        f"{ADMIN_URL}/products/{product.id}/status",
        json={"status": "archived"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


# ── Orders ────────────────────────────────────────────────────────────────────

async def test_admin_list_orders(async_client: AsyncClient, admin_token: str):
    resp = await async_client.get(
        f"{ADMIN_URL}/orders",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data


# ── Reviews ───────────────────────────────────────────────────────────────────

async def test_admin_delete_review(
    async_client: AsyncClient,
    admin_token: str,
    buyer_user: User,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id, title="ReviewProd")
    review = await create_review(test_db, ReviewCreate(rating=3), buyer_user.id, product.id)

    resp = await async_client.delete(
        f"{ADMIN_URL}/reviews/{review.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Review deleted"


async def test_admin_delete_review_not_found(async_client: AsyncClient, admin_token: str):
    resp = await async_client.delete(
        f"{ADMIN_URL}/reviews/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
