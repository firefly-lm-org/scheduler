"""
firefly-scheduler · Service · Contribution
贡献值结算 + 流水记录
v0.1 简化版：仅按基础值结算
v0.5+ 扩展：加入硬件系数 × 质量系数
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.contribution import ContributionLog
from app.models.task import Task
from app.models.node import Node


# ─────────────────────────────────────
# 核心结算函数
# ─────────────────────────────────────
async def settle_contribution(
    db: AsyncSession,
    task: Task,
    node: Node,
    quality_coefficient: float = 1.0,
) -> int:
    """
    结算任务贡献值
    公式（v0.1 简化）：final = base × quality_coefficient
    公式（v0.5 完整）：final = base × hardware_coef × quality_coefficient
    """
    # 硬件系数（v0.1 暂固定为 1.0）
    hardware_coefficient = 1.0

    # 计算最终贡献值
    amount = int(task.base_contribution * hardware_coefficient * quality_coefficient)

    # 写入流水（不可篡改，仅追加）
    log = ContributionLog(
        id=str(uuid.uuid4()),
        user_id=node.user_id,
        node_id=node.id,
        task_id=task.id,
        amount=amount,
        type="earn",
        reason=f"Task {task.id} completed, level={task.level}",
    )
    db.add(log)

    # 更新用户累计贡献值
    await db.execute(
        update(Node.__table__)
        .where(Node.id == node.id)
        .values(total_tasks_completed=Node.total_tasks_completed + 1)
    )

    # 注意：user.total_contribution 的更新需要在上层 join 后统一 flush
    return amount


# ─────────────────────────────────────
# 扣除贡献值（校验失败/作弊用）
# ─────────────────────────────────────
async def deduct_contribution(
    db: AsyncSession,
    node: Node,
    task: Task,
    amount: int,
    reason: str = "Validation failed",
):
    """记录一笔负贡献流水"""
    log = ContributionLog(
        id=str(uuid.uuid4()),
        user_id=node.user_id,
        node_id=node.id,
        task_id=task.id,
        amount=-abs(amount),
        type="deduct",
        reason=reason,
    )
    db.add(log)
    return log
