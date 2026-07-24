"""
firefly-scheduler · Pydantic Schemas · Node
节点注册 / 心跳 / 状态响应
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class NodeRegisterRequest(BaseModel):
    """节点首次启动，上报硬件信息"""
    node_name: str = Field(..., min_length=1, max_length=64)
    cpu_cores: int = Field(..., ge=1, le=256)
    total_memory_gb: float = Field(..., ge=0.5, le=1024)
    gpu_model: Optional[str] = None
    gpu_vram_gb: Optional[float] = Field(None, ge=0, le=256)
    os_type: str = Field(..., max_length=32)  # Windows / Linux / macOS


class NodeHeartbeatRequest(BaseModel):
    """心跳上报，附带当前状态"""
    status: str = Field(..., pattern=r"^(online|busy|offline)$")
    cpu_usage: Optional[float] = None
    gpu_usage: Optional[float] = None


class NodeResponse(BaseModel):
    """节点信息响应"""
    node_id: str
    node_name: str
    status: str
    reputation_score: int
    max_task_level: int
    last_heartbeat: Optional[datetime]
