"""
firefly-scheduler · 配置管理
分层配置：环境变量 > .env 文件 > 默认值
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── 环境 ──────────────────────────
    env: str = "development"

    # ── 数据库 ────────────────────────
    database_url: str = "postgresql+asyncpg://firefly:firefly123@localhost:5432/firefly"

    # ── Redis ──────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── MinIO ──────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "firefly"
    minio_secret_key: str = "firefly123456"
    minio_bucket: str = "firefly-tasks"
    minio_secure: bool = False

    # ── JWT ────────────────────────────
    jwt_secret: str = "change-me"
    jwt_access_expire: int = 86400       # 24 小时
    jwt_refresh_expire: int = 604800     # 7 天

    # ── 任务调度参数 ──────────────────
    task_claim_interval: int = 10        # 节点最短领取间隔（秒）
    task_heartbeat_timeout: int = 90     # 心跳超时（秒）→ 判定离线
    task_progress_interval: int = 60     # 进度上报间隔（秒）
    task_max_retries: int = 3            # 任务最大重试次数

    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局单例
settings = Settings()

# ── 导出常用常量（方便其他模块 import） ──
ENV = settings.env
DATABASE_URL = settings.database_url
REDIS_URL = settings.redis_url
TASK_MAX_RETRIES = settings.task_max_retries
TASK_HEARTBEAT_TIMEOUT = settings.task_heartbeat_timeout
