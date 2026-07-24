"""
firefly-scheduler · ORM · Task
"""
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Float, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="UUID")
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    level: Mapped[int] = mapped_column(default=1, nullable=False, comment="1=L1轻量 2=L2中量 3=L3重量")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True,
                                         comment="pending/claimed/running/completed/failed/archived")

    # ── 领取与执行 ──
    claimed_by: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    claimed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── 重试与超时 ──
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)
    timeout_sec: Mapped[int] = mapped_column(default=3600, comment="任务超时秒数")

    # ── 贡献与配置 ──
    base_contribution: Mapped[int] = mapped_column(default=10, comment="基础贡献值")
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="训练超参数 JSON")

    # ── 任务包与结果 ──
    task_package_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_object_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # ── 校验结果 ──
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="三级校验质量系数")
    validation_passed: Mapped[bool] = mapped_column(default=False)

    # ── 聚合相关字段 ──
    model_version: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True, default="v0.1",
        comment="模型版本，用于同版本任务的权重聚合"
    )
    aggregation_key: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, index=True,
        comment="聚合分组键，同 key 的任务将被聚合在一起"
    )

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Task {self.id} level={self.level} status={self.status}>"
