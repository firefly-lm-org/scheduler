"""
firefly-scheduler · Redis 工具
连接池 + 常用操作封装（分布式锁、心跳缓存、频率限制）
"""
import redis.asyncio as redis
from app.config import settings


# ── 全局连接池 ──────────────────────
redis_client: redis.Redis = redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


# ── 分布式锁（任务抢占用） ──────────
async def acquire_lock(lock_key: str, expire: int = 10) -> bool:
    """
    尝试获取 Redis 分布式锁（SET NX EX）
    成功返回 True，失败返回 False
    """
    return await redis_client.set(lock_key, "1", nx=True, ex=expire)


async def release_lock(lock_key: str):
    """释放锁"""
    await redis_client.delete(lock_key)


# ── 心跳缓存 ────────────────────────
HEARTBEAT_PREFIX = "node:heartbeat:"
LOCK_PREFIX = "task:lock:"

async def set_heartbeat(node_id: str):
    """记录节点心跳，TTL = 心跳超时时间"""
    key = f"{HEARTBEAT_PREFIX}{node_id}"
    await redis_client.set(key, int(time.time()), ex=settings.task_heartbeat_timeout)


async def is_node_online(node_id: str) -> bool:
    """检查节点是否在心跳超时窗口内"""
    key = f"{HEARTBEAT_PREFIX}{node_id}"
    return await redis_client.exists(key) == 1


# ── 领取频率限制 ────────────────────
async def check_claim_rate(node_id: str) -> bool:
    """
    检查节点领取频率是否超限
    返回 True = 可以领取，False = 需要等待
    """
    key = f"node:claim:{node_id}"
    last = await redis_client.get(key)
    if last is None:
        await redis_client.set(key, "1", ex=settings.task_claim_interval)
        return True
    return False


# 延迟导入 time（避免循环导入）
import time
