"""node 请求/响应 Pydantic 模型."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NodeRegisterRequest(BaseModel):
    node_name: str = Field(..., max_length=100)
    cpu_cores: int = Field(ge=1)
    total_memory_gb: int = Field(ge=1)
    gpu_model: str = Field(default="", max_length=100)
    gpu_vram_gb: int = Field(default=0, ge=0)
    os_type: str = Field(default="", max_length=50)


class NodeHeartbeatRequest(BaseModel):
    node_id: str


class NodeRead(BaseModel):
    id: str
    user_id: str
    node_name: str
    status: str
    level: int
    reputation_score: float
    cpu_cores: int
    total_memory_gb: int
    gpu_model: str
    gpu_vram_gb: int
    os_type: str
    last_heartbeat: Optional[datetime]
    created_at: datetime
