import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.user import UserPublic


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    slug: str


class ReviewCreate(BaseModel):
    rating: int
    title: Optional[str] = None
    body: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    title: Optional[str] = None
    body: Optional[str] = None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rating: int
    title: Optional[str] = None
    body: Optional[str] = None
    is_verified_purchase: bool
    helpful_count: int
    user: UserPublic
    created_at: datetime


class RatingSummary(BaseModel):
    average: float
    total: int
    breakdown: dict[int, int]


class ReviewAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rating: int
    title: Optional[str] = None
    body: Optional[str] = None
    is_verified_purchase: bool
    helpful_count: int
    user: UserPublic
    product: Optional[ProductBrief] = None
    created_at: datetime
