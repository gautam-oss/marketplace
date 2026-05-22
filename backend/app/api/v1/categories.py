import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_role
from app.core.redis import cache_delete, cache_get, cache_set
from app.crud.category import (
    create_category,
    delete_category,
    get_all_categories,
    get_category_by_id,
    get_category_by_slug,
    update_category,
)
from app.models.product import Product
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/categories", tags=["categories"])

_CACHE_KEY = "categories:tree"
_CACHE_TTL = 3600


@router.get("", response_model=list[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    cached = await cache_get(_CACHE_KEY)
    if cached:
        return json.loads(cached)

    categories = await get_all_categories(db)
    validated = [CategoryResponse.model_validate(c) for c in categories]
    await cache_set(
        _CACHE_KEY,
        json.dumps([c.model_dump(mode="json") for c in validated]),
        ttl=_CACHE_TTL,
    )
    return validated


@router.get("/{slug}", response_model=CategoryResponse)
async def get_category_by_slug_route(slug: str, db: AsyncSession = Depends(get_db)):
    category = await get_category_by_slug(db, slug)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
)
async def create_new_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    category = await create_category(db, data)
    await cache_delete(_CACHE_KEY)
    return await get_category_by_id(db, category.id)


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def update_existing_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    category = await update_category(db, category_id, data)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    await cache_delete(_CACHE_KEY)
    return category


@router.delete(
    "/{category_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def delete_existing_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product)
        .where(Product.category_id == category_id, Product.status == "active")
        .limit(1)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category has active products. Archive or reassign them first.",
        )

    deleted = await delete_category(db, category_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    await cache_delete(_CACHE_KEY)
    return MessageResponse(message="Category deleted")
