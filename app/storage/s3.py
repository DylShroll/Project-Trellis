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
