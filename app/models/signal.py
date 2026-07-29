"""
firefly-scheduler · ORM · Signal
v0.6 信号回流数据模型
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ContribSignalLog(Base):
    """
    节点贡献信号日志（不可篡改，仅追加）
    用途：信号回流存储 / 贡献排行榜 / 调度优化数据
    """
    __tablename__ = "contrib_signal_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    node_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    # 训练质量信号
    holdout_improvement: Mapped[float] = mapped_column(Float, default=0.0)
    baseline_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    final_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    query_patterns: Mapped[str] = mapped_column(Text, nullable=True, comment="逗号分隔的 min-hash 指纹")

    # 训练过程
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    final_loss: Mapped[float] = mapped_column(Float, default=0.0)
    training_time_sec: Mapped[float] = mapped_column(Float, default=0.0)

    # 硬件环境
    gpu_model: Mapped[str] = mapped_column(String(128), nullable=True)
    gpu_vram_gb: Mapped[float] = mapped_column(Float, nullable=True)
    os_type: Mapped[str] = mapped_column(String(32), nullable=True)

    # 版本 & 幂等
    client_version: Mapped[str] = mapped_column(String(16), default="0.6")
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    contribution_estimated: Mapped[int] = mapped_column(Integer, default=0, comment="估算贡献积分")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
