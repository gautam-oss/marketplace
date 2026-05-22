import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.schemas.user import UserPublic


class ShippingAddress(BaseModel):
    full_name: str
    phone: str
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    pincode: str
    country: str = "India"

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 6:
            raise ValueError("Pincode must be exactly 6 digits")
        return v


class OrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=100)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1)
    shipping_address: ShippingAddress
    notes: Optional[str] = None


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    product_title: str
    product_image: Optional[str] = None
    quantity: int
    unit_price: Decimal

    @computed_field  # type: ignore[misc]
    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    subtotal: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total: Decimal
    shipping_address: dict
    notes: Optional[str] = None
    items: list[OrderItemResponse]
    buyer: UserPublic
    created_at: datetime
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


class OrderListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    total: Decimal
    items: list[OrderItemResponse]
    created_at: datetime


class CheckoutResponse(BaseModel):
    order_id: uuid.UUID
    razorpay_order_id: str
    amount: int  # paise (INR × 100)
    currency: str = "INR"
    razorpay_key_id: str
