"""admin 路由：手动创建任务 + 全局统计 + 失败重置."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import Task, TaskStatus
from app.models.node import Node
from app.models.user import User
from app.models.contribution import ContributionLog
from app.schemas.task import TaskCreateRequest
from app.utils.security import decode_token

router = APIRouter(prefix="/admin", tags=["admin"])


def _admin_check(request: Request) -> None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing Authorization")
    payload = decode_token(auth[7:])
    if not payload:
        raise HTTPException(401, "Invalid token")
    # TODO: add admin role check in User model


@router.post("/tasks", status_code=201)
async def create_task(body: TaskCreateRequest, request: Request, db: AsyncSession = Depends(get_db)):
    _admin_check(request)
    task = Task(
        name=body.name,
        level=body.level,
        base_contribution=body.base_contribution,
        timeout_sec=body.timeout_sec,
        config=body.config,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return {"id": str(task.id), "name": task.name, "status": task.status.value}


@router.get("/stats")
async def global_stats(request: Request, db: AsyncSession = Depends(get_db)):
    _admin_check(request)
    task_count = (await db.execute(select(func.count(Task.id)))).scalar()
    pending = (await db.execute(select(func.count(Task.id)).where(Task.status == TaskStatus.PENDING))).scalar()
    running = (await db.execute(select(func.count(Task.id)).where(Task.status == TaskStatus.RUNNING))).scalar()
    completed = (await db.execute(select(func.count(Task.id)).where(Task.status == TaskStatus.COMPLETED))).scalar()
    failed = (await db.execute(select(func.count(Task.id)).where(Task.status == TaskStatus.FAILED))).scalar()
    user_count = (await db.execute(select(func.count(User.id)))).scalar()
    node_count = (await db.execute(select(func.count(Node.id)))).scalar()
    total_contrib = (await db.execute(select(func.sum(User.contribution_balance)))).scalar() or 0

    return {
        "tasks": {"total": task_count, "pending": pending, "running": running, "completed": completed, "failed": failed},
        "users": user_count,
        "nodes": node_count,
        "total_contribution_distributed": total_contrib,
    }


@router.post("/tasks/reset-failed")
async def reset_failed_tasks(request: Request, db: AsyncSession = Depends(get_db)):
    _admin_check(request)
    result = await db.execute(
        select(Task).where(Task.status == TaskStatus.FAILED)
    )
    tasks = result.scalars().all()
    for t in tasks:
        t.status = TaskStatus.PENDING
        t.retry_count = 0
    await db.commit()
    return {"reset": len(tasks)}
