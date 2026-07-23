"""contribution Pydantic 模型."""
from datetime import datetime
from pydantic import BaseModel


class ContributionLogRead(BaseModel):
    id: str
    task_id: str | None
    amount: int
    balance_after: int
    reason: str | None
    created_at: datetime


class ContributionsSummary(BaseModel):
    user_id: str
    username: str
    balance: int
    logs: list[ContributionLogRead]
