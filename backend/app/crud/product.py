import re
import uuid
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")


async def _unique_slug(db: AsyncSession, base_slug: str) -> str:
    slug = base_slug
    counter = 2
    while True:
        result = await db.execute(select(Product).where(Product.slug == slug))
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


async def get_product_by_id(
    db: AsyncSession, product_id: uuid.UUID, load_relations: bool = True
) -> Product | None:
    query = select(Product).where(Product.id == product_id)
    if load_relations:
        query = query.options(
            selectinload(Product.seller),
            selectinload(Product.category).selectinload(Category.children),
            selectinload(Product.reviews),
        )
    result = await db.execute(query)
    return result.scalar_one_or_none()


# Alias used by cart service and other code
get_product = get_product_by_id


async def get_product_by_slug(db: AsyncSession, slug: str) -> Product | None:
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.seller),
            selectinload(Product.category).selectinload(Category.children),
            selectinload(Product.reviews),
        )
        .where(Product.slug == slug)
    )
    return result.scalar_one_or_none()


async def get_products_by_ids(db: AsyncSession, ids: list[str]) -> list[Product]:
    if not ids:
        return []
    uuids = [uuid.UUID(i) for i in ids]
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.seller),
            selectinload(Product.category).selectinload(Category.children),
        )
        .where(Product.id.in_(uuids))
    )
    return list(result.scalars().all())


async def list_products(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    category_id: uuid.UUID | None = None,
    seller_id: uuid.UUID | None = None,
    status: str | None = "active",
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[Product], int]:
    query = select(Product).options(
        selectinload(Product.seller),
        selectinload(Product.category).selectinload(Category.children),
    )
    if status is not None:
        query = query.where(Product.status == status)
    if category_id:
        query = query.where(Product.category_id == category_id)
    if seller_id:
        query = query.where(Product.seller_id == seller_id)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)

    col = getattr(Product, sort_by, Product.created_at)
    query = query.order_by(col.desc() if sort_order == "desc" else col.asc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()
    items = (await db.execute(query.offset((page - 1) * per_page).limit(per_page))).scalars().all()
    return list(items), total


async def create_product(
    db: AsyncSession,
    schema: ProductCreate,
    seller_id: uuid.UUID,
    images: list[str] | None = None,
) -> Product:
    base_slug = _slugify(schema.title)
    slug = await _unique_slug(db, base_slug)
    product = Product(
        seller_id=seller_id,
        category_id=schema.category_id,
        title=schema.title,
        slug=slug,
        description=schema.description,
        price=schema.price,
        compare_at_price=schema.compare_at_price,
        stock=schema.stock,
        sku=schema.sku,
        images=images or [],
        tags=schema.tags,
        status="draft",
    )
    db.add(product)
    await db.commit()
    return await get_product_by_id(db, product.id)


async def update_product(db: AsyncSession, product_id: uuid.UUID, schema: ProductUpdate) -> Product | None:
    product = await get_product_by_id(db, product_id)
    if not product:
        return None
    updates = schema.model_dump(exclude_unset=True)
    if "title" in updates:
        updates["slug"] = await _unique_slug(db, _slugify(updates["title"]))
    for field, value in updates.items():
        setattr(product, field, value)
    await db.commit()
    return await get_product_by_id(db, product.id)


async def update_product_images(db: AsyncSession, product_id: uuid.UUID, images: list[str]) -> Product | None:
    product = await get_product_by_id(db, product_id)
    if not product:
        return None
    product.images = images
    await db.commit()
    return await get_product_by_id(db, product.id)


async def update_product_stock(db: AsyncSession, product_id: uuid.UUID, delta: int) -> Product | None:
    """Atomically adjust stock by delta (positive = add, negative = subtract)."""
    await db.execute(
        update(Product)
        .where(Product.id == product_id)
        .values(stock=Product.stock + delta)
    )
    await db.commit()
    return await get_product_by_id(db, product_id)


async def soft_delete_product(db: AsyncSession, product_id: uuid.UUID) -> Product | None:
    product = await get_product_by_id(db, product_id)
    if not product:
        return None
    product.status = "archived"
    await db.commit()
    return await get_product_by_id(db, product.id)


# Legacy alias used by existing API routes
async def delete_product(db: AsyncSession, product: Product) -> None:
    await soft_delete_product(db, product.id)
