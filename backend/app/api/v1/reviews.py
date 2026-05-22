import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_role
from app.core.redis import cache_delete
from app.crud.product import get_product_by_id
from app.crud.review import (
    create_review,
    delete_review,
    get_rating_summary,
    get_review_by_id,
    get_review_by_user_product,
    increment_helpful,
    list_reviews_by_product,
    update_review,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.review import RatingSummary, ReviewCreate, ReviewResponse, ReviewUpdate
from app.services.search import ElasticsearchService, get_es_client

product_reviews_router = APIRouter(prefix="/products", tags=["reviews"])
reviews_router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewListResponse(BaseModel):
    reviews: PaginatedResponse[ReviewResponse]
    rating_summary: RatingSummary


async def _reindex_product(db: AsyncSession, product_id: uuid.UUID) -> None:
    try:
        product = await get_product_by_id(db, product_id)
        if product:
            await ElasticsearchService.index_product(get_es_client(), product)
    except Exception:
        pass


@product_reviews_router.get("/{product_id}/reviews", response_model=ReviewListResponse, summary="List reviews for a product")
async def get_product_reviews(
    product_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort: str = Query("recent"),
    db: AsyncSession = Depends(get_db),
):
    summary = await get_rating_summary(db, product_id)
    items, total = await list_reviews_by_product(db, product_id, page=page, per_page=per_page, sort=sort)
    pages = (total + per_page - 1) // per_page
    return ReviewListResponse(
        reviews=PaginatedResponse(
            items=[ReviewResponse.model_validate(r) for r in items],
            total=total, page=page, per_page=per_page, pages=pages,
        ),
        rating_summary=RatingSummary(**summary),
    )


@product_reviews_router.post(
    "/{product_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a product review (one per buyer per product)",
)
async def create_product_review(
    product_id: uuid.UUID,
    data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("buyer")),
):
    product = await get_product_by_id(db, product_id, load_relations=False)
    if not product or product.status == "archived":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    existing = await get_review_by_user_product(db, current_user.id, product_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already reviewed this product")

    # Verified purchase: buyer must have a delivered order containing this product
    from sqlalchemy import exists, select as sa_select
    from app.models.order import Order, OrderItem

    is_verified = bool((await db.execute(
        sa_select(exists().where(
            Order.buyer_id == current_user.id,
            Order.status == "delivered",
            OrderItem.order_id == Order.id,
            OrderItem.product_id == product_id,
        ))
    )).scalar())

    review = await create_review(db, data, current_user.id, product_id, is_verified_purchase=is_verified)

    await cache_delete(f"products:slug:{product.slug}")
    await _reindex_product(db, product_id)

    return review


@product_reviews_router.put("/{product_id}/reviews/{review_id}", response_model=ReviewResponse, summary="Edit your review")
async def update_product_review(
    product_id: uuid.UUID,
    review_id: uuid.UUID,
    data: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    review = await get_review_by_id(db, review_id)
    if not review or review.product_id != product_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your review")

    updated = await update_review(db, review_id, data)

    product = await get_product_by_id(db, product_id, load_relations=False)
    if product:
        await cache_delete(f"products:slug:{product.slug}")
        await _reindex_product(db, product_id)

    return updated


@product_reviews_router.delete("/{product_id}/reviews/{review_id}", response_model=MessageResponse, summary="Delete a review (owner or admin)")
async def delete_product_review(
    product_id: uuid.UUID,
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    review = await get_review_by_id(db, review_id)
    if not review or review.product_id != product_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if current_user.role != "admin" and review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your review")

    product = await get_product_by_id(db, product_id, load_relations=False)
    await delete_review(db, review_id)

    if product:
        await cache_delete(f"products:slug:{product.slug}")
        await _reindex_product(db, product_id)

    return MessageResponse(message="Review deleted")


@reviews_router.post("/{review_id}/helpful", response_model=MessageResponse, summary="Mark a review as helpful")
async def mark_helpful(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    review = await get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if review.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark your own review as helpful",
        )
    await increment_helpful(db, review_id)
    return MessageResponse(message="Marked as helpful")
