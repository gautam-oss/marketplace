import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem


async def get_order_by_id(
    db: AsyncSession, order_id: uuid.UUID, load_relations: bool = True
) -> Order | None:
    query = select(Order).where(Order.id == order_id)
    if load_relations:
        query = query.options(
            selectinload(Order.buyer),
            selectinload(Order.items).selectinload(OrderItem.product),
        )
    result = await db.execute(query)
    return result.scalar_one_or_none()


# Alias
get_order = get_order_by_id


async def get_order_by_razorpay_id(db: AsyncSession, razorpay_order_id: str) -> Order | None:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.buyer), selectinload(Order.items))
        .where(Order.razorpay_order_id == razorpay_order_id)
    )
    return result.scalar_one_or_none()


async def list_orders_by_buyer(
    db: AsyncSession,
    buyer_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    status: str | None = None,
) -> tuple[list[Order], int]:
    query = select(Order).where(Order.buyer_id == buyer_id)
    if status:
        query = query.where(Order.status == status)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    items = (
        await db.execute(
            query.options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()
    return list(items), total


async def list_orders_by_seller(
    db: AsyncSession,
    seller_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Order], int]:
    from app.models.product import Product

    # Subquery returns distinct order IDs that contain the seller's products
    id_subquery = (
        select(Order.id)
        .join(Order.items)
        .join(OrderItem.product)
        .where(Product.seller_id == seller_id)
        .distinct()
        .subquery()
    )
    base = select(Order).where(Order.id.in_(select(id_subquery.c.id)))
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = (
        await db.execute(
            base.options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()
    return list(items), total


async def create_order(
    db: AsyncSession,
    buyer_id: uuid.UUID,
    items_data: list[dict],
    subtotal: Decimal,
    shipping_amount: Decimal,
    tax_amount: Decimal,
    total: Decimal,
    shipping_address: dict,
    notes: Optional[str] = None,
    razorpay_order_id: Optional[str] = None,
) -> Order:
    order = Order(
        buyer_id=buyer_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_amount=shipping_amount,
        total=total,
        razorpay_order_id=razorpay_order_id,
        shipping_address=shipping_address,
        notes=notes,
        status="pending",
    )
    db.add(order)
    await db.flush()

    for item in items_data:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item["product_id"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            product_title=item["product_title"],
            product_image=item.get("product_image"),
        ))

    await db.commit()
    return await get_order_by_id(db, order.id)


async def update_order_status(
    db: AsyncSession,
    order: Order,
    status: str,
    payment_id: str | None = None,
    paid_at: Optional[datetime] = None,
    shipped_at: Optional[datetime] = None,
    delivered_at: Optional[datetime] = None,
) -> Order:
    order.status = status
    if payment_id:
        order.razorpay_payment_id = payment_id
    if paid_at:
        order.paid_at = paid_at
    if shipped_at:
        order.shipped_at = shipped_at
    if delivered_at:
        order.delivered_at = delivered_at
    await db.commit()
    await db.refresh(order)
    return order


async def set_razorpay_payment_id(db: AsyncSession, order: Order, payment_id: str) -> Order:
    order.razorpay_payment_id = payment_id
    await db.commit()
    await db.refresh(order)
    return order


async def cancel_order(db: AsyncSession, order: Order) -> Order:
    from app.crud.product import update_product_stock

    order.status = "cancelled"
    await db.commit()
    for item in order.items:
        if item.product_id:
            await update_product_stock(db, item.product_id, delta=item.quantity)
    return order
