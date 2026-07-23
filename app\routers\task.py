"""task 路由：任务领取 + 进度更新 + 结果提交."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import Task, TaskStatus
from app.models.node import Node, NodeStatus
from app.schemas.task import (
    TaskCreateRequest, TaskClaimResponse, TaskProgressRequest, TaskSubmitRequest, TaskRead
)
from app.utils.security import decode_token
from app.utils.redis_client import get_redis, RedisLock, RateLimiter
from app.services.contribution_service import settle_contribution
from app.config import get_settings

router = APIRouter(prefix="/task", tags=["task"])
settings_cfg = get_settings()


def _user_from_header(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing Authorization header")
    payload = decode_token(auth[7:])
    if not payload:
        raise HTTPException(401, "Invalid token")
    return payload


async def _check_rate_limit(redis_client, user_id: str, action: str):
    key = f"ratelimit:{action}:{user_id}"
    limit = settings_cfg.rate_limit_claim_per_min
    limiter = RateLimiter(redis_client, key, limit)
    if not await limiter.is_allowed():
        raise HTTPException(429, f"{action} 频率超限，请稍后再试")


@router.get("/available")
async def list_available_tasks(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.status == TaskStatus.PENDING).order_by(Task.created_at).limit(20)
    )
    tasks = result.scalars().all()
    return [
        TaskRead(
            id=str(t.id), name=t.name, level=t.level, base_contribution=t.base_contribution,
            status=t.status.value, claimed_by_node_id=str(t.claimed_by_node_id) if t.claimed_by_node_id else None,
            claimed_by_user_id=str(t.claimed_by_user_id) if t.claimed_by_user_id else None,
            result_url=t.result_url, result_hash=t.result_hash, retry_count=t.retry_count,
            timeout_sec=t.timeout_sec, created_at=t.created_at, started_at=t.started_at,
            completed_at=t.completed_at,
        )
        for t in tasks
    ]


@router.post("/claim", response_model=TaskClaimResponse)
async def claim_task(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = _user_from_header(request)
    user_id = uuid.UUID(payload["sub"])

    async with get_redis() as r:
        await _check_rate_limit(r, payload["sub"], "claim")
        # Find a pending task
        result = await db.execute(
            select(Task, Node)
            .join(Node, Task.claimed_by_node_id == None)
            .where(Task.status == TaskStatus.PENDING)
            .order_by(Task.created_at)
            .limit(1)
        )
        row = result.first()
        if not row:
            raise HTTPException(404, "暂无可领取任务")
        task, node = row

        # Redis 乐观锁
        lock_key = f"lock:claim:{task.id}"
        lock = RedisLock(r, lock_key, ttl_sec=settings_cfg.task_claim_ttl_sec)
        if not await lock.acquire():
            raise HTTPException(409, "任务已被其他节点抢先")

        try:
            # DB 行锁
            await db.execute(
                select(Task).where(Task.id == task.id).with_for_update()
            )
            fresh = (await db.execute(select(Task).where(Task.id == task.id))).scalar_one()
            if fresh.status != TaskStatus.PENDING:
                raise HTTPException(409, "任务状态已变化")

            running_key = f"lock:running:{task.id}"
            fresh.status = TaskStatus.RUNNING
            fresh.claimed_by_user_id = user_id
            fresh.claimed_by_node_id = node.id
            fresh.started_at = datetime.now(timezone.utc)
            fresh.running_lock_key = running_key
            await db.commit()

            return TaskClaimResponse(
                task_id=str(task.id), name=task.name, level=task.level,
                base_contribution=task.base_contribution, timeout_sec=task.timeout_sec,
                config=task.config, started_at=fresh.started_at,
            )
        except HTTPException:
            await db.rollback()
            raise
        finally:
            await lock.release()


@router.post("/progress")
async def update_progress(
    body: TaskProgressRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = _user_from_header(request)
    user_id = uuid.UUID(payload["sub"])

    result = await db.execute(
        select(Task).where(Task.id == uuid.UUID(body.task_id)).with_for_update()
    )
    task: Task | None = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.claimed_by_user_id != user_id:
        raise HTTPException(403, "不是你的任务")

    async with get_redis() as r:
        running_key = f"lock:running:{task.id}"
        lock = RedisLock(r, running_key, ttl_sec=settings_cfg.task_run_ttl_sec)
        await lock.extend(settings_cfg.task_run_ttl_sec)

    return {"ok": True, "progress_pct": body.progress_pct}


@router.post("/submit")
async def submit_result(
    body: TaskSubmitRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = _user_from_header(request)
    user_id = uuid.UUID(payload["sub"])

    result = await db.execute(
        select(Task).where(Task.id == uuid.UUID(body.task_id)).with_for_update()
    )
    task: Task | None = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.claimed_by_user_id != user_id:
        raise HTTPException(403, "不是你的任务")
    if task.status not in (TaskStatus.RUNNING, TaskStatus.PENDING):
        raise HTTPException(409, f"任务状态不允许提交: {task.status.value}")

    task.status = TaskStatus.COMPLETED
    task.result_url = body.result_url
    task.result_hash = body.result_hash
    task.completed_at = datetime.now(timezone.utc)

    await settle_contribution(
        session=db,
        user_id=user_id,
        task_id=task.id,
        amount=task.base_contribution,
        reason=f"任务完成: {task.name}",
    )
    await db.commit()
    return {"ok": True, "contribution_earned": task.base_contribution}
