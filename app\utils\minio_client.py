"""MinIO / S3 客户端：预签名 URL 生成."""
import logging
from typing import Optional
from minio import Minio
from minio.datatypes import Object

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _client() -> Minio:
    return Minio(
        settings.minio.endpoint,
        access_key=settings.minio.access_key,
        secret_key=settings.minio.secret_key,
        secure=settings.minio.secure,
    )


def ensure_buckets() -> None:
    mc = _client()
    for bucket in [settings.minio.bucket_packages, settings.minio.bucket_results]:
        if not mc.bucket_exists(bucket):
            mc.make_bucket(bucket)
            logger.info("Bucket created: %s", bucket)


def get_presigned_upload_url(object_name: str, bucket: str, expires_sec: int = 3600) -> str:
    mc = _client()
    return mc.presigned_put_object(bucket, object_name, expires=expires_sec)


def get_presigned_download_url(object_name: str, bucket: str, expires_sec: int = 3600) -> str:
    mc = _client()
    return mc.presigned_get_object(bucket, object_name, expires=expires_sec)
