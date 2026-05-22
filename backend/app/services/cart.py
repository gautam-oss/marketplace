import uuid
from decimal import Decimal

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.product import get_products_by_ids
from app.schemas.cart import CartItem, CartResponse
from app.schemas.product import ProductListResponse

CART_TTL = 60 * 60 * 24 * 30  # 30 days


def _cart_key(user_id: uuid.UUID) -> str:
    return f"cart:{user_id}"


class CartService:
    @staticmethod
    async def get_cart(redis: aioredis.Redis, user_id: uuid.UUID, db: AsyncSession) -> CartResponse:
        raw = await redis.hgetall(_cart_key(user_id))
        if not raw:
            return CartResponse(items=[], total=Decimal("0"), item_count=0)

        products = await get_products_by_ids(db, list(raw.keys()))
        product_map = {str(p.id): p for p in products}

        items: list[CartItem] = []
        stale_keys: list[str] = []
        for pid_str, qty_str in raw.items():
            product = product_map.get(pid_str)
            if not product or product.status != "active" or product.stock == 0:
                stale_keys.append(pid_str)
                continue
            qty = int(qty_str)
            subtotal = product.price * qty
            items.append(CartItem(
                product_id=uuid.UUID(pid_str),
                quantity=qty,
                product=ProductListResponse.model_validate(product),
                subtotal=subtotal,
            ))

        if stale_keys:
            await redis.hdel(_cart_key(user_id), *stale_keys)

        total = sum(i.subtotal for i in items)
        return CartResponse(items=items, total=total, item_count=len(items))

    @staticmethod
    async def add_item(
        redis: aioredis.Redis,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
        db: AsyncSession,
    ) -> CartResponse:
        from app.crud.product import get_product_by_id

        product = await get_product_by_id(db, product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        if product.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not available")
        if product.seller_id == user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot buy your own product")

        current_qty = int(await redis.hget(_cart_key(user_id), str(product_id)) or 0)
        new_qty = min(current_qty + quantity, product.stock)
        await redis.hset(_cart_key(user_id), str(product_id), new_qty)
        await redis.expire(_cart_key(user_id), CART_TTL)
        return await CartService.get_cart(redis, user_id, db)

    @staticmethod
    async def update_item(
        redis: aioredis.Redis,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
        db: AsyncSession,
    ) -> CartResponse:
        if quantity == 0:
            await redis.hdel(_cart_key(user_id), str(product_id))
        else:
            from app.crud.product import get_product_by_id

            product = await get_product_by_id(db, product_id)
            if not product:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
            capped = min(quantity, product.stock)
            await redis.hset(_cart_key(user_id), str(product_id), capped)
        await redis.expire(_cart_key(user_id), CART_TTL)
        return await CartService.get_cart(redis, user_id, db)

    @staticmethod
    async def remove_item(
        redis: aioredis.Redis,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        db: AsyncSession,
    ) -> CartResponse:
        await redis.hdel(_cart_key(user_id), str(product_id))
        return await CartService.get_cart(redis, user_id, db)

    @staticmethod
    async def clear_cart(redis: aioredis.Redis, user_id: uuid.UUID) -> None:
        await redis.delete(_cart_key(user_id))
