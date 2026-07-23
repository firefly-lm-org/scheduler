"""后台任务：超时回收 + 离线检测 + 信誉恢复."""
import asyncio, logging, uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.task import Task, TaskStatus
from app.models.node import Node, NodeStatus

settings = get_settings()
logger = logging.getLogger(__name__)


async def _db():
    async with AsyncSessionLocal() as s:
        return s


async def reclaim_timed_out_tasks() -> int:
    """将超时的 running 任务回退为 pending，释放节点锁."""
    async with AsyncSessionLocal() as s:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.task_run_ttl_sec)
        result = await s.execute(
            update(Task)
            .where(Task.status == TaskStatus.RUNNING, Task.started_at < cutoff)
            .values(status=TaskStatus.PENDING, claimed_by_node_id=None, claimed_by_user_id=None,
                    started_at=None, running_lock_key=None)
        )
        await s.commit()
        n = result.rowcount
        if n:
            logger.warning("Reclaimed %d timed-out running tasks", n)
        return n


async def detect_offline_nodes() -> int:
    """心跳超时 → offline."""
    async with AsyncSessionLocal() as s:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.node_offline_sec)
        result = await s.execute(
            update(Node)
            .where(Node.status == NodeStatus.ONLINE, Node.last_heartbeat < cutoff)
            .values(status=NodeStatus.OFFLINE)
        )
        await s.commit()
        n = result.rowcount
        if n:
            logger.info("Marked %d nodes offline", n)
        return n


async def recover_node_reputation() -> int:
    """每6h恢复节点信誉分，上限100."""
    async with AsyncSessionLocal() as s:
        result = await s.execute(
            select(Node).where(Node.reputation_score < 100.0)
        )
        nodes = result.scalars().all()
        count = 0
        for node in nodes:
            node.reputation_score = min(100.0, node.reputation_score + 1.0)
            count += 1
        await s.commit()
        if count:
            logger.info("Recovered reputation for %d nodes", count)
        return count


async def background_scheduler_loop():
    """每60s 执行一次清理扫描."""
    while True:
        try:
            await reclaim_timed_out_tasks()
            await detect_offline_nodes()
            await recover_node_reputation()
        except Exception as exc:
            logger.error("Background task error: %s", exc)
        await asyncio.sleep(60)
