from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.category import create_category
from app.crud.product import create_product, update_product
from app.models.user import User
from app.schemas.category import CategoryCreate
from app.schemas.product import ProductCreate, ProductUpdate

CART_URL = "/api/v1/cart"
ITEMS_URL = "/api/v1/cart/items"


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _active_product(db: AsyncSession, seller_id, title="Widget", price="200.00", stock=10):
    schema = ProductCreate(title=title, price=Decimal(price), stock=stock)
    p = await create_product(db, schema, seller_id=seller_id, images=[])
    return await update_product(db, p.id, ProductUpdate(status="active"))


async def _add_to_cart(client: AsyncClient, token: str, product_id, quantity: int = 1):
    return await client.post(
        ITEMS_URL,
        json={"product_id": str(product_id), "quantity": quantity},
        headers={"Authorization": f"Bearer {token}"},
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_get_empty_cart(async_client: AsyncClient, buyer_token: str):
    resp = await async_client.get(CART_URL, headers={"Authorization": f"Bearer {buyer_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert float(data["total"]) == 0.0
    assert data["item_count"] == 0


async def test_add_item_to_cart(
    async_client: AsyncClient, buyer_token: str, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id, title="Test Widget")

    resp = await _add_to_cart(async_client, buyer_token, product.id, quantity=2)
    assert resp.status_code == 201
    data = resp.json()
    assert data["item_count"] == 1
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["product"]["title"] == "Test Widget"


async def test_add_item_exceeds_stock(
    async_client: AsyncClient, buyer_token: str, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id, stock=2)

    resp = await _add_to_cart(async_client, buyer_token, product.id, quantity=99)
    assert resp.status_code == 201
    # Quantity should be capped at stock=2, not an error
    data = resp.json()
    assert data["items"][0]["quantity"] == 2


async def test_add_own_product(
    async_client: AsyncClient, seller_token: str, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id)

    resp = await _add_to_cart(async_client, seller_token, product.id)
    assert resp.status_code == 400


async def test_add_inactive_product(
    async_client: AsyncClient, buyer_token: str, seller_user: User, test_db: AsyncSession
):
    # Create draft product (not activated)
    schema = ProductCreate(title="Draft Item", price=Decimal("100.00"), stock=5)
    product = await create_product(test_db, schema, seller_id=seller_user.id, images=[])

    resp = await _add_to_cart(async_client, buyer_token, product.id)
    assert resp.status_code == 400


async def test_update_cart_item_quantity(
    async_client: AsyncClient, buyer_token: str, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id, stock=10)
    await _add_to_cart(async_client, buyer_token, product.id, quantity=1)

    resp = await async_client.put(
        f"{ITEMS_URL}/{product.id}",
        json={"quantity": 5},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["items"][0]["quantity"] == 5


async def test_update_cart_item_to_zero(
    async_client: AsyncClient, buyer_token: str, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id)
    await _add_to_cart(async_client, buyer_token, product.id, quantity=3)

    resp = await async_client.put(
        f"{ITEMS_URL}/{product.id}",
        json={"quantity": 0},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["item_count"] == 0
    assert data["items"] == []


async def test_remove_cart_item(
    async_client: AsyncClient, buyer_token: str, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id)
    await _add_to_cart(async_client, buyer_token, product.id, quantity=2)

    resp = await async_client.delete(
        f"{ITEMS_URL}/{product.id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["item_count"] == 0
    assert data["items"] == []


async def test_clear_cart(
    async_client: AsyncClient, buyer_token: str, seller_user: User, test_db: AsyncSession
):
    p1 = await _active_product(test_db, seller_user.id, title="Item A", stock=5)
    p2 = await _active_product(test_db, seller_user.id, title="Item B", stock=5)
    await _add_to_cart(async_client, buyer_token, p1.id)
    await _add_to_cart(async_client, buyer_token, p2.id)

    resp = await async_client.delete(
        CART_URL,
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Cart cleared"

    # Verify cart is actually empty
    cart_resp = await async_client.get(CART_URL, headers={"Authorization": f"Bearer {buyer_token}"})
    assert cart_resp.json()["item_count"] == 0


async def test_cart_unauthenticated(async_client: AsyncClient):
    resp = await async_client.get(CART_URL)
    assert resp.status_code == 401
