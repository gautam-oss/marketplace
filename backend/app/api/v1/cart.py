import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.redis import get_redis
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse
from app.schemas.common import MessageResponse
from app.services.cart import CartService

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartResponse)
async def get_cart(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    return await CartService.get_cart(redis, current_user.id, db)


@router.post("/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    data: CartItemAdd,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    return await CartService.add_item(redis, current_user.id, data.product_id, data.quantity, db)


@router.put("/items/{product_id}", response_model=CartResponse)
async def update_cart_item(
    product_id: uuid.UUID,
    data: CartItemUpdate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    return await CartService.update_item(redis, current_user.id, product_id, data.quantity, db)


@router.delete("/items/{product_id}", response_model=CartResponse)
async def remove_from_cart(
    product_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    return await CartService.remove_item(redis, current_user.id, product_id, db)


@router.delete("", response_model=MessageResponse)
async def clear_cart(
    current_user=Depends(get_current_active_user),
    redis=Depends(get_redis),
):
    await CartService.clear_cart(redis, current_user.id)
    return MessageResponse(message="Cart cleared")
