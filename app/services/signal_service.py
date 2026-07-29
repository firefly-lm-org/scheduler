"""
firefly-scheduler · Service · Signal
v0.6 信号回流服务：接收、存储、分析节点上报的脱敏信号
"""
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sql_func

from app.models.signal import ContribSignalLog
from app.models.node import Node


# ─────────────────────────────────────
# 信号贡献估算（给节点参考的积分预估）
# ─────────────────────────────────────
def estimate_contribution(req: "ContribSignalRequest") -> int:
    """
    估算信号贡献积分（v0.6 简化版）

    规则：
    - 每上报一次信号：+1 分（参与奖励）
    - holdout 提升 > 5%：额外 +2 分
    - 每贡献一个样本（脱敏）：+0.5 分
    - 有 query_patterns：+1 分（数据质量信号）

    返回估算积分（四舍五入）
    """
    score = 1  # 基础参与奖
    if req.holdout_improvement > 0.05:
        score += 2
    if req.sample_count > 0:
        score += min(req.sample_count, 10) // 2  # 最多 +5
    if req.query_patterns:
        score += 1
    return score


async def record_signal(
    db: AsyncSession,
    req: "ContribSignalRequest",
    contribution_estimated: int,
) -> ContribSignalLog:
    """
    写入一条信号日志（幂等：同一 idempotency_key 不重复写入）
    """
    # 检查是否重复
    existing = await db.execute(
        select(ContribSignalLog).where(
            ContribSignalLog.idempotency_key == req.idempotency_key
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Duplicate signal (idempotency_key already exists)")

    log = ContribSignalLog(
        id=str(uuid.uuid4()),
        task_id=req.task_id,
        node_id=req.node_id,
        holdout_improvement=req.holdout_improvement,
        baseline_accuracy=req.baseline_accuracy,
        final_accuracy=req.final_accuracy,
        sample_count=req.sample_count,
        query_patterns=",".join(req.query_patterns),   # 逗号分隔存储
        total_steps=req.total_steps,
        final_loss=req.final_loss,
        training_time_sec=req.training_time_sec,
        gpu_model=req.gpu_model,
        gpu_vram_gb=req.gpu_vram_gb,
        os_type=req.os_type,
        client_version=req.client_version,
        idempotency_key=req.idempotency_key,
        contribution_estimated=contribution_estimated,
    )
    db.add(log)
    return log


async def is_signal_duplicate(
    db: AsyncSession, idempotency_key: str
) -> bool:
    """检查幂等键是否已存在"""
    result = await db.execute(
        select(ContribSignalLog).where(
            ContribSignalLog.idempotency_key == idempotency_key
        )
    )
    return result.scalar_one_or_none() is not None


async def get_node_signal_stats(
    db: AsyncSession, node_id: str
) -> dict:
    """统计节点累计信号贡献（用于排行榜 / 奖励）"""
    result = await db.execute(
        select(
            sql_func.count(ContribSignalLog.id),
            sql_func.avg(ContribSignalLog.holdout_improvement),
            sql_func.sum(ContribSignalLog.sample_count),
            sql_func.sum(ContribSignalLog.contribution_estimated),
        ).where(ContribSignalLog.node_id == node_id)
    )
    row = result.one_or_none()
    return {
        "total_signals": row[0] or 0,
        "avg_holdout_improvement": round(float(row[1] or 0), 4),
        "total_samples_donated": row[2] or 0,
        "total_contribution_estimated": row[3] or 0,
    }
