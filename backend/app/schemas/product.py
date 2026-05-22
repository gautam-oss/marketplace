import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserPublic

if TYPE_CHECKING:
    from app.schemas.category import CategoryResponse


class ProductCreate(BaseModel):
    title: str = Field(min_length=3)
    description: Optional[str] = None
    price: Decimal = Field(gt=0)
    compare_at_price: Optional[Decimal] = Field(default=None, gt=0)
    stock: int = Field(ge=0)
    sku: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    tags: list[str] = []


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, gt=0)
    compare_at_price: Optional[Decimal] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)
    sku: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    images: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None


class ProductListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    price: Decimal
    compare_at_price: Optional[Decimal] = None
    stock: int
    status: str
    images: list[str] = []
    seller: UserPublic
    average_rating: float = 0.0
    review_count: int = 0


class ProductResponse(ProductListResponse):
    description: Optional[str] = None
    sku: Optional[str] = None
    tags: list[str] = []
    metadata_: dict = {}
    category: Optional["CategoryResponse"] = None
    created_at: datetime
    updated_at: datetime


# Resolve forward ref after CategoryResponse is importable
def _rebuild() -> None:
    from app.schemas.category import CategoryResponse  # noqa: F401
    ProductResponse.model_rebuild()


_rebuild()
