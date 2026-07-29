"""
firefly-scheduler · MinIO 工具（本地 Mock 实现）
当 MinIO 不可用时，使用本地文件系统模拟对象存储。
文件存储在 _minio_mock/{bucket}/{object_name}
预签名 URL 指向 localhost:9001 的本地 HTTP 服务器
"""
import asyncio
import hashlib
import os
import shutil
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

from app.config import settings

# ── 本地 Mock 存储根目录 ──────────────
MOCK_ROOT = Path("D:/firefly-scheduler/_minio_mock")
MOCK_HTTP_PORT = 9001

# ── 全局 Mock 客户端（兼容 minio API 但本地实现）─────────
class _LocalMockClient:
    """本地模拟 MinIO，API 签名兼容 minio Python SDK"""

    def __init__(self):
        self._root = MOCK_ROOT / settings.minio_bucket
        self._root.mkdir(parents=True, exist_ok=True)

    def bucket_exists(self) -> bool:
        return self._root.exists()

    def make_bucket(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)

    def fput_object(self, bucket: str, object_name: str, file_path: str) -> None:
        dest = self._root / object_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest)

    def fget_object(self, bucket: str, object_name: str, file_path: str) -> None:
        src = self._root / object_name
        if not src.exists():
            raise FileNotFoundError(f"Mock object not found: {object_name}")
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, file_path)

    def stat_object(self, bucket: str, object_name: str):
        """返回模拟的 ObjectStat"""
        src = self._root / object_name
        if not src.exists():
            raise FileNotFoundError(f"Mock object not found: {object_name}")
        return _MockObjectStat(src.stat().st_size, datetime.now(timezone.utc))

    def presigned_get_object(self, bucket: str, object_name: str, expires: timedelta) -> str:
        """返回本地 HTTP URL"""
        return f"http://localhost:{MOCK_HTTP_PORT}/{bucket}/{object_name}"

    def presigned_put_object(self, bucket: str, object_name: str, expires: timedelta) -> str:
        return f"http://localhost:{MOCK_HTTP_PORT}/__upload__/{bucket}/{object_name}"


class _MockObjectStat:
    def __init__(self, size: int, last_modified: datetime):
        self.size = size
        self.last_modified = last_modified


minio_client: object = _LocalMockClient()  # type: ignore[assignment]


# ── 本地 HTTP 服务器（为客户端提供下载服务）─────────────
_mock_server_thread: threading.Thread | None = None
_mock_server_shutdown = threading.Event()


class _MockHTTPHandler(SimpleHTTPRequestHandler):
    """处理 presigned URL 请求"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(MOCK_ROOT), **kwargs)

    def log_message(self, format, *args):
        pass  # 静默日志

    def do_GET(self):
        # 去掉 /bucket/ 前缀
        path = self.path.lstrip("/")
        file_path = MOCK_ROOT / path
        if file_path.is_file():
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", file_path.stat().st_size)
            self.end_headers()
            with open(file_path, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
        else:
            self.send_error(404)

    def do_PUT(self):
        path = self.path.lstrip("/")
        if path.startswith("__upload__/"):
            object_path = path[len("__upload__/"):]
        else:
            object_path = path
        file_path = MOCK_ROOT / object_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content_length = int(self.headers.get("Content-Length", 0))
        with open(file_path, "wb") as f:
            shutil.copyfileobj(self.rfile, f, length=min(content_length, 10 * 1024 * 1024))
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self):
        path = self.path.lstrip("/")
        file_path = MOCK_ROOT / path
        if file_path.is_file():
            self.send_response(200)
            self.send_header("Content-Length", file_path.stat().st_size)
            self.end_headers()
        else:
            self.send_error(404)


def _run_mock_server():
    MOCK_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        server = HTTPServer(("0.0.0.0", MOCK_HTTP_PORT), _MockHTTPHandler)
        print(f"[MinIO Mock] HTTP server running on port {MOCK_HTTP_PORT}")
        while not _mock_server_shutdown.is_set():
            server.timeout = 0.5
            server.handle_request()
        server.server_close()
    except Exception as e:
        print(f"[MinIO Mock] Server error: {e}")


def start_mock_server():
    global _mock_server_thread
    if _mock_server_thread is None or not _mock_server_thread.is_alive():
        _mock_server_shutdown.clear()
        _mock_server_thread = threading.Thread(target=_run_mock_server, daemon=True)
        _mock_server_thread.start()


def stop_mock_server():
    _mock_server_shutdown.set()


# ── 初始化：确保 bucket 存在 ────────
async def ensure_bucket():
    """应用启动时调用，确保本地存储就绪 + 启动 HTTP 服务器"""
    try:
        if not minio_client.bucket_exists():
            minio_client.make_bucket()
        start_mock_server()
        print("  ✓ MinIO (local mock) ready")
    except Exception as e:
        print(f"[MinIO] Error: {e}")


# ── 上传文件 ────────────────────────
async def upload_file(object_name: str, file_path: str) -> str:
    """上传本地文件到 Mock 存储"""
    await asyncio.to_thread(minio_client.fput_object, settings.minio_bucket, object_name, file_path)
    return f"{settings.minio_bucket}/{object_name}"


# ── 生成预签名下载 URL ────────────────
async def get_presigned_download_url(object_name: str, expires_sec: int = 3600) -> str:
    """生成带签名的临时下载链接"""
    return await asyncio.to_thread(
        minio_client.presigned_get_object,
        settings.minio_bucket,
        object_name,
        timedelta(seconds=expires_sec),
    )


# ── 生成预签名上传 URL ────────────────
async def get_presigned_upload_url(object_name: str, expires_sec: int = 3600) -> str:
    """生成带签名的临时上传链接（客户端直传用）"""
    return await asyncio.to_thread(
        minio_client.presigned_put_object,
        settings.minio_bucket,
        object_name,
        timedelta(seconds=expires_sec),
    )
