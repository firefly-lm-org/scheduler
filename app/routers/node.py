"""
firefly-scheduler · Router · Node
节点注册 / 心跳 / 状态查询
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.node import Node
from app.models.user import User
from app.schemas.node import NodeRegisterRequest, NodeHeartbeatRequest, NodeResponse
from app.utils.security import decode_token
from app.utils.redis_client import set_heartbeat, is_node_online

router = APIRouter(prefix="/api/v1/node", tags=["Node"])
bearer = HTTPBearer()


# ── 从 JWT 获取当前用户 ──────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    result = await db.execute(User.__table__.select().where(User.id == payload["sub"]))
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── 计算节点最高任务等级 ──────────────
def calc_max_task_level(gpu_vram_gb: float | None) -> int:
    """根据显存自动评定节点等级"""
    if gpu_vram_gb is None or gpu_vram_gb < 4:
        return 1   # L1 仅数据处理
    elif gpu_vram_gb < 8:
        return 2   # L2 轻量微调
    else:
        return 3   # L3 重量微调


@router.post("/register", response_model=NodeResponse)
async def register_node(
    body: NodeRegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """节点首次启动，注册到调度中心"""
    node = Node(
        id=str(uuid.uuid4()),
        user_id=user.id,
        node_name=body.node_name,
        status="offline",
        reputation_score=100,
        max_task_level=calc_max_task_level(body.gpu_vram_gb),
        cpu_cores=body.cpu_cores,
        total_memory_gb=body.total_memory_gb,
        gpu_model=body.gpu_model,
        gpu_vram_gb=body.gpu_vram_gb,
        os_type=body.os_type,
    )
    db.add(node)
    await db.flush()

    return NodeResponse(
        node_id=node.id,
        node_name=node.node_name,
        status=node.status,
        reputation_score=node.reputation_score,
        max_task_level=node.max_task_level,
        last_heartbeat=None,
    )


@router.post("/heartbeat")
async def heartbeat(
    body: NodeHeartbeatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    节点心跳（每 30 秒一次）
    更新 Redis 心跳缓存 + 数据库状态
    """
    # 查找用户的活跃节点（简化为取第一个在线节点）
    result = await db.execute(
        select(Node).where(
            Node.user_id == user.id,
            Node.is_banned == False,
        ).limit(1)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="No active node found")

    # 更新数据库
    node.status = body.status
    node.last_heartbeat = datetime.utcnow()
    if body.status == "offline":
        # 离线不更新心跳缓存
        pass
    else:
        await set_heartbeat(node.id)

    return {"status": "ok", "node_id": node.id}


@router.get("/status", response_model=NodeResponse)
async def node_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户节点的状态"""
    result = await db.execute(
        select(Node).where(Node.user_id == user.id).limit(1)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="No node registered")

    online = await is_node_online(node.id)
    return NodeResponse(
        node_id=node.id,
        node_name=node.node_name,
        status="online" if online else "offline",
        reputation_score=node.reputation_score,
        max_task_level=node.max_task_level,
        last_heartbeat=node.last_heartbeat,
    )
