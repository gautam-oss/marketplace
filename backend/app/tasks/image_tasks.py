from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_product_image(self, product_id: int, image_bytes_hex: str, content_type: str):
    import asyncio

    from app.services.storage import upload_image

    async def _upload():
        image_bytes = bytes.fromhex(image_bytes_hex)
        return await upload_image(image_bytes, content_type, folder="products")

    try:
        url = asyncio.run(_upload())
    except Exception as exc:
        raise self.retry(exc=exc)

    import asyncio

    from app.core.database import AsyncSessionLocal
    from app.crud.product import get_product

    async def _update_url():
        async with AsyncSessionLocal() as db:
            product = await get_product(db, product_id)
            if product:
                product.image_url = url
                await db.commit()

    asyncio.run(_update_url())
