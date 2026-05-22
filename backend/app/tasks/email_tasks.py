import resend

from app.core.config import settings
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation_email(self, order_id: int):
    import asyncio

    from app.core.database import AsyncSessionLocal
    from app.crud.order import get_order

    async def _fetch_order():
        async with AsyncSessionLocal() as db:
            return await get_order(db, order_id)

    order = asyncio.run(_fetch_order())
    if not order:
        return

    async def _fetch_user():
        from app.core.database import AsyncSessionLocal
        from app.crud.user import get_user_by_id

        async with AsyncSessionLocal() as db:
            return await get_user_by_id(db, order.buyer_id)

    user = asyncio.run(_fetch_user())
    if not user:
        return

    resend.api_key = settings.RESEND_API_KEY

    html_body = f"""
    <h2>Order Confirmed! #{str(order.id).zfill(8).upper()}</h2>
    <p>Hi {user.full_name},</p>
    <p>Your order has been confirmed and payment received.</p>
    <table>
      <tr><td><strong>Order ID:</strong></td><td>#{order.id}</td></tr>
      <tr><td><strong>Total:</strong></td><td>₹{order.total}</td></tr>
      <tr><td><strong>Status:</strong></td><td>{order.status.upper()}</td></tr>
    </table>
    <p>Thank you for shopping with us!</p>
    """

    try:
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [user.email],
            "subject": f"Order Confirmed! #{str(order.id).zfill(8).upper()}",
            "html": html_body,
        })
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_shipping_notification_email(self, order_id: str):
    import asyncio

    from app.core.database import AsyncSessionLocal
    from app.crud.order import get_order
    from app.crud.user import get_user_by_id

    async def _fetch():
        async with AsyncSessionLocal() as db:
            order = await get_order(db, order_id)
            if not order:
                return None, None
            user = await get_user_by_id(db, order.buyer_id)
            return order, user

    order, user = asyncio.run(_fetch())
    if not order or not user:
        return

    resend.api_key = settings.RESEND_API_KEY

    try:
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [user.email],
            "subject": f"Your order #{str(order.id)[:8].upper()} has shipped!",
            "html": (
                f"<h2>Order Shipped!</h2>"
                f"<p>Hi {user.full_name}, your order is on its way.</p>"
                f"<p>Order ID: #{str(order.id)[:8].upper()}</p>"
            ),
        })
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email(self, user_id: int):
    import asyncio

    from app.core.database import AsyncSessionLocal
    from app.crud.user import get_user_by_id

    async def _fetch():
        async with AsyncSessionLocal() as db:
            return await get_user_by_id(db, user_id)

    user = asyncio.run(_fetch())
    if not user:
        return

    resend.api_key = settings.RESEND_API_KEY

    try:
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [user.email],
            "subject": "Welcome to Marketplace!",
            "html": f"<h2>Welcome, {user.full_name}!</h2><p>Thanks for joining the marketplace.</p>",
        })
    except Exception as exc:
        raise self.retry(exc=exc)
