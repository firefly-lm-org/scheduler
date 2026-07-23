"""
firefly-scheduler · ORM · ContributionLog
贡献值流水（不可篡改、仅追加）
"""
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ContributionLog(Base):
    __tablename__ = "contribution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="UUID")
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    node_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    amount: Mapped[int] = mapped_column(nullable=False, comment="变动数值（可正可负）")
    type: Mapped[str] = mapped_column(String(16), nullable=False, comment="earn/deduct/adjust")
    reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Contribution {self.amount} type={self.type}>"
