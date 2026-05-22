from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.product import create_product, update_product
from app.crud.review import create_review
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate
from app.schemas.review import ReviewCreate

PRODUCTS_URL = "/api/v1/products"
REVIEWS_URL = "/api/v1/reviews"


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _active_product(db: AsyncSession, seller_id, title="Widget", price="200.00", stock=10):
    schema = ProductCreate(title=title, price=Decimal(price), stock=stock)
    p = await create_product(db, schema, seller_id=seller_id, images=[])
    return await update_product(db, p.id, ProductUpdate(status="active"))


# ── List reviews ──────────────────────────────────────────────────────────────

async def test_get_reviews_empty(
    async_client: AsyncClient, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id)
    resp = await async_client.get(f"{PRODUCTS_URL}/{product.id}/reviews")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reviews"]["items"] == []
    assert data["rating_summary"]["total"] == 0
    assert data["rating_summary"]["average"] == 0.0


async def test_get_reviews_with_entries(
    async_client: AsyncClient, buyer_user: User, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id)
    await create_review(test_db, ReviewCreate(rating=4, title="Good"), buyer_user.id, product.id)

    resp = await async_client.get(f"{PRODUCTS_URL}/{product.id}/reviews")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reviews"]["total"] == 1
    assert data["rating_summary"]["total"] == 1
    assert data["rating_summary"]["average"] == 4.0


# ── Create review ─────────────────────────────────────────────────────────────

async def test_create_review_as_buyer(
    async_client: AsyncClient, buyer_token: str, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id)
    resp = await async_client.post(
        f"{PRODUCTS_URL}/{product.id}/reviews",
        json={"rating": 5, "title": "Great!", "body": "Loved it"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["rating"] == 5
    assert data["title"] == "Great!"
    assert data["is_verified_purchase"] is False


async def test_create_review_as_seller_forbidden(
    async_client: AsyncClient, seller_token: str, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id)
    resp = await async_client.post(
        f"{PRODUCTS_URL}/{product.id}/reviews",
        json={"rating": 4},
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert resp.status_code == 403


async def test_create_review_unauthenticated(
    async_client: AsyncClient, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id)
    resp = await async_client.post(
        f"{PRODUCTS_URL}/{product.id}/reviews",
        json={"rating": 3},
    )
    assert resp.status_code == 401


async def test_create_review_duplicate(
    async_client: AsyncClient,
    buyer_token: str,
    buyer_user: User,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    await create_review(test_db, ReviewCreate(rating=3), buyer_user.id, product.id)

    resp = await async_client.post(
        f"{PRODUCTS_URL}/{product.id}/reviews",
        json={"rating": 4},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 409


async def test_create_review_invalid_rating(
    async_client: AsyncClient, buyer_token: str, seller_user: User, test_db: AsyncSession
):
    product = await _active_product(test_db, seller_user.id)
    resp = await async_client.post(
        f"{PRODUCTS_URL}/{product.id}/reviews",
        json={"rating": 6},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 422


# ── Update review ─────────────────────────────────────────────────────────────

async def test_update_review_owner(
    async_client: AsyncClient,
    buyer_token: str,
    buyer_user: User,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    review = await create_review(test_db, ReviewCreate(rating=3), buyer_user.id, product.id)

    resp = await async_client.put(
        f"{PRODUCTS_URL}/{product.id}/reviews/{review.id}",
        json={"rating": 5, "title": "Updated"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["rating"] == 5
    assert resp.json()["title"] == "Updated"


async def test_update_review_other_user_forbidden(
    async_client: AsyncClient,
    seller_token: str,
    buyer_user: User,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    review = await create_review(test_db, ReviewCreate(rating=3), buyer_user.id, product.id)

    resp = await async_client.put(
        f"{PRODUCTS_URL}/{product.id}/reviews/{review.id}",
        json={"rating": 1},
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert resp.status_code == 403


# ── Delete review ─────────────────────────────────────────────────────────────

async def test_delete_review_owner(
    async_client: AsyncClient,
    buyer_token: str,
    buyer_user: User,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    review = await create_review(test_db, ReviewCreate(rating=4), buyer_user.id, product.id)

    resp = await async_client.delete(
        f"{PRODUCTS_URL}/{product.id}/reviews/{review.id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Review deleted"


async def test_delete_review_by_admin(
    async_client: AsyncClient,
    admin_token: str,
    buyer_user: User,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    review = await create_review(test_db, ReviewCreate(rating=2), buyer_user.id, product.id)

    resp = await async_client.delete(
        f"{PRODUCTS_URL}/{product.id}/reviews/{review.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200


async def test_delete_review_other_user_forbidden(
    async_client: AsyncClient,
    seller_token: str,
    buyer_user: User,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    review = await create_review(test_db, ReviewCreate(rating=5), buyer_user.id, product.id)

    resp = await async_client.delete(
        f"{PRODUCTS_URL}/{product.id}/reviews/{review.id}",
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert resp.status_code == 403


# ── Helpful ───────────────────────────────────────────────────────────────────

async def test_mark_helpful(
    async_client: AsyncClient,
    seller_token: str,
    buyer_user: User,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    review = await create_review(test_db, ReviewCreate(rating=5), buyer_user.id, product.id)

    resp = await async_client.post(
        f"{REVIEWS_URL}/{review.id}/helpful",
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Marked as helpful"


async def test_mark_own_review_helpful(
    async_client: AsyncClient,
    buyer_token: str,
    buyer_user: User,
    seller_user: User,
    test_db: AsyncSession,
):
    product = await _active_product(test_db, seller_user.id)
    review = await create_review(test_db, ReviewCreate(rating=5), buyer_user.id, product.id)

    resp = await async_client.post(
        f"{REVIEWS_URL}/{review.id}/helpful",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 400
