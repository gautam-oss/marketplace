import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")


async def get_category_by_id(db: AsyncSession, cat_id: uuid.UUID) -> Category | None:
    result = await db.execute(
        select(Category).options(selectinload(Category.children)).where(Category.id == cat_id)
    )
    return result.scalar_one_or_none()


async def get_category_by_slug(db: AsyncSession, slug: str) -> Category | None:
    result = await db.execute(
        select(Category).options(selectinload(Category.children)).where(Category.slug == slug)
    )
    return result.scalar_one_or_none()


async def get_root_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.children))
        .where(Category.parent_id.is_(None))
        .order_by(Category.sort_order)
    )
    return list(result.scalars().all())


async def get_all_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(
        select(Category).options(selectinload(Category.children)).order_by(Category.sort_order)
    )
    return list(result.scalars().all())


async def create_category(db: AsyncSession, data: CategoryCreate) -> Category:
    slug = data.slug or _slugify(data.name)
    category = Category(
        name=data.name,
        slug=slug,
        description=data.description,
        image_url=data.image_url,
        parent_id=data.parent_id,
        sort_order=data.sort_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(db: AsyncSession, cat_id: uuid.UUID, data: CategoryUpdate) -> Category | None:
    category = await get_category_by_id(db, cat_id)
    if not category:
        return None
    updates = data.model_dump(exclude_unset=True)
    if "name" in updates and "slug" not in updates:
        updates["slug"] = _slugify(updates["name"])
    for field, value in updates.items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, cat_id: uuid.UUID) -> bool:
    category = await get_category_by_id(db, cat_id)
    if not category:
        return False
    await db.delete(category)
    await db.commit()
    return True
