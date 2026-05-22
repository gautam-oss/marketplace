import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.product import ProductListResponse


class CartItemAdd(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=99)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=0, le=99)  # 0 = remove


class CartItem(BaseModel):
    product_id: uuid.UUID
    quantity: int
    product: ProductListResponse
    subtotal: Decimal


class CartResponse(BaseModel):
    items: list[CartItem]
    total: Decimal
    item_count: int
