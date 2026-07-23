"""贡献值结算服务."""
import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.contribution import ContributionLog

logger = logging.getLogger(__name__)


async def settle_contribution(
    session: AsyncSession,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
    amount: int,
    reason: str,
) -> int:
    """
    原子积分增减：SELECT FOR UPDATE → 更新余额 → 写流水.
    返回扣减后的余额。
    """
    result = await session.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    user: User | None = result.scalar_one_or_none()
    if not user:
        raise ValueError(f"User {user_id} not found")

    user.contribution_balance += amount
    balance_after = user.contribution_balance

    log = ContributionLog(
        user_id=user_id,
        task_id=task_id,
        amount=amount,
        balance_after=balance_after,
        reason=reason,
    )
    session.add(log)
    await session.commit()
    logger.info("Contribution settled: user=%s amount=%+d reason=%s", user_id, amount, reason)
    return balance_after
