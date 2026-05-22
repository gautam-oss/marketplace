"""add_performance_indexes

Revision ID: 751b123db5f1
Revises: 47f2dc0b571e
Create Date: 2026-05-22 07:41:19.263296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '751b123db5f1'
down_revision: Union[str, None] = '47f2dc0b571e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # products: filter by status (active/draft/archived) — most common query predicate
    op.create_index('ix_products_status', 'products', ['status'])
    # products: compound index for the common "list active products sorted by date" query
    op.create_index('ix_products_status_created_at', 'products', ['status', 'created_at'])
    # orders: filter by status for admin/seller dashboards
    op.create_index('ix_orders_status', 'orders', ['status'])
    # orders: date range queries for revenue stats
    op.create_index('ix_orders_paid_at', 'orders', ['paid_at'])
    # orders: created_at for ordering and date-range filtering
    op.create_index('ix_orders_created_at', 'orders', ['created_at'])
    # users: role filter for admin user list / stats query
    op.create_index('ix_users_role', 'users', ['role'])
    # users: new users this week query
    op.create_index('ix_users_created_at', 'users', ['created_at'])
    # reviews: sort by created_at within a product
    op.create_index('ix_reviews_created_at', 'reviews', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_reviews_created_at', table_name='reviews')
    op.drop_index('ix_users_created_at', table_name='users')
    op.drop_index('ix_users_role', table_name='users')
    op.drop_index('ix_orders_created_at', table_name='orders')
    op.drop_index('ix_orders_paid_at', table_name='orders')
    op.drop_index('ix_orders_status', table_name='orders')
    op.drop_index('ix_products_status_created_at', table_name='products')
    op.drop_index('ix_products_status', table_name='products')
