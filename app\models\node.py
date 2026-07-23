"""
firefly-scheduler · ORM · Node
"""
import json
from sqlalchemy import String, Integer, DateTime, Float, Boolean, func, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="UUID")
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False, comment="关联用户")
    node_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="offline", nullable=False,
                                         comment="online/offline/busy/banned")
    reputation_score: Mapped[int] = mapped_column(default=100, nullable=False, comment="信誉分 0~120")
    max_task_level: Mapped[int] = mapped_column(default=1, nullable=False, comment="最高可执行任务等级")

    # ── 硬件信息（JSON 存储） ──
    cpu_cores: Mapped[int] = mapped_column(default=1)
    total_memory_gb: Mapped[float] = mapped_column(default=4.0)
    gpu_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gpu_vram_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    os_type: Mapped[str] = mapped_column(String(32), default="unknown")

    # ── 运行时信息 ──
    last_heartbeat: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(default=0, comment="连续失败次数")
    total_tasks_completed: Mapped[int] = mapped_column(default=0)
    is_banned: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Node {self.node_name} status={self.status}>"
