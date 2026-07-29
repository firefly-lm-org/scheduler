"""
firefly-scheduler · Router · Signal
v0.6 信号回流 API
POST /api/v1/contrib/signal   接收节点贡献信号
GET  /api/v1/contrib/stats/{node_id}  查询节点信号统计
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.models.node import Node
from app.schemas.signal import ContribSignalRequest, ContribSignalResponse
from app.services import signal_service
from app.utils.security import decode_token

router = APIRouter(prefix="/api/v1/contrib", tags=["Contribution · Signal"])


@router.post("/signal", response_model=ContribSignalResponse)
async def receive_signal(
    body: ContribSignalRequest,
    db = Depends(get_db),
):
    """
    接收节点上报的贡献信号（幂等）
    - 同一 idempotency_key 只记录一次
    - 不影响任务状态，仅记录信号
    """
    # 幂等检查
    is_dup = await signal_service.is_signal_duplicate(db, body.idempotency_key)
    if is_dup:
        return ContribSignalResponse(
            task_id=body.task_id,
            status="duplicate",
            contribution_estimated=0,
            message="Signal already received",
        )

    # 节点存在性校验（警告，不阻断）
    node = await db.get(Node, body.node_id)
    if not node:
        # 不阻断，但记录警告
        pass

    # 估算贡献
    estimated = signal_service.estimate_contribution(body)

    # 写入日志
    try:
        await signal_service.record_signal(db, body, contribution_estimated=estimated)
        await db.commit()
    except ValueError:
        # 幂等冲突（并发场景）
        return ContribSignalResponse(
            task_id=body.task_id,
            status="duplicate",
            contribution_estimated=0,
            message="Concurrent duplicate detected",
        )

    return ContribSignalResponse(
        task_id=body.task_id,
        status="accepted",
        contribution_estimated=estimated,
        message=f"Signal recorded, estimated +{estimated} contribution points",
    )


@router.get("/stats/{node_id}")
async def get_signal_stats(
    node_id: str,
    db = Depends(get_db),
):
    """查询节点的信号贡献统计"""
    stats = await signal_service.get_node_signal_stats(db, node_id)
    return {"node_id": node_id, **stats}
