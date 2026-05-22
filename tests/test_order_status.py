"""Tests for PATCH /orders/{id}/status and POST /orders/{id}/cancel."""
import uuid
from decimal import Decimal
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.crud.order import get_order_by_id, update_order_status
from app.crud.product import create_product, update_product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate

from tests.conftest import TestSessionLocal

ORDERS_URL = "/api/v1/orders"
CHECKOUT_URL = "/api/v1/orders/checkout"

_SHIPPING = {
    "full_name": "Test Buyer",
    "phone": "9876543210",
    "line1": "123 Main St",
    "city": "Mumbai",
    "state": "Maharashtra",
    "pincode": "400001",
    "country": "India",
}

_FAKE_RZ_ORDER = {"id": "order_STATUS123", "amount": 20000, "currency": "INR"}


async def _active_product(db: AsyncSession, seller_id, stock=10):
    schema = ProductCreate(title="Status Widget", price=Decimal("200.00"), stock=stock)
    p = await create_product(db, schema, seller_id=seller_id, images=[])
    return await update_product(db, p.id, ProductUpdate(status="active"))


async def _place_order(client: AsyncClient, token: str, product_id) -> dict:
    with patch("app.api.v1.orders.razorpay_service.create_order", return_value=_FAKE_RZ_ORDER):
        resp = await client.post(
            CHECKOUT_URL,
            json={"items": [{"product_id": str(product_id), "quantity": 1}], "shipping_address": _SHIPPING},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _advance_to(db: AsyncSession, order_id: str, *statuses: str):
    for s in statuses:
        order = await get_order_by_id(db, uuid.UUID(order_id))
        await update_order_status(db, order, s)


# ── PATCH /{id}/status ─────────────────────────────────────────────────────────

async def test_admin_advances_order_paid_to_processing(
    async_client: AsyncClient,
    admin_token: str,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    order_id = checkout_data["order_id"]

    async with TestSessionLocal() as db:
        await _advance_to(db, order_id, "paid")

    resp = await async_client.patch(
        f"{ORDERS_URL}/{order_id}/status",
        json={"status": "processing"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"


async def test_admin_advances_order_to_shipped(
    async_client: AsyncClient,
    admin_token: str,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    order_id = checkout_data["order_id"]

    async with TestSessionLocal() as db:
        await _advance_to(db, order_id, "paid", "processing")

    with patch("app.tasks.email_tasks.send_shipping_notification_email.delay"):
        resp = await async_client.patch(
            f"{ORDERS_URL}/{order_id}/status",
            json={"status": "shipped"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "shipped"


async def test_admin_advances_order_to_delivered(
    async_client: AsyncClient,
    admin_token: str,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    order_id = checkout_data["order_id"]

    async with TestSessionLocal() as db:
        await _advance_to(db, order_id, "paid", "processing", "shipped")

    resp = await async_client.patch(
        f"{ORDERS_URL}/{order_id}/status",
        json={"status": "delivered"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "delivered"


async def test_invalid_transition_rejected(
    async_client: AsyncClient,
    admin_token: str,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    order_id = checkout_data["order_id"]

    # pending → shipped is invalid (must go pending → paid → processing → shipped)
    resp = await async_client.patch(
        f"{ORDERS_URL}/{order_id}/status",
        json={"status": "shipped"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


async def test_seller_advances_own_product_order(
    async_client: AsyncClient,
    seller_token: str,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    order_id = checkout_data["order_id"]

    async with TestSessionLocal() as db:
        await _advance_to(db, order_id, "paid")

    resp = await async_client.patch(
        f"{ORDERS_URL}/{order_id}/status",
        json={"status": "processing"},
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"


async def test_buyer_cannot_advance_status(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    order_id = checkout_data["order_id"]

    async with TestSessionLocal() as db:
        await _advance_to(db, order_id, "paid")

    resp = await async_client.patch(
        f"{ORDERS_URL}/{order_id}/status",
        json={"status": "processing"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 403


async def test_update_status_order_not_found(async_client: AsyncClient, admin_token: str):
    resp = await async_client.patch(
        f"{ORDERS_URL}/{uuid.uuid4()}/status",
        json={"status": "processing"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


async def test_update_status_unauthenticated(async_client: AsyncClient):
    resp = await async_client.patch(
        f"{ORDERS_URL}/{uuid.uuid4()}/status",
        json={"status": "processing"},
    )
    assert resp.status_code == 401
