import json
import uuid
from decimal import Decimal
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.crud.order import get_order_by_id, update_order_status
from app.crud.product import create_product, get_product_by_id as gpid, update_product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate

from tests.conftest import TestSessionLocal

ORDERS_URL = "/api/v1/orders"
CHECKOUT_URL = "/api/v1/orders/checkout"
WEBHOOK_URL = "/api/v1/orders/webhook"


# ── Helpers ──────────────────────────────────────────────────────────────────

_SHIPPING = {
    "full_name": "Test Buyer",
    "phone": "9876543210",
    "line1": "123 Main St",
    "city": "Mumbai",
    "state": "Maharashtra",
    "pincode": "400001",
    "country": "India",
}

_FAKE_RZ_ORDER = {"id": "order_FAKE123456789", "amount": 10000, "currency": "INR"}


async def _active_product(db: AsyncSession, seller_id, title="Widget", price="200.00", stock=10):
    schema = ProductCreate(title=title, price=Decimal(price), stock=stock)
    p = await create_product(db, schema, seller_id=seller_id, images=[])
    return await update_product(db, p.id, ProductUpdate(status="active"))


def _checkout_payload(product_id, quantity=1):
    return {
        "items": [{"product_id": str(product_id), "quantity": quantity}],
        "shipping_address": _SHIPPING,
    }


async def _place_order(client: AsyncClient, token: str, product_id) -> dict:
    with patch(
        "app.api.v1.orders.razorpay_service.create_order",
        return_value=_FAKE_RZ_ORDER,
    ):
        resp = await client.post(
            CHECKOUT_URL,
            json=_checkout_payload(product_id),
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Checkout tests ────────────────────────────────────────────────────────────

async def test_checkout_success(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id, price="600.00")

    with patch(
        "app.api.v1.orders.razorpay_service.create_order",
        return_value=_FAKE_RZ_ORDER,
    ):
        resp = await async_client.post(
            CHECKOUT_URL,
            json=_checkout_payload(product.id),
            headers={"Authorization": f"Bearer {buyer_token}"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["razorpay_order_id"] == _FAKE_RZ_ORDER["id"]
    assert "order_id" in data
    assert data["razorpay_key_id"] is not None


async def test_checkout_product_not_found(
    async_client: AsyncClient, buyer_token: str
):
    resp = await async_client.post(
        CHECKOUT_URL,
        json=_checkout_payload(uuid.uuid4()),
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 404


async def test_checkout_out_of_stock(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id, stock=1)

    with patch("app.api.v1.orders.razorpay_service.create_order", return_value=_FAKE_RZ_ORDER):
        resp = await async_client.post(
            CHECKOUT_URL,
            json=_checkout_payload(product.id, quantity=99),
            headers={"Authorization": f"Bearer {buyer_token}"},
        )
    assert resp.status_code == 400


async def test_checkout_own_product(
    async_client: AsyncClient,
    seller_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)

    with patch("app.api.v1.orders.razorpay_service.create_order", return_value=_FAKE_RZ_ORDER):
        resp = await async_client.post(
            CHECKOUT_URL,
            json=_checkout_payload(product.id),
            headers={"Authorization": f"Bearer {seller_token}"},
        )
    # seller role is rejected by require_role("buyer") before ownership check
    assert resp.status_code == 403


async def test_checkout_inactive_product(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    schema = ProductCreate(title="Draft", price=Decimal("100.00"), stock=5)
    product = await create_product(test_db, schema, seller_id=seller_user.id, images=[])

    with patch("app.api.v1.orders.razorpay_service.create_order", return_value=_FAKE_RZ_ORDER):
        resp = await async_client.post(
            CHECKOUT_URL,
            json=_checkout_payload(product.id),
            headers={"Authorization": f"Bearer {buyer_token}"},
        )
    assert resp.status_code == 400


async def test_checkout_unauthenticated(async_client: AsyncClient):
    resp = await async_client.post(CHECKOUT_URL, json=_checkout_payload(uuid.uuid4()))
    assert resp.status_code == 401


# ── Webhook tests ─────────────────────────────────────────────────────────────

def _webhook_body(rz_order_id: str, event: str = "payment.captured", payment_id: str = "pay_FAKE") -> bytes:
    payload = {
        "event": event,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": rz_order_id,
                }
            }
        },
    }
    return json.dumps(payload).encode()


async def test_webhook_payment_captured(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    rz_order_id = checkout_data["razorpay_order_id"]

    body = _webhook_body(rz_order_id)
    with patch("app.api.v1.orders.verify_webhook_signature", return_value=True), \
         patch("app.tasks.email_tasks.send_order_confirmation_email.delay"):
        resp = await async_client.post(
            WEBHOOK_URL,
            content=body,
            headers={"X-Razorpay-Signature": "sig"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    async with TestSessionLocal() as db:
        order_id = uuid.UUID(checkout_data["order_id"])
        order = await get_order_by_id(db, order_id)
    assert order.status == "paid"


async def test_webhook_payment_failed(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id, stock=5)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    rz_order_id = checkout_data["razorpay_order_id"]

    body = _webhook_body(rz_order_id, event="payment.failed")
    with patch("app.api.v1.orders.verify_webhook_signature", return_value=True):
        resp = await async_client.post(
            WEBHOOK_URL,
            content=body,
            headers={"X-Razorpay-Signature": "sig"},
        )

    assert resp.status_code == 200
    async with TestSessionLocal() as db:
        order_id = uuid.UUID(checkout_data["order_id"])
        order = await get_order_by_id(db, order_id)
    assert order.status == "cancelled"


async def test_webhook_invalid_signature(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    body = _webhook_body(checkout_data["razorpay_order_id"])

    # No mock → verify_webhook_signature returns False (bad sig)
    resp = await async_client.post(
        WEBHOOK_URL,
        content=body,
        headers={"X-Razorpay-Signature": "badsig"},
    )
    assert resp.status_code == 400


async def test_webhook_duplicate_captured(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    rz_order_id = checkout_data["razorpay_order_id"]

    body = _webhook_body(rz_order_id)
    with patch("app.api.v1.orders.verify_webhook_signature", return_value=True), \
         patch("app.tasks.email_tasks.send_order_confirmation_email.delay"):
        await async_client.post(WEBHOOK_URL, content=body, headers={"X-Razorpay-Signature": "sig"})

    # Second capture — idempotent, order already "paid", condition skipped
    with patch("app.api.v1.orders.verify_webhook_signature", return_value=True), \
         patch("app.tasks.email_tasks.send_order_confirmation_email.delay"):
        resp = await async_client.post(
            WEBHOOK_URL, content=body, headers={"X-Razorpay-Signature": "sig"}
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── List / get tests ──────────────────────────────────────────────────────────

async def test_list_orders_buyer_sees_only_own(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    await _place_order(async_client, buyer_token, product.id)

    resp = await async_client.get(ORDERS_URL, headers={"Authorization": f"Bearer {buyer_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "pending"


async def test_list_orders_seller_sees_own_products_orders(
    async_client: AsyncClient,
    buyer_token: str,
    seller_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    await _place_order(async_client, buyer_token, product.id)

    resp = await async_client.get(ORDERS_URL, headers={"Authorization": f"Bearer {seller_token}"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_get_order_detail_owner(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    order_id = checkout_data["order_id"]

    resp = await async_client.get(
        f"{ORDERS_URL}/{order_id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


async def test_get_order_detail_other_buyer(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    async with TestSessionLocal() as db:
        other = User(
            email="other_buyer@test.com",
            hashed_password=hash_password("TestPass123!"),
            full_name="Other Buyer",
            role="buyer",
        )
        db.add(other)
        await db.commit()
        await db.refresh(other)
        other_token = create_access_token({"sub": str(other.id), "role": other.role})

    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    order_id = checkout_data["order_id"]

    resp = await async_client.get(
        f"{ORDERS_URL}/{order_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 403


# ── Cancel tests ──────────────────────────────────────────────────────────────

async def test_cancel_pending_order(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id, stock=3)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    order_id = checkout_data["order_id"]

    resp = await async_client.post(
        f"{ORDERS_URL}/{order_id}/cancel",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    async with TestSessionLocal() as db:
        refreshed = await gpid(db, product.id, load_relations=False)
    assert refreshed.stock == 3


async def test_cancel_shipped_order_as_buyer(
    async_client: AsyncClient,
    buyer_token: str,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    checkout_data = await _place_order(async_client, buyer_token, product.id)
    order_id = checkout_data["order_id"]

    async with TestSessionLocal() as db:
        order = await get_order_by_id(db, uuid.UUID(order_id))
        await update_order_status(db, order, "paid")
        order = await get_order_by_id(db, uuid.UUID(order_id))
        await update_order_status(db, order, "processing")
        order = await get_order_by_id(db, uuid.UUID(order_id))
        await update_order_status(db, order, "shipped")

    resp = await async_client.post(
        f"{ORDERS_URL}/{order_id}/cancel",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 400
