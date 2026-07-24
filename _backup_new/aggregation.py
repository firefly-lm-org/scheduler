"""
firefly-scheduler · Router · Aggregation
手动触发权重聚合 API + 聚合记录查询
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.aggregation import AggregationRecord
from app.models.task import Task
from app.services.aggregation_service import (
    find_ready_aggregation,
    run_pending_aggregations,
)
from app.utils.security import decode_token

router = APIRouter(prefix="/api/v1/admin", tags=["Admin · Aggregation"])
bearer = HTTPBearer()


# ── 复用 get_current_user（与 node.py 保持一致） ──
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    result = await db.execute(
        select(User).where(User.id == payload["sub"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── 1. 手动触发聚合 ──────────────────────────
@router.post("/aggregate")
async def trigger_aggregation(
    model_version: str = Form(..., description="要聚合的模型版本，如 v0.1"),
    aggregation_key: str = Form(
        None, description="可选，指定聚合分组键，默认为 'default'"
    ),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    手动触发指定 model_version 的权重聚合。
    - 查找该 model_version 下所有已完成但未聚合的任务
    - 如果数量达到阈值（aggregation_threshold）则立即执行聚合
    - 否则返回当前就绪状态
    """
    key = aggregation_key or "default"

    # 先检查就绪情况
    ready_groups = await find_ready_aggregation(db)
    target_key = f"{model_version}___{key}"

    if target_key not in ready_groups:
        # 没有达到阈值，提示当前状态
        # 统计当前该版本的已完成任务数
        result = await db.execute(
            select(Task).where(
                Task.status == "completed",
                Task.result_sha256.isnot(None),
                Task.model_version == model_version,
            )
        )
        from app.config import settings
        completed = list(result.scalars().all())
        return {
            "status": "not_ready",
            "model_version": model_version,
            "aggregation_key": key,
            "completed_tasks": len(completed),
            "threshold": settings.aggregation_threshold,
            "message": (
                f"已完成 {len(completed)} 个任务，需要 {settings.aggregation_threshold} 个才能触发聚合"
            ),
        }

    # 执行聚合
    task_infos = ready_groups[target_key]
    from app.services.aggregation_service import (
        aggregate_for_version,
        settle_aggregation,
        mark_tasks_aggregated,
        get_lock,
    )

    lock = await get_lock(model_version)
    if lock.locked():
        raise HTTPException(
            status_code=409,
            detail=f"Aggregation for {model_version} is already running",
        )

    async with lock:
        try:
            agg_result = await aggregate_for_version(
                db, model_version, key, task_infos
            )
            await settle_aggregation(db, task_infos, agg_result)
            task_ids = [t["task_id"] for t in task_infos]
            await mark_tasks_aggregated(db, task_ids, agg_result["aggregation_id"])
            await db.commit()
            return {
                "status": "ok",
                "message": "Aggregation completed",
                **agg_result,
            }
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Aggregation failed: {e}",
            )


# ── 2. 查询聚合记录列表 ──────────────────────
@router.get("/aggregation-records")
async def list_aggregation_records(
    model_version: str | None = None,
    status_filter: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    查询聚合记录列表。
    支持按 model_version 和 status 过滤。
    """
    query = select(AggregationRecord).order_by(desc(AggregationRecord.created_at))

    if model_version:
        query = query.where(AggregationRecord.model_version == model_version)
    if status_filter:
        query = query.where(AggregationRecord.status == status_filter)

    query = query.limit(limit)

    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "total": len(records),
        "records": [
            {
                "id": r.id,
                "model_version": r.model_version,
                "aggregation_key": r.aggregation_key,
                "num_participants": r.num_participants,
                "num_tasks": r.num_tasks,
                "status": r.status,
                "checkpoint_url": r.aggregated_checkpoint_url,
                "aggregated_sha256": r.aggregated_sha256,
                "total_contribution_settled": r.total_contribution_settled,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in records
        ],
    }


# ── 3. 查询单个聚合详情 ─────────────────────
@router.get("/aggregation-records/{aggregation_id}")
async def get_aggregation_record(
    aggregation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    查询单个聚合记录的完整详情。
    """
    result = await db.execute(
        select(AggregationRecord).where(AggregationRecord.id == aggregation_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Aggregation record not found")

    # 同时返回参与该聚合的任务列表
    # 由于 tasks 表的 aggregation_key 不是外键，通过 result_sha256 关联
    # 简化处理：直接返回记录本身的字段
    return {
        "id": record.id,
        "model_version": record.model_version,
        "aggregation_key": record.aggregation_key,
        "num_participants": record.num_participants,
        "num_tasks": record.num_tasks,
        "status": record.status,
        "checkpoint_url": record.aggregated_checkpoint_url,
        "aggregated_sha256": record.aggregated_sha256,
        "total_contribution_settled": record.total_contribution_settled,
        "error_message": record.error_message,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
    }


# ── 4. 获取当前可聚合状态（无需鉴权，公开） ──
@router.get("/aggregation-status")
async def get_aggregation_status(
    db: AsyncSession = Depends(get_db),
):
    """
    公开接口：返回各 model_version 的当前可聚合状态。
    无需认证，供调度中心仪表盘使用。
    """
    from app.config import settings

    ready_groups = await find_ready_aggregation(db)

    # 统计所有版本的就绪情况
    all_versions: dict[str, dict] = {}
    for key_str, task_infos in ready_groups.items():
        parts = key_str.split("___", 1)
        version = parts[0]
        if version not in all_versions:
            all_versions[version] = {
                "model_version": version,
                "ready_groups": [],
                "total_ready_tasks": 0,
            }
        all_versions[version]["ready_groups"].append({
            "aggregation_key": parts[1] if len(parts) > 1 else "default",
            "ready_task_count": len(task_infos),
            "threshold": settings.aggregation_threshold,
        })
        all_versions[version]["total_ready_tasks"] += len(task_infos)

    return {
        "threshold": settings.aggregation_threshold,
        "versions": list(all_versions.values()),
    }
