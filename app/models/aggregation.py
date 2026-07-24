"""
firefly-scheduler · ORM · Aggregation Record
权重聚合记录表
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AggregationRecord(Base):
    """
    记录每次权重聚合的元数据。
    status: pending → running → completed / failed
    """
    __tablename__ = "aggregation_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_version: Mapped[str] = mapped_column(String(64), index=True)
    aggregation_key: Mapped[str] = mapped_column(String(256), index=True)

    num_participants: Mapped[int] = mapped_column(Integer, default=0)
    num_tasks: Mapped[int] = mapped_column(Integer, default=0)

    aggregated_checkpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    aggregated_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[str] = mapped_column(
        String(16), default="pending",
        comment="pending/running/completed/failed"
    )

    total_contribution_settled: Mapped[float] = mapped_column(Float, default=0.0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AggregationRecord {self.id[:8]} "
            f"model={self.model_version} status={self.status}>"
        )
