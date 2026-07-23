"""分层配置：环境变量 + .env 文件，pydantic-settings 自动校验."""
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    user: str = Field(default="firefly", alias="POSTGRES_USER")
    password: str = Field(default="changeme", alias="POSTGRES_PASSWORD")
    name: str = Field(default="firefly_scheduler", alias="POSTGRES_DB")

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    db: int = Field(default=0, alias="REDIS_DB")

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class MinIOSettings(BaseSettings):
    endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    access_key: str = Field(default="firefly_admin", alias="MINIO_ACCESS_KEY")
    secret_key: str = Field(default="changeme", alias="MINIO_SECRET_KEY")
    bucket_packages: str = Field(default="task-packages", alias="MINIO_BUCKET_PACKAGES")
    bucket_results: str = Field(default="results", alias="MINIO_BUCKET_RESULTS")
    secure: bool = Field(default=False, alias="MINIO_SECURE")


class JWTSettings(BaseSettings):
    secret_key: str = Field(default="CHANGE_ME_IN_PRODUCTION", alias="JWT_SECRET_KEY")
    algorithm: str = "HS256"
    access_expire_minutes: int = Field(default=30, alias="JWT_ACCESS_EXPIRE_MINUTES")
    refresh_expire_days: int = Field(default=7, alias="JWT_REFRESH_EXPIRE_DAYS")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # App
    app_name: str = "Firefly Scheduler"
    debug: bool = False

    # Sub-configs
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    minio: MinIOSettings = Field(default_factory=MinIOSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)

    # Scheduler policy
    task_claim_ttl_sec: int = 600        # 10 min → claimed 超时回 pending
    task_run_ttl_sec: int = 7200         # 2 h → running 超时回收
    heartbeat_interval_sec: int = 30
    task_max_retries: int = 3
    node_offline_sec: int = 60            # 60s 无心跳 → offline
    node_recover_interval_sec: int = 21600  # 6 h → 信誉恢复

    # Rate limits
    rate_limit_claim_per_min: int = 6
    rate_limit_heartbeat_per_min: int = 60
    rate_limit_register_per_hour: int = 10

    @property
    def database_url(self) -> str:
        return self.postgres.url

    @property
    def redis_url(self) -> str:
        return self.redis.url


@lru_cache
def get_settings() -> Settings:
    return Settings()
