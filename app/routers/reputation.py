"""
firefly-scheduler · Router · Reputation
v0.6 信誉分 API
GET  /api/v1/reputation/{node_id}          查信誉分
GET  /api/v1/reputation/{node_id}/history  查变动历史
POST /api/v1/reputation/{node_id}/adjust   管理员手动调整
GET  /api/v1/reputation/{node_id}/can_claim  查询是否能接任务
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.node import Node
from app.services import reputation_service
from app.utils.security import decode_token

router = APIRouter(prefix="/api/v1/reputation", tags=["Reputation"])


# ── Schemas ──────────────────────────

class ReputationScoreResponse(BaseModel):
    node_id: str
    score: int
    is_banned: bool
    status: str
    can_claim: bool
    rate_limit_factor: float
    level_cap: int  # 最高可接任务等级

class ReputationHistoryItem(BaseModel):
    id: str
    delta: int
    score_before: int
    score_after: int
    reason: str
    task_id: str | None
    created_at: str

class ReputationHistoryResponse(BaseModel):
    node_id: str
    score: int
    history: list[ReputationHistoryItem]

class ReputationAdjustRequest(BaseModel):
    delta: int
    reason: str

class ReputationAdjustResponse(BaseModel):
    node_id: str
    score_before: int
    score_after: int
    reason: str


# ── 路由实现 ──────────────────────────

@router.get("/{node_id}", response_model=ReputationScoreResponse)
async def get_reputation(
    node_id: str,
    db: AsyncSession = Depends(get_db),
):
    """查询节点当前信誉分及相关状态"""
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    can_claim, _ = await reputation_service.can_claim_task(db, node_id)
    rate_factor = await reputation_service.get_rate_limit_factor(db, node_id)

    # 信誉分决定可接任务等级
    score = node.reputation_score
    level_cap = 1
    if score >= 110:
        level_cap = 3
    elif score >= 100:
        level_cap = 2

    return ReputationScoreResponse(
        node_id=node_id,
        score=score,
        is_banned=node.is_banned,
        status=node.status,
        can_claim=can_claim,
        rate_limit_factor=rate_factor,
        level_cap=level_cap,
    )


@router.get("/{node_id}/history", response_model=ReputationHistoryResponse)
async def get_reputation_history(
    node_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """查询节点信誉分变动历史（最近 N 条）"""
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    logs = await reputation_service.get_node_reputation_history(db, node_id, limit=limit)
    return ReputationHistoryResponse(
        node_id=node_id,
        score=node.reputation_score,
        history=[
            ReputationHistoryItem(
                id=log.id,
                delta=log.delta,
                score_before=log.score_before,
                score_after=log.score_after,
                reason=log.reason,
                task_id=log.task_id,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ],
    )


@router.post("/{node_id}/adjust", response_model=ReputationAdjustResponse)
async def adjust_reputation(
    node_id: str,
    body: ReputationAdjustRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(decode_token),  # 需要认证（管理员）
):
    """
    管理员手动调整节点信誉分
    不受单次变动幅度限制（管理员有完整权限）
    """
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    score_before, score_after = await reputation_service.admin_adjust_score(
        db, node_id, body.delta, body.reason
    )
    await db.commit()

    return ReputationAdjustResponse(
        node_id=node_id,
        score_before=score_before,
        score_after=score_after,
        reason=body.reason,
    )


@router.get("/{node_id}/can_claim")
async def check_can_claim(
    node_id: str,
    db: AsyncSession = Depends(get_db),
):
    """快速查询节点是否能接任务（不含认证，供客户端轮询）"""
    can_claim, reason = await reputation_service.can_claim_task(db, node_id)
    score = await reputation_service.get_node_score(db, node_id)
    return {
        "node_id": node_id,
        "can_claim": can_claim,
        "reason": reason,
        "score": score,
        "rate_limit_factor": await reputation_service.get_rate_limit_factor(db, node_id),
    }
