"""
firefly-scheduler · Service · Reputation
v0.6 信誉分核心逻辑 + 评分规则

规则体系（v0.6 初始版）：
- 新节点初始：100 分
- 任务完成：+5 分（每成功完成 1 个 task）
- 任务超时：-10 分
- 数据校验失败（轻微）：-5 分
- 提交虚假数据（人工标记）：-50 分
- 连续失败 ≥3 次：-5 分（额外惩罚）
- 最低分：0（封禁参与）；最高分：120（上限）

速率限制：
- 同一节点单次变更最大幅度：-20 / +10（防止刷分）
- 信誉分只升不降机制（仅适用于自动恢复场景）

贡献分与信誉分联动（v0.6）：
- 信誉分 < 60：降低接任务频率（rate_limit_factor = 0.5）
- 信誉分 < 30：禁止认领新任务
- 信誉分 = 0：永久封禁（is_banned=True）
- 信誉分 ≥ 110：解锁 level 3+ 任务权限
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func as sql_func

from app.models.node import Node
from app.models.reputation import ReputationLog
from app.models.task import Task


# ─────────────────────────────────────
# 常量
# ─────────────────────────────────────
SCORE_INIT = 100
SCORE_MIN = 0
SCORE_MAX = 120
SCORE_BAN_THRESHOLD = 0       # ≤ 0 永久封禁
SCORE_DISABLE_THRESHOLD = 30   # < 30 禁止接任务
SCORE_THROTTLE_THRESHOLD = 60  # < 60 降速 50%

# 评分规则
SCORE_TASK_COMPLETE = 5        # 任务成功完成
SCORE_TASK_TIMEOUT = -10       # 任务超时
SCORE_VALIDATION_FAIL = -5     # 数据校验失败（轻微）
SCORE_CHEATING = -50           # 提交虚假数据（人工标记）
SCORE_CONSECUTIVE_FAIL = -5    # 连续失败 ≥3 次

# 变动幅度限制（防止单次刷分）
SCORE_DROP_MAX = -20           # 单次最多扣这么多
SCORE_RISE_MAX = 10            # 单次最多加这么多

# 自动恢复（已有 background_tasks 中 reputation_recovery，但这里也支持主动触发）
SCORE_RECOVERY = 1             # 连续完成 N 任务后自动 +1


# ─────────────────────────────────────
# 核心服务
# ─────────────────────────────────────

async def get_node_score(db: AsyncSession, node_id: str) -> int:
    """查询节点信誉分"""
    result = await db.execute(select(Node.reputation_score).where(Node.id == node_id))
    row = result.scalar_one_or_none()
    return row if row is not None else SCORE_INIT


async def record_delta(
    db: AsyncSession,
    node_id: str,
    delta: int,
    reason: str,
    task_id: Optional[str] = None,
) -> tuple[int, int]:
    """
    记录一次信誉分变动，返回 (score_before, score_after)
    自动裁剪到 [SCORE_MIN, SCORE_MAX] 范围
    """
    # 读取当前分
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        return SCORE_INIT, SCORE_INIT

    score_before = node.reputation_score

    # 裁剪变动幅度
    if delta > SCORE_RISE_MAX:
        delta = SCORE_RISE_MAX
    if delta < SCORE_DROP_MAX:
        delta = SCORE_DROP_MAX

    score_after = max(SCORE_MIN, min(SCORE_MAX, score_before + delta))
    delta_actual = score_after - score_before

    # 写流水
    log = ReputationLog(
        id=str(uuid.uuid4()),
        node_id=node_id,
        task_id=task_id,
        delta=delta_actual,
        score_before=score_before,
        score_after=score_after,
        reason=reason,
    )
    db.add(log)

    # 更新节点分
    node.reputation_score = score_after

    # 触发副作用：封禁检查
    if score_after <= SCORE_BAN_THRESHOLD:
        node.is_banned = True
        node.status = "banned"
        log.reason = f"[BAN] {reason}"

    # 触发副作用：连续失败计数重置（成功时）
    if delta > 0:
        node.consecutive_failures = 0

    return score_before, score_after


async def on_task_complete(
    db: AsyncSession, node_id: str, task_id: str, quality_stars: int = 3
) -> int:
    """
    任务成功完成 → 信誉分 +5（质量优秀可额外 +2）
    quality_stars: 1~5（客户端回报，1=及格，5=优秀）
    """
    # 基础 +5，质量优秀 +2
    bonus = 2 if quality_stars >= 5 else (1 if quality_stars >= 4 else 0)
    delta = SCORE_TASK_COMPLETE + bonus
    _, score_after = await record_delta(db, node_id, delta, f"Task {task_id} completed, stars={quality_stars}", task_id)
    return score_after


async def on_task_timeout(
    db: AsyncSession, node_id: str, task_id: str
) -> int:
    """任务超时 → 信誉分 -10"""
    # 连续失败计数
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if node:
        node.consecutive_failures += 1
        if node.consecutive_failures >= 3:
            await record_delta(db, node_id, SCORE_CONSECUTIVE_FAIL, "Consecutive 3+ failures", task_id)

    _, score_after = await record_delta(db, node_id, SCORE_TASK_TIMEOUT, f"Task {task_id} timeout", task_id)
    return score_after


async def on_task_validation_fail(
    db: AsyncSession, node_id: str, task_id: str
) -> int:
    """数据校验失败 → 信誉分 -5"""
    _, score_after = await record_delta(db, node_id, SCORE_VALIDATION_FAIL, f"Task {task_id} validation failed", task_id)
    return score_after


async def on_task_cheating(
    db: AsyncSession, node_id: str, task_id: str, detail: str = ""
) -> int:
    """提交虚假数据（人工标记）→ 信誉分 -50"""
    _, score_after = await record_delta(
        db, node_id, SCORE_CHEATING,
        f"Task {task_id} cheating: {detail}"[:128], task_id
    )
    return score_after


async def can_claim_task(
    db: AsyncSession, node_id: str
) -> tuple[bool, str]:
    """
    检查节点是否有权认领任务
    返回 (allowed, reason)
    """
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        return False, "Node not found"

    if node.is_banned or node.reputation_score <= SCORE_DISABLE_THRESHOLD:
        return False, f"Reputation {node.reputation_score} <= {SCORE_DISABLE_THRESHOLD}: blocked"

    if node.status == "banned":
        return False, "Node is banned"

    return True, "OK"


async def get_rate_limit_factor(
    db: AsyncSession, node_id: str
) -> float:
    """
    返回节点的限速因子（影响接任务频率）
    - 信誉分 ≥ 60：1.0（正常速度）
    - 信誉分 30~59：0.5（降速）
    - 信誉分 < 30：0（禁止接任务）
    """
    score = await get_node_score(db, node_id)
    if score < SCORE_DISABLE_THRESHOLD:
        return 0.0
    if score < SCORE_THROTTLE_THRESHOLD:
        return 0.5
    return 1.0


async def get_node_reputation_history(
    db: AsyncSession, node_id: str, limit: int = 50
) -> list[ReputationLog]:
    """查询节点的信誉分变动历史"""
    result = await db.execute(
        select(ReputationLog)
        .where(ReputationLog.node_id == node_id)
        .order_by(ReputationLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def admin_adjust_score(
    db: AsyncSession, node_id: str, delta: int, reason: str
) -> tuple[int, int]:
    """
    管理员手动调整信誉分（不受变动幅度限制）
    用于：申诉补偿 / 风控处理 / 测试
    """
    score_before, score_after = await record_delta(
        db, node_id, delta, f"[ADMIN] {reason}", task_id=None
    )
    return score_before, score_after
