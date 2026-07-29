"""
firefly-scheduler · ORM · Reputation
v0.6 信誉分系统数据模型
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ReputationLog(Base):
    """
    信誉分变动流水（不可篡改，仅追加）
    用途：节点申诉依据 / 风控审计 / 历史排名
    """
    __tablename__ = "reputation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    node_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    task_id: Mapped[str] = mapped_column(String(36), nullable=True, comment="关联任务（可选）")

    # 变动
    delta: Mapped[int] = mapped_column(nullable=False, comment="本次变动值，正负均可")
    score_before: Mapped[int] = mapped_column(nullable=False)
    score_after: Mapped[int] = mapped_column(nullable=False)

    reason: Mapped[str] = mapped_column(String(128), nullable=False, comment="变动原因")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
