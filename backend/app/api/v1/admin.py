import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_role
from app.core.redis import cache_delete, cache_delete_pattern
from app.crud.product import get_product_by_id, list_products, update_product
from app.crud.review import delete_review, get_review_by_id
from app.crud.user import get_user_by_id, list_users
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.order import OrderListResponse, OrderResponse
from app.schemas.product import ProductResponse, ProductUpdate
from app.schemas.user import UserResponse
from app.services.search import ElasticsearchService, get_es_client

router = APIRouter(prefix="/admin", tags=["admin"])


class _UserAdminUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class _StatusBody(BaseModel):
    status: str


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=PaginatedResponse[UserResponse],
            dependencies=[Depends(require_role("admin"))])
async def admin_list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_users(db, page=page, per_page=per_page, role=role, q=q)
    pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in items],
        total=total, page=page, per_page=per_page, pages=pages,
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: uuid.UUID,
    data: _UserAdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    if data.role is not None and user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


# ── Products ──────────────────────────────────────────────────────────────────

@router.get("/products", response_model=PaginatedResponse[ProductResponse],
            dependencies=[Depends(require_role("admin"))])
async def admin_list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    seller_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_products(
        db, page=page, per_page=per_page,
        status=status_filter,   # None → no filter → all statuses
        seller_id=seller_id,
    )
    pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total, page=page, per_page=per_page, pages=pages,
    )


@router.patch("/products/{product_id}/status", response_model=ProductResponse,
              dependencies=[Depends(require_role("admin"))])
async def admin_update_product_status(
    product_id: uuid.UUID,
    data: _StatusBody,
    db: AsyncSession = Depends(get_db),
):
    product = await get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    old_slug = product.slug
    updated = await update_product(db, product_id, ProductUpdate(status=data.status))
    try:
        await ElasticsearchService.index_product(get_es_client(), updated)
    except Exception:
        pass
    await cache_delete_pattern("products:list:*")
    await cache_delete(f"products:slug:{old_slug}")
    return updated


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=PaginatedResponse[OrderResponse],
            dependencies=[Depends(require_role("admin"))])
async def admin_list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    buyer_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Order).options(
        selectinload(Order.buyer),
        selectinload(Order.items).selectinload(OrderItem.product),
    )
    if status_filter:
        query = query.where(Order.status == status_filter)
    if buyer_id:
        query = query.where(Order.buyer_id == buyer_id)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    items = (
        await db.execute(
            query.order_by(Order.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()
    pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        items=[OrderResponse.model_validate(o) for o in items],
        total=total, page=page, per_page=per_page, pages=pages,
    )


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats", dependencies=[Depends(require_role("admin"))])
async def admin_stats(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 1:
        start_of_last_month = start_of_month.replace(year=now.year - 1, month=12)
    else:
        start_of_last_month = start_of_month.replace(month=now.month - 1)
    week_ago = now - timedelta(days=7)

    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    total_sellers = (await db.execute(
        select(func.count(User.id)).where(User.role == "seller")
    )).scalar_one()
    total_buyers = (await db.execute(
        select(func.count(User.id)).where(User.role == "buyer")
    )).scalar_one()
    new_users_this_week = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )).scalar_one()

    total_products = (await db.execute(select(func.count(Product.id)))).scalar_one()
    active_products = (await db.execute(
        select(func.count(Product.id)).where(Product.status == "active")
    )).scalar_one()

    total_orders = (await db.execute(select(func.count(Order.id)))).scalar_one()
    status_rows = (await db.execute(
        select(Order.status, func.count(Order.id)).group_by(Order.status)
    )).all()
    orders_by_status = {
        s: 0 for s in ("pending", "paid", "processing", "shipped", "delivered", "cancelled", "refunded")
    }
    for s, cnt in status_rows:
        orders_by_status[s] = cnt

    def _rev_q(start, end):
        return select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.status == "paid",
            Order.paid_at >= start,
            Order.paid_at < end,
        )

    revenue_this_month = float(
        (await db.execute(_rev_q(start_of_month, now + timedelta(days=1)))).scalar_one()
    )
    revenue_last_month = float(
        (await db.execute(_rev_q(start_of_last_month, start_of_month))).scalar_one()
    )

    return {
        "total_users": total_users,
        "total_sellers": total_sellers,
        "total_buyers": total_buyers,
        "total_products": total_products,
        "active_products": active_products,
        "total_orders": total_orders,
        "orders_by_status": orders_by_status,
        "revenue_this_month": revenue_this_month,
        "revenue_last_month": revenue_last_month,
        "new_users_this_week": new_users_this_week,
    }


# ── Reviews ───────────────────────────────────────────────────────────────────

@router.delete("/reviews/{review_id}", response_model=MessageResponse,
               dependencies=[Depends(require_role("admin"))])
async def admin_delete_review(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    review = await get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    product = await get_product_by_id(db, review.product_id, load_relations=False)
    await delete_review(db, review_id)

    if product:
        await cache_delete(f"products:slug:{product.slug}")
        try:
            product_full = await get_product_by_id(db, product.id)
            if product_full:
                await ElasticsearchService.index_product(get_es_client(), product_full)
        except Exception:
            pass

    return MessageResponse(message="Review deleted")
