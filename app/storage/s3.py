import uuid as _uuid

import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings

settings = get_settings()


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


def generate_presigned_upload_url(
    object_key: str, content_type: str = "image/jpeg", expires_in: int = 300
) -> str:
    """Generate a presigned URL for direct S3 upload from the browser."""
    client = get_s3_client()
    url: str = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket_name,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )
    return url


def generate_presigned_download_url(object_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for reading an S3 object."""
    client = get_s3_client()
    url: str = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": object_key},
        ExpiresIn=expires_in,
    )
    return url


def delete_object(object_key: str) -> None:
    client = get_s3_client()
    client.delete_object(Bucket=settings.s3_bucket_name, Key=object_key)


def build_object_key(user_id: str, plot_id: str, filename: str) -> str:
    return f"profiles/{user_id}/{plot_id}/{filename}"


_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

ALLOWED_IMAGE_TYPES: frozenset[str] = frozenset(_MIME_TO_EXT)
MAX_IMAGE_BYTES: int = 2 * 1024 * 1024  # 2 MB


def resize_image(data: bytes, max_size: int = 400) -> tuple[bytes, str]:
    """Resize image to at most max_size x max_size, preserving aspect ratio.
    Always outputs JPEG. Returns (resized_bytes, content_type).
    """
    import io

    from PIL import Image

    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue(), "image/jpeg"


def upload_image(data: bytes, content_type: str, user_id: str, scope: str = "uploads") -> str:
    """Upload raw image bytes to S3 and return the public object URL.

    Raises ``ClientError`` or ``ValueError`` on failure.
    """
    ext = _MIME_TO_EXT.get(content_type, "jpg")
    key = f"{scope}/{user_id}/{_uuid.uuid4()}.{ext}"
    client = get_s3_client()
    client.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"
