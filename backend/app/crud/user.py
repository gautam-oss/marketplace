import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate, role: str = "buyer") -> User:
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    updates = data.model_dump(exclude_unset=True)
    if "password" in updates:
        updates["hashed_password"] = hash_password(updates.pop("password"))
    for field, value in updates.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    user = await get_user_by_id(db, user_id)
    if user:
        user.is_active = False
        await db.commit()
        await db.refresh(user)
    return user


async def list_users(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    role: str | None = None,
    q: str | None = None,
) -> tuple[list[User], int]:
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if q:
        pattern = f"%{q}%"
        query = query.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()
    items = (
        await db.execute(query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page))
    ).scalars().all()
    return list(items), total
