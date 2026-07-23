"""node 路由：节点注册 + 心跳 + 查询."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.node import Node, NodeStatus
from app.schemas.node import NodeRegisterRequest, NodeHeartbeatRequest, NodeRead
from app.utils.security import decode_token
from app.utils.redis_client import get_redis, RateLimiter
from app.config import get_settings

router = APIRouter(prefix="/node", tags=["node"])
settings_cfg = get_settings()


def _get_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    payload = decode_token(auth[7:])
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    return payload


def _auto_level(cpu_cores: int, gpu_vram_gb: int) -> int:
    if gpu_vram_gb >= 24:
        return 3
    elif gpu_vram_gb >= 8 or cpu_cores >= 16:
        return 2
    return 1


@router.post("/register", response_model=NodeRead)
async def register_node(
    body: NodeRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = _get_user(request)
    user_id = uuid.UUID(payload["sub"])

    node = Node(
        user_id=user_id,
        node_name=body.node_name,
        cpu_cores=body.cpu_cores,
        total_memory_gb=body.total_memory_gb,
        gpu_model=body.gpu_model or "",
        gpu_vram_gb=body.gpu_vram_gb or 0,
        os_type=body.os_type or "",
        status=NodeStatus.ONLINE,
        last_heartbeat=datetime.now(timezone.utc),
        level=_auto_level(body.cpu_cores, body.gpu_vram_gb),
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return NodeRead(
        id=str(node.id), user_id=str(node.user_id), node_name=node.node_name,
        status=node.status.value, level=node.level,
        reputation_score=node.reputation_score,
        cpu_cores=node.cpu_cores, total_memory_gb=node.total_memory_gb,
        gpu_model=node.gpu_model, gpu_vram_gb=node.gpu_vram_gb,
        os_type=node.os_type, last_heartbeat=node.last_heartbeat,
        created_at=node.created_at,
    )


@router.post("/heartbeat")
async def heartbeat(
    body: NodeHeartbeatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = _get_user(request)
    async with get_redis() as r:
        limiter = RateLimiter(r, f"hb:{body.node_id}", settings_cfg.rate_limit_heartbeat_per_min)
        if not await limiter.is_allowed():
            raise HTTPException(429, "心跳频率超限")

    result = await db.execute(select(Node).where(Node.id == uuid.UUID(body.node_id)))
    node: Node | None = result.scalar_one_or_none()
    if not node:
        raise HTTPException(404, "节点不存在")
    if str(node.user_id) != payload["sub"]:
        raise HTTPException(403, "不属于你的节点")

    node.last_heartbeat = datetime.now(timezone.utc)
    if node.status == NodeStatus.OFFLINE:
        node.status = NodeStatus.ONLINE
    await db.commit()
    return {"ok": True, "last_heartbeat": node.last_heartbeat}


@router.get("/me", response_model=list[NodeRead])
async def list_my_nodes(request: Request, db: AsyncSession = Depends(get_db)):
    payload = _get_user(request)
    result = await db.execute(
        select(Node).where(Node.user_id == uuid.UUID(payload["sub"])).order_by(Node.created_at.desc())
    )
    nodes = result.scalars().all()
    return [
        NodeRead(
            id=str(n.id), user_id=str(n.user_id), node_name=n.node_name,
            status=n.status.value, level=n.level, reputation_score=n.reputation_score,
            cpu_cores=n.cpu_cores, total_memory_gb=n.total_memory_gb,
            gpu_model=n.gpu_model, gpu_vram_gb=n.gpu_vram_gb,
            os_type=n.os_type, last_heartbeat=n.last_heartbeat, created_at=n.created_at,
        )
        for n in nodes
    ]
