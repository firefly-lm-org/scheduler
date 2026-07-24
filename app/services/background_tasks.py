"""
firefly-scheduler · Background Tasks
周期性任务：超时回收 / 心跳检测 / 信誉恢复 / 权重聚合轮询
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, update

from app.database import engine
from app.models.task import Task
from app.models.node import Node
from app.config import settings

# 独立会话工厂（后台任务用）
BackgroundSession = async_sessionmaker(engine, expire_on_commit=False)


# ─────────────────────────────────────
# 任务1：超时任务回收
# 每 60 秒扫描一次 claimed/running 超过 timeout 的任务
# ─────────────────────────────────────
async def timeout_reclaimer():
    """将超时的任务释放回 pending 队列"""
    while True:
        try:
            async with BackgroundSession() as db:
                timeout_threshold = datetime.utcnow() - timedelta(seconds=settings.task_heartbeat_timeout * 2)
                # 查找超时任务
                result = await db.execute(
                    select(Task).where(
                        Task.status.in_(["claimed", "running"]),
                        Task.claimed_at < timeout_threshold,
                    ).limit(50)
                )
                expired_tasks = result.scalars().all()

                for task in expired_tasks:
                    task.retry_count += 1
                    if task.retry_count >= task.max_retries:
                        task.status = "failed"
                    else:
                        task.status = "pending"
                        task.claimed_by = None
                        task.claimed_at = None
                    await db.flush()

                if expired_tasks:
                    print(f"[Reclaimer] Reclaimed {len(expired_tasks)} timed-out tasks")

                await db.commit()
        except Exception as e:
            print(f"[Reclaimer] Error: {e}")

        await asyncio.sleep(60)


# ─────────────────────────────────────
# 任务2：离线节点检测
# 每 30 秒检测 Redis 心跳，超时则标记 offline
# ─────────────────────────────────────
async def offline_detector():
    """心跳超时 → 标记节点 offline（不扣信誉分）"""
    import redis.asyncio as redis
    r = redis.from_url(settings.redis_url, decode_responses=True)

    while True:
        try:
            async with BackgroundSession() as db:
                # 查找所有 online/busy 节点
                result = await db.execute(
                    select(Node).where(Node.status.in_(["online", "busy"]))
                )
                nodes = result.scalars().all()

                for node in nodes:
                    exists = await r.exists(f"node:heartbeat:{node.id}")
                    if not exists:
                        node.status = "offline"
                        await db.flush()

                await db.commit()
        except Exception as e:
            print(f"[OfflineDetector] Error: {e}")

        await asyncio.sleep(30)


# ─────────────────────────────────────
# 任务3：信誉分恢复
# 每 6 小时，连续完成 10 个任务的节点 +1 信誉分（上限 100）
# ─────────────────────────────────────
async def reputation_recovery():
    """信誉分缓慢恢复机制"""
    while True:
        try:
            async with BackgroundSession() as db:
                # 查找信誉分 < 100 且近期有完成记录的节点
                result = await db.execute(
                    select(Node).where(
                        Node.reputation_score < 100,
                        Node.total_tasks_completed >= 10,
                    ).limit(50)
                )
                nodes = result.scalars().all()

                for node in nodes:
                    node.reputation_score = min(100, node.reputation_score + 1)
                    await db.flush()

                if nodes:
                    print(f"[Reputation] Recovered {len(nodes)} nodes")

                await db.commit()
        except Exception as e:
            print(f"[Reputation] Error: {e}")

        # 6 小时
        await asyncio.sleep(6 * 3600)


# ─────────────────────────────────────
# 任务4：权重聚合轮询（Weight Aggregation Loop）
# 每 aggregation_interval_sec 秒检查一次是否达到聚合阈值
# ─────────────────────────────────────
async def aggregation_loop():
    """
    权重聚合轮询协程：
    1. 每 N 秒调用 find_ready_aggregation 检测就绪组
    2. 对达到阈值的组执行完整聚合流程
    3. 结算贡献积分，标记任务状态
    """
    while True:
        try:
            async with BackgroundSession() as db:
                from app.services.aggregation_service import run_pending_aggregations

                results = await run_pending_aggregations(db)
                if results:
                    print(f"[AggregationLoop] Completed {len(results)} aggregation(s)")
        except Exception as e:
            print(f"[AggregationLoop] Error: {e}")

        await asyncio.sleep(settings.aggregation_interval_sec)
