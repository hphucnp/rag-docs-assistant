import io
import logging
import uuid
from datetime import timedelta

from miniopy_async import Minio
from miniopy_async.error import S3Error

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: Minio | None = None

SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
}


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            f"{settings.minio_host}:{settings.minio_port}",
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


async def ensure_bucket() -> None:
    """Create the default bucket if it does not exist yet."""
    client = get_minio_client()
    found = await client.bucket_exists(settings.minio_bucket)
    if not found:
        await client.make_bucket(settings.minio_bucket)
        logger.info("Created MinIO bucket: %s", settings.minio_bucket)
    else:
        logger.debug("MinIO bucket already exists: %s", settings.minio_bucket)


async def upload_file(data: bytes, filename: str, content_type: str) -> str:
    """Upload raw bytes to MinIO and return the object key."""
    client = get_minio_client()
    object_key = f"{uuid.uuid4()}/{filename}"
    await client.put_object(
        settings.minio_bucket,
        object_key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    logger.info("Uploaded file to MinIO: %s", object_key)
    return object_key


async def download_file(object_key: str) -> bytes:
    """Download an object from MinIO and return its bytes."""
    client = get_minio_client()
    response = await client.get_object(settings.minio_bucket, object_key)
    return await response.read()


async def delete_file(object_key: str) -> None:
    """Delete an object from MinIO, silently ignoring missing keys."""
    client = get_minio_client()
    try:
        await client.remove_object(settings.minio_bucket, object_key)
        logger.info("Deleted file from MinIO: %s", object_key)
    except S3Error as exc:
        if exc.code != "NoSuchKey":
            raise


async def presigned_download_url(object_key: str, expires_seconds: int = 3600) -> str:
    """Return a pre-signed GET URL valid for `expires_seconds` seconds."""
    client = get_minio_client()
    return await client.presigned_get_object(
        settings.minio_bucket,
        object_key,
        expires=timedelta(seconds=expires_seconds),
    )
