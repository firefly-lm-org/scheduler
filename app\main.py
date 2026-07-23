"""
firefly-scheduler · 主入口
FastAPI 应用初始化、路由挂载、启动/关闭钩子
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, close_db
from app.utils.minio_client import ensure_bucket
from app.services.background_tasks import (
    timeout_reclaimer,
    offline_detector,
    reputation_recovery,
)
from app.routers import auth, node, task, admin


# ─────────────────────────────────────
# 生命周期管理
# ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的初始化与清理"""
    print("🟢 [Firefly] Starting up...")

    # 1. 初始化数据库表
    await init_db()
    print("  ✓ Database tables ready")

    # 2. 确保 MinIO bucket 存在
    await ensure_bucket()
    print("  ✓ MinIO bucket ready")

    # 3. 启动后台任务
    tasks = [
        asyncio.create_task(timeout_reclaimer(), name="timeout_reclaimer"),
        asyncio.create_task(offline_detector(), name="offline_detector"),
        asyncio.create_task(reputation_recovery(), name="reputation_recovery"),
    ]
    print("  ✓ Background tasks started")
    print("🔥 Firefly Scheduler is LIVE")

    yield

    # ── 关闭清理 ──
    print("🔴 [Firefly] Shutting down...")
    for t in tasks:
        t.cancel()
    await close_db()
    print("  ✓ Cleanup complete")


# ─────────────────────────────────────
# 创建 FastAPI 实例
# ─────────────────────────────────────
app = FastAPI(
    title="Firefly LM · 萤火虫大模型调度中心",
    description="全球分布式志愿算力驱动的 AI 训练调度系统",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS（开发阶段允许前端跨域） ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # v0.1 全开，v1.0 收紧到具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────
# 挂载路由
# ─────────────────────────────────────
app.include_router(auth.router, prefix="", tags=["Auth"])
app.include_router(node.router, prefix="", tags=["Node"])
app.include_router(task.router, prefix="", tags=["Task"])
app.include_router(admin.router, prefix="", tags=["Admin"])


# ─────────────────────────────────────
# 根路径
# ─────────────────────────────────────
@app.get("/")
async def root():
    return {
        "project": "Firefly LM",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """健康检查（供 Docker / 负载均衡探活）"""
    return {"status": "healthy"}
