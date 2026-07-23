"""
firefly-scheduler · Router · Task
任务领取 / 进度上报 / 结果提交 / 状态查询
"""
import uuid
import time
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database import get_db
from app.models.task import Task
from app.models.node import Node
from app.models.user import User
from app.schemas.task import (
    TaskClaimResponse, TaskProgressRequest,
    TaskSubmitRequest, TaskResponse,
)
from app.utils.security import decode_token
from app.utils.redis_client import (
    acquire_lock, release_lock, check_claim_rate,
    set_heartbeat,
)
from app.utils.minio_client import get_presigned_download_url
from app.config import settings

router = APIRouter(prefix="/api/v1/task", tags=["Task"])
bearer = HTTPBearer()

TASK_LOCK_PREFIX = "task:lock:"
CLAIM_PREFIX = "node:claim:"


# ── 获取当前用户 ──────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── 获取用户活跃节点 ──────────────────
async def get_active_node(user: User, db: AsyncSession) -> Node:
    result = await db.execute(
        select(Node).where(
            Node.user_id == user.id,
            Node.is_banned == False,
        ).limit(1)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="No active node found")
    return node


# ─────────────────────────────────────
# POST /claim  节点领取任务
# ─────────────────────────────────────
@router.post("/claim", response_model=TaskClaimResponse)
async def claim_task(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """节点领取一个最合适的待分配任务"""
    node = await get_active_node(user, db)

    # 1. 频率限制
    if not await check_claim_rate(node.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Claim too frequent, please wait",
        )

    # 2. 节点必须在线
    if node.status != "online":
        raise HTTPException(status_code=400, detail="Node is not online")

    # 3. 查询候选任务（乐观锁抢占）
    candidate = await db.execute(
        select(Task).where(
            Task.status == "pending",
            Task.level <= node.max_task_level,
            Task.retry_count < Task.max_retries,
        ).order_by(Task.created_at.asc()).limit(5)
    )
    tasks = candidate.scalars().all()

    claimed_task = None
    for task in tasks:
        lock_key = f"{TASK_LOCK_PREFIX}{task.id}"
        if await acquire_lock(lock_key, expire=5):
            # 原子更新：仅当 status 仍为 pending 时
            result = await db.execute(
                update(Task).where(
                    Task.id == task.id,
                    Task.status == "pending",
                ).values(
                    status="claimed",
                    claimed_by=node.id,
                    claimed_at=datetime.utcnow(),
                ).returning(Task)
            )
            updated = result.scalar_one_or_none()
            if updated:
                claimed_task = updated
                await db.flush()
                break
            await release_lock(lock_key)

    if not claimed_task:
        raise HTTPException(status_code=404, detail="No available tasks")

    # 4. 更新节点状态 + 心跳
    node.status = "busy"
    await set_heartbeat(node.id)

    # 5. 生成预签名下载 URL
    config = json.loads(claimed_task.config_json or "{}")
    download_url = await get_presigned_download_url(
        claimed_task.task_package_url or f"tasks/{claimed_task.id}/package.zip",
        expires_sec=3600,
    )
    deadline = datetime.utcnow() + timedelta(seconds=claimed_task.timeout_sec)

    return TaskClaimResponse(
        task_id=claimed_task.id,
        task_name=claimed_task.name,
        task_level=claimed_task.level,
        task_package_url=download_url,
        config=config,
        deadline=deadline,
    )


# ─────────────────────────────────────
# POST /progress  节点上报进度
# ─────────────────────────────────────
@router.post("/progress")
async def report_progress(
    body: TaskProgressRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """节点定期上报训练进度（每 60 秒）"""
    node = await get_active_node(user, db)

    # 查找该节点正在执行的任务
    result = await db.execute(
        select(Task).where(
            Task.claimed_by == node.id,
            Task.status.in_(["claimed", "running"]),
        ).limit(1)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="No active task found")

    # 更新状态和心跳
    task.status = "running"
    await set_heartbeat(node.id)

    # TODO: 进度写入 Redis 供监控面板读取
    progress_pct = (body.current_step / max(body.total_steps, 1)) * 100

    return {
        "status": "ok",
        "task_id": task.id,
        "progress_pct": round(progress_pct, 1),
    }


# ─────────────────────────────────────
# POST /submit  节点提交结果
# ─────────────────────────────────────
@router.post("/submit")
async def submit_task(
    body: TaskSubmitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    节点提交训练结果
    进入校验队列（v0.1 仅做格式校验，后续版本加质量评估）
    """
    node = await get_active_node(user, db)

    # 查找该节点的进行中任务
    result = await db.execute(
        select(Task).where(
            Task.claimed_by == node.id,
            Task.status.in_(["claimed", "running"]),
        ).limit(1)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="No active task to submit")

    # ── 一级校验：格式与完整性（v0.1 简化版） ──
    if not body.result_object_name:
        # 驳回：扣信誉分 + 任务回退
        node.reputation_score = max(0, node.reputation_score - 10)
        task.retry_count += 1
        if task.retry_count >= task.max_retries:
            task.status = "failed"
        else:
            task.status = "pending"
            task.claimed_by = None
        await db.flush()
        raise HTTPException(status_code=400, detail="Result file missing")

    # 校验通过 → 标记完成，等待异步校验
    task.status = "completed"
    task.result_object_name = body.result_object_name
    task.result_sha256 = body.result_sha256
    task.completed_at = datetime.utcnow()

    # 节点统计更新
    node.total_tasks_completed += 1
    node.status = "online"
    await set_heartbeat(node.id)

    await db.flush()

    # TODO: v0.5 接入二级/三级校验 + 贡献值结算
    # 当前 v0.1 直接给基础贡献值
    # （结算逻辑放在 services/contribution_service.py）

    return {
        "status": "accepted",
        "task_id": task.id,
        "message": "Result submitted, pending validation",
    }


# ─────────────────────────────────────
# GET /{task_id}  查询任务状态
# ─────────────────────────────────────
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """查询任务当前状态"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        task_id=task.id,
        status=task.status,
        level=task.level,
        claimed_by=task.claimed_by,
        retry_count=task.retry_count,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )
