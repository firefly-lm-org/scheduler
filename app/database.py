"""
firefly-scheduler · 数据库连接
SQLAlchemy 2.0 异步引擎 + 会话工厂
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类"""
    pass


# ── 异步引擎 ──────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=(settings.env == "development"),   # 开发环境打印 SQL
    pool_pre_ping=True,
)

# ── 会话工厂 ──────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── 依赖注入：FastAPI 路由中使用 ──
async def get_db() -> AsyncSession:
    """FastAPI Depends 用：自动管理会话生命周期"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── 初始化：建表（开发环境首次启动用） ──
async def init_db():
    """在应用启动时调用，自动创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── 关闭引擎 ──────────────────────────
async def close_db():
    await engine.dispose()
