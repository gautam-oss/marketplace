import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]]
    image_url: Mapped[Optional[str]]
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    parent: Mapped[Optional["Category"]] = relationship(
        back_populates="children",
        remote_side="Category.id",
        foreign_keys="[Category.parent_id]",
    )
    children: Mapped[list["Category"]] = relationship(
        back_populates="parent",
        foreign_keys="[Category.parent_id]",
    )
    products: Mapped[list["Product"]] = relationship(back_populates="category")
