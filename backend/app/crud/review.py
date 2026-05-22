import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import Review
from app.schemas.review import ReviewCreate, ReviewUpdate


async def get_review_by_id(db: AsyncSession, review_id: uuid.UUID) -> Review | None:
    result = await db.execute(
        select(Review).options(selectinload(Review.user)).where(Review.id == review_id)
    )
    return result.scalar_one_or_none()


async def get_review_by_user_product(
    db: AsyncSession, user_id: uuid.UUID, product_id: uuid.UUID
) -> Review | None:
    result = await db.execute(
        select(Review).where(Review.user_id == user_id, Review.product_id == product_id)
    )
    return result.scalar_one_or_none()


async def list_reviews_by_product(
    db: AsyncSession,
    product_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    sort: str = "recent",
) -> tuple[list[Review], int]:
    query = select(Review).options(selectinload(Review.user)).where(Review.product_id == product_id)

    if sort == "rating_high":
        query = query.order_by(Review.rating.desc())
    elif sort == "rating_low":
        query = query.order_by(Review.rating.asc())
    elif sort == "helpful":
        query = query.order_by(Review.helpful_count.desc())
    else:
        query = query.order_by(Review.created_at.desc())

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    items = (await db.execute(query.offset((page - 1) * per_page).limit(per_page))).scalars().all()
    return list(items), total


async def get_rating_summary(db: AsyncSession, product_id: uuid.UUID) -> dict:
    rows = (
        await db.execute(
            select(Review.rating, func.count(Review.id))
            .where(Review.product_id == product_id)
            .group_by(Review.rating)
        )
    ).all()

    breakdown: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total = 0
    total_rating = 0
    for rating, count in rows:
        breakdown[rating] = count
        total += count
        total_rating += rating * count

    average = round(total_rating / total, 2) if total else 0.0
    return {"average": average, "total": total, "breakdown": breakdown}


async def create_review(
    db: AsyncSession,
    schema: ReviewCreate,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
    is_verified_purchase: bool = False,
) -> Review:
    review = Review(
        user_id=user_id,
        product_id=product_id,
        rating=schema.rating,
        title=schema.title,
        body=schema.body,
        is_verified_purchase=is_verified_purchase,
    )
    db.add(review)
    await db.commit()
    return await get_review_by_id(db, review.id)


async def update_review(db: AsyncSession, review_id: uuid.UUID, schema: ReviewUpdate) -> Review | None:
    review = await get_review_by_id(db, review_id)
    if not review:
        return None
    for field, value in schema.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    await db.commit()
    return await get_review_by_id(db, review_id)


async def delete_review(db: AsyncSession, review_id: uuid.UUID) -> bool:
    review = await get_review_by_id(db, review_id)
    if not review:
        return False
    await db.delete(review)
    await db.commit()
    return True


async def increment_helpful(db: AsyncSession, review_id: uuid.UUID) -> Review | None:
    await db.execute(
        update(Review).where(Review.id == review_id).values(helpful_count=Review.helpful_count + 1)
    )
    await db.commit()
    return await get_review_by_id(db, review_id)
