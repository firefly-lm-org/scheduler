"""nodes 表：计算节点，含硬件信息 + 信誉分."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class NodeStatus(str, enum.Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    BANNED = "banned"


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Hardware
    cpu_cores: Mapped[int] = mapped_column(Integer, default=0)
    total_memory_gb: Mapped[int] = mapped_column(Integer, default=0)
    gpu_model: Mapped[str] = mapped_column(String(100), default="")
    gpu_vram_gb: Mapped[int] = mapped_column(Integer, default=0)
    os_type: Mapped[str] = mapped_column(String(50), default="")

    # Status
    status: Mapped[NodeStatus] = mapped_column(
        Enum(NodeStatus), default=NodeStatus.OFFLINE, server_default="offline"
    )
    reputation_score: Mapped[float] = mapped_column(Float, default=100.0)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Auto-set on register
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    level: Mapped[int] = mapped_column(Integer, default=1)   # 1-3, set by auto-tier logic
