import io
import uuid

import boto3
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.core.config import settings

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    return _s3_client


async def upload_image(file: UploadFile, folder: str = "products") -> str:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type!r} not allowed. Use JPEG, PNG, or WebP.",
        )

    data = await file.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds 5 MB limit")

    img = Image.open(io.BytesIO(data))
    if img.width > 1200 or img.height > 1200:
        img.thumbnail((1200, 1200), Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)

    key = f"{folder}/{uuid.uuid4()}.jpg"
    s3 = get_s3_client()
    s3.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=buffer.getvalue(),
        ContentType="image/jpeg",
        ACL="public-read",
    )
    return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


async def delete_image(url: str) -> None:
    prefix = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/"
    if not url.startswith(prefix):
        return
    key = url[len(prefix):]
    s3 = get_s3_client()
    s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
