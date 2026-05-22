import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.core.websocket import manager as ws_manager

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_active_user, require_role
from app.core.redis import get_redis
from app.crud.order import (
    cancel_order,
    create_order,
    get_order_by_id,
    get_order_by_razorpay_id,
    list_orders_by_buyer,
    list_orders_by_seller,
    update_order_status,
)
from app.crud.product import get_product_by_id
from app.schemas.common import PaginatedResponse
from app.schemas.order import CheckoutResponse, OrderCreate, OrderListResponse, OrderResponse
from app.services.cart import CartService
from app.services.razorpay import issue_refund, razorpay_service, verify_webhook_signature

router = APIRouter(prefix="/orders", tags=["orders"])

GST_RATE = Decimal("0.18")
SHIPPING_COST = Decimal("50")
FREE_SHIPPING_THRESHOLD = Decimal("500")

VALID_TRANSITIONS = {
    "paid": "processing",
    "processing": "shipped",
    "shipped": "delivered",
}


class _StatusBody(BaseModel):
    status: str


@router.get("", response_model=PaginatedResponse[OrderListResponse], summary="List my orders (buyer sees own; seller sees orders for their products)")
async def list_my_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    if current_user.role == "seller":
        items, total = await list_orders_by_seller(db, current_user.id, page=page, per_page=per_page)
    else:
        items, total = await list_orders_by_buyer(db, current_user.id, page=page, per_page=per_page)

    pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        items=[OrderListResponse.model_validate(o) for o in items],
        total=total, page=page, per_page=per_page, pages=pages,
    )


@router.get("/{order_id}", response_model=OrderResponse, summary="Get order detail")
async def get_my_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    order = await get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if current_user.role != "admin" and order.buyer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
    return order


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED, summary="Create order and Razorpay payment from cart")
async def checkout(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    current_user=Depends(require_role("buyer")),
):
    order_items: list[dict] = []
    subtotal = Decimal("0")

    for item_req in data.items:
        product = await get_product_by_id(db, item_req.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item_req.product_id} not found",
            )
        if product.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {product.title} is not available",
            )
        if product.seller_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot purchase your own product",
            )
        if product.stock < item_req.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {product.title} (available: {product.stock})",
            )
        order_items.append({
            "product_id": item_req.product_id,
            "quantity": item_req.quantity,
            "unit_price": product.price,
            "product_title": product.title,
            "product_image": product.images[0] if product.images else None,
        })
        subtotal += product.price * item_req.quantity

    shipping_amount = Decimal("0") if subtotal > FREE_SHIPPING_THRESHOLD else SHIPPING_COST
    tax_amount = (subtotal * GST_RATE).quantize(Decimal("0.01"))
    total = subtotal + shipping_amount + tax_amount
    amount_paise = int(total * 100)

    rz_order = razorpay_service.create_order(amount_paise)

    # Decrement stock with SELECT FOR UPDATE to prevent race conditions
    from sqlalchemy import select as sa_select
    from app.models.product import Product as _Product
    for item_req in data.items:
        result = await db.execute(
            sa_select(_Product).where(_Product.id == item_req.product_id).with_for_update()
        )
        locked_product = result.scalar_one_or_none()
        if locked_product:
            locked_product.stock -= item_req.quantity
    await db.commit()

    shipping_dict = data.shipping_address.model_dump()
    order = await create_order(
        db,
        buyer_id=current_user.id,
        items_data=order_items,
        subtotal=subtotal,
        shipping_amount=shipping_amount,
        tax_amount=tax_amount,
        total=total,
        shipping_address=shipping_dict,
        notes=data.notes,
        razorpay_order_id=rz_order["id"],
    )

    await CartService.clear_cart(redis, current_user.id)

    return CheckoutResponse(
        order_id=order.id,
        razorpay_order_id=rz_order["id"],
        amount=amount_paise,
        razorpay_key_id=settings.RAZORPAY_KEY_ID,
    )


@router.post("/webhook", summary="Razorpay payment webhook (signature verified, no auth required)")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    payload = json.loads(body)
    event = payload.get("event")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    rz_order_id = payment_entity.get("order_id")

    if not rz_order_id:
        return {"status": "ignored"}

    order = await get_order_by_razorpay_id(db, rz_order_id)
    if not order:
        return {"status": "order_not_found"}

    if event == "payment.captured" and order.status == "pending":
        await update_order_status(
            db, order, "paid",
            payment_id=payment_entity.get("id"),
            paid_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        now_iso = datetime.now(timezone.utc).isoformat()
        short_id = str(order.id)[:8].upper()
        await ws_manager.send_to_user(str(order.buyer_id), {
            "type": "order.paid",
            "order_id": str(order.id),
            "message": f"Payment confirmed for order #{short_id}!",
            "timestamp": now_iso,
        })
        # Notify each seller whose products are in the order
        from app.models.product import Product as _Prod
        from sqlalchemy import select as _sel
        product_ids = [item.product_id for item in order.items if item.product_id]
        if product_ids:
            result = await db.execute(
                _sel(_Prod.seller_id).where(_Prod.id.in_(product_ids)).distinct()
            )
            for seller_id in result.scalars().all():
                await ws_manager.send_to_user(str(seller_id), {
                    "type": "order.placed",
                    "order_id": str(order.id),
                    "message": f"New order received! #{short_id}",
                    "timestamp": now_iso,
                })
        from app.tasks.email_tasks import send_order_confirmation_email
        send_order_confirmation_email.delay(str(order.id))

    elif event == "payment.failed" and order.status == "pending":
        await cancel_order(db, order)
        await ws_manager.send_to_user(str(order.buyer_id), {
            "type": "order.cancelled",
            "order_id": str(order.id),
            "message": f"Payment failed for order #{str(order.id)[:8].upper()}.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    return {"status": "ok"}


@router.patch("/{order_id}/status", response_model=OrderResponse, summary="Advance order status (seller or admin)")
async def update_status(
    order_id: uuid.UUID,
    body: _StatusBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    order = await get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    allowed_next = VALID_TRANSITIONS.get(order.status)
    if body.status != allowed_next:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {order.status!r} to {body.status!r}",
        )

    # Sellers can only advance orders that contain their products
    if current_user.role == "seller":
        seller_product_ids = {item.product_id for item in order.items}
        from app.models.product import Product
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(Product.id).where(
                Product.id.in_(seller_product_ids),
                Product.seller_id == current_user.id,
            )
        )
        if not result.scalars().first():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
    elif current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    kwargs = {}
    if body.status == "shipped":
        kwargs["shipped_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        from app.tasks.email_tasks import send_shipping_notification_email
        send_shipping_notification_email.delay(str(order.id))
    elif body.status == "delivered":
        kwargs["delivered_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

    updated = await update_order_status(db, order, body.status, **kwargs)

    status_messages = {
        "processing": "Your order is being processed.",
        "shipped": "Your order has shipped!",
        "delivered": "Your order has been delivered!",
    }
    await ws_manager.send_to_user(str(order.buyer_id), {
        "type": "order.status_changed",
        "order_id": str(order.id),
        "status": body.status,
        "message": status_messages.get(body.status, f"Order status updated to {body.status}."),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return updated


@router.post("/{order_id}/cancel", response_model=OrderResponse, summary="Cancel a pending order")
async def cancel_my_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    order = await get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if current_user.role != "admin" and order.buyer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")

    # Buyers can only cancel pending orders; admins can cancel anything non-delivered
    if current_user.role != "admin" and order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order in status {order.status!r}",
        )
    if order.status == "delivered":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivered orders cannot be cancelled",
        )

    if order.razorpay_payment_id:
        try:
            amount_paise = int(order.total * 100)
            issue_refund(order.razorpay_payment_id, amount_paise)
        except Exception:
            pass
        order = await update_order_status(db, order, "refunded")
    else:
        order = await cancel_order(db, order)

    await ws_manager.send_to_user(str(order.buyer_id), {
        "type": "order.cancelled",
        "order_id": str(order.id),
        "message": f"Order #{str(order.id)[:8].upper()} has been cancelled.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return order
