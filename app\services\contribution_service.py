"""贡献值结算服务（适配 zip ORM：str 主键 + total_contribution）."""
import logging
import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.contribution import ContributionLog

logger = logging.getLogger(__name__)


async def settle_contribution(
    session: AsyncSession,
    user_id: str,
    task_id: str,
    amount: int,
    contrib_type: str = "earn",
    reason: str = "",
) -> int:
    """
    原子积分结算：SELECT FOR UPDATE → 累加 → 写流水（不可篡改）。
    返回更新后的 total_contribution。
    """
    # 行锁
    result = await session.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    user: User | None = result.scalar_one_or_none()
    if not user:
        raise ValueError(f"User {user_id} not found")

    user.total_contribution += amount
    balance_after = user.total_contribution

    # 写流水（append-only，不可改）
    log = ContributionLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        task_id=task_id,
        amount=amount,
        type=contrib_type,
        reason=reason,
    )
    session.add(log)
    await session.commit()
    logger.info(
        "Contribution settled: user=%s amount=%+d reason=%s balance=%d",
        user_id, amount, reason, balance_after,
    )
    return balance_after
