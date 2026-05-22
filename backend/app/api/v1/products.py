import hashlib
import json
import uuid
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_role
from app.core.redis import cache_delete, cache_delete_pattern, cache_get, cache_set
from app.crud.category import get_category_by_slug
from app.crud.product import (
    create_product,
    get_product_by_id,
    get_product_by_slug,
    get_products_by_ids,
    list_products,
    soft_delete_product,
    update_product,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.product import ProductCreate, ProductListResponse, ProductResponse, ProductUpdate
from app.services.search import ElasticsearchService, get_es_client
from app.services.storage import upload_image

router = APIRouter(prefix="/products", tags=["products"])

MAX_IMAGES = 5
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

_SORT_BY = {"newest": "created_at", "price_asc": "price", "price_desc": "price", "rating": "created_at"}
_SORT_ORDER = {"newest": "desc", "price_asc": "asc", "price_desc": "desc", "rating": "desc"}


class _StatusBody(BaseModel):
    status: str


def _list_cache_key(page, per_page, category, seller_id, min_price, max_price, sort, q) -> str:
    raw = f"{page}:{per_page}:{category}:{seller_id}:{min_price}:{max_price}:{sort}:{q}"
    return "products:list:" + hashlib.md5(raw.encode()).hexdigest()


async def _reindex(product) -> None:
    try:
        await ElasticsearchService.index_product(get_es_client(), product)
    except Exception:
        pass  # ES unavailable is non-fatal


async def _invalidate_product_cache(slug: str) -> None:
    await cache_delete(f"products:slug:{slug}")
    await cache_delete_pattern("products:list:*")


@router.get("/my", response_model=PaginatedResponse[ProductListResponse], summary="List the seller's own products")
async def get_my_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("seller", "admin")),
):
    products, total = await list_products(
        db, page=page, per_page=per_page, seller_id=current_user.id
    )
    pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        items=[ProductListResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("", response_model=PaginatedResponse[ProductListResponse], summary="List active products with filtering and search")
async def get_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: str | None = None,
    seller_id: uuid.UUID | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc|rating)$"),
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    cache_key = _list_cache_key(page, per_page, category, seller_id, min_price, max_price, sort, q)
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    products: list
    total: int

    if q:
        try:
            es = get_es_client()
            hits, total = await ElasticsearchService.search(
                es,
                q=q,
                category=category,
                min_price=float(min_price) if min_price is not None else None,
                max_price=float(max_price) if max_price is not None else None,
                sort=sort,
                page=page,
                per_page=per_page,
            )
            product_ids = [h["id"] for h in hits]
            products_db = await get_products_by_ids(db, product_ids)
            product_map = {str(p.id): p for p in products_db}
            products = [product_map[pid] for pid in product_ids if pid in product_map]
        except Exception:
            products, total = await list_products(db, page=page, per_page=per_page, status="active")
    else:
        category_id = None
        if category:
            cat = await get_category_by_slug(db, category)
            category_id = cat.id if cat else None

        products, total = await list_products(
            db,
            page=page,
            per_page=per_page,
            category_id=category_id,
            seller_id=seller_id,
            status="active",
            min_price=min_price,
            max_price=max_price,
            sort_by=_SORT_BY.get(sort, "created_at"),
            sort_order=_SORT_ORDER.get(sort, "desc"),
        )

    pages = (total + per_page - 1) // per_page
    response = PaginatedResponse(
        items=[ProductListResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
    await cache_set(cache_key, response.model_dump_json(), ttl=120)
    return response


@router.get("/{slug}", response_model=ProductResponse, summary="Get product detail by slug")
async def get_product(slug: str, db: AsyncSession = Depends(get_db)):
    cache_key = f"products:slug:{slug}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    product = await get_product_by_slug(db, slug)
    if not product or product.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    response = ProductResponse.model_validate(product)
    reviews = getattr(product, "reviews", []) or []
    response.average_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 0.0
    response.review_count = len(reviews)

    await cache_set(cache_key, response.model_dump_json(), ttl=300)
    return response


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, summary="Create a new product (sellers only)")
async def create_new_product(
    title: Annotated[str, Form(min_length=3)],
    price: Annotated[Decimal, Form(gt=0)],
    stock: Annotated[int, Form(ge=0)],
    description: Annotated[Optional[str], Form()] = None,
    compare_at_price: Annotated[Optional[Decimal], Form()] = None,
    sku: Annotated[Optional[str], Form()] = None,
    category_id: Annotated[Optional[uuid.UUID], Form()] = None,
    tags: Annotated[Optional[str], Form()] = None,
    images: list[UploadFile] = File(default=[]),
    current_user=Depends(require_role("seller", "admin")),
    db: AsyncSession = Depends(get_db),
):
    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGES} images allowed")

    for img_file in images:
        if img_file.filename:
            content = await img_file.read()
            if len(content) > MAX_IMAGE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image '{img_file.filename}' exceeds the 5 MB limit",
                )
            await img_file.seek(0)

    # Parse tags: accept JSON array string or comma-separated
    parsed_tags: list[str] = []
    if tags:
        try:
            parsed_tags = json.loads(tags)
        except Exception:
            parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

    schema = ProductCreate(
        title=title,
        description=description,
        price=price,
        compare_at_price=compare_at_price,
        stock=stock,
        sku=sku,
        category_id=category_id,
        tags=parsed_tags,
    )

    image_urls: list[str] = []
    for img_file in images:
        if img_file.filename:
            url = await upload_image(img_file, folder="products")
            image_urls.append(url)

    product = await create_product(db, schema, seller_id=current_user.id, images=image_urls)
    await _reindex(product)
    await cache_delete_pattern("products:list:*")
    return product


@router.put("/{product_id}", response_model=ProductResponse, summary="Update product details")
async def update_existing_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    product = await get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if current_user.role == "seller" and product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your product")

    updated = await update_product(db, product_id, data)
    await _reindex(updated)
    await _invalidate_product_cache(updated.slug)
    return updated


@router.patch("/{product_id}/status", response_model=ProductResponse, summary="Change product status (draft / active / archived)")
async def update_product_status(
    product_id: uuid.UUID,
    data: _StatusBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    if current_user.role not in ("seller", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sellers or admins only")

    product = await get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if current_user.role == "seller" and product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your product")

    if data.status == "active":
        if product.stock == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stock must be greater than 0 to activate product",
            )
        if product.category_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category must be set to activate product",
            )

    updated = await update_product(db, product_id, ProductUpdate(status=data.status))
    await _reindex(updated)
    await _invalidate_product_cache(updated.slug)
    return updated


@router.delete("/{product_id}", response_model=MessageResponse, summary="Soft-delete a product")
async def delete_existing_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    product = await get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if current_user.role == "seller" and product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your product")

    slug = product.slug
    await soft_delete_product(db, product_id)

    try:
        await ElasticsearchService.remove_product(get_es_client(), str(product_id))
    except Exception:
        pass

    await _invalidate_product_cache(slug)
    return MessageResponse(message="Product deleted")
