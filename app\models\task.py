"""tasks 表：训练任务状态机载体."""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Enum as SAEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1)          # 1-3
    base_contribution: Mapped[int] = mapped_column(Integer, default=10)

    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus), default=TaskStatus.PENDING, server_default="pending"
    )

    # Redis key holders (for cleanup / TTL tracking)
    claim_lock_key: Mapped[str] = mapped_column(String(255), nullable=True)
    running_lock_key: Mapped[str] = mapped_column(String(255), nullable=True)

    # Who holds this task
    claimed_by_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nodes.id"), nullable=True)
    claimed_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Result
    result_url: Mapped[str] = mapped_column(Text, nullable=True)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=True)   # SHA256
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timing
    timeout_sec: Mapped[int] = mapped_column(Integer, default=3600)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Admin metadata
    config: Mapped[dict] = mapped_column(JSON, nullable=True)
