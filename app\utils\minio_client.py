"""
firefly-scheduler · MinIO 工具
对象存储：任务包上传/下载、预签名 URL
"""
from minio import Minio
from minio.error import S3Error
from app.config import settings


# ── 全局客户端 ──────────────────────
minio_client = Minio(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)


# ── 初始化：确保 bucket 存在 ────────
async def ensure_bucket():
    """应用启动时调用，确保 bucket 存在"""
    try:
        found = await asyncio.to_thread(minio_client.bucket_exists, settings.minio_bucket)
        if not found:
            await asyncio.to_thread(minio_client.make_bucket, settings.minio_bucket)
    except S3Error as e:
        print(f"[MinIO] Error: {e}")


# ── 上传文件 ────────────────────────
async def upload_file(object_name: str, file_path: str) -> str:
    """
    上传本地文件到 MinIO
    返回对象的 URL 路径
    """
    await asyncio.to_thread(
        minio_client.fput_object,
        settings.minio_bucket,
        object_name,
        file_path,
    )
    return f"{settings.minio_bucket}/{object_name}"


# ── 生成预签名下载 URL ──────────────
async def get_presigned_download_url(object_name: str, expires_sec: int = 3600) -> str:
    """
    生成带签名的临时下载链接（默认 1 小时有效）
    """
    url = await asyncio.to_thread(
        minio_client.presigned_get_object,
        settings.minio_bucket,
        object_name,
        expires=expires_sec,
    )
    return url


# ── 生成预签名上传 URL ──────────────
async def get_presigned_upload_url(object_name: str, expires_sec: int = 3600) -> str:
    """
    生成带签名的临时上传链接（客户端直传用）
    """
    url = await asyncio.to_thread(
        minio_client.presigned_put_object,
        settings.minio_bucket,
        object_name,
        expires=expires_sec,
    )
    return url


# 延迟导入（避免循环依赖）
import asyncio
