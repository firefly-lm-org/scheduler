"""
firefly-scheduler · Schemas · Signal
v0.6 信号回流协议请求/响应
"""
from pydantic import BaseModel, Field
from typing import Optional


class ContribSignalRequest(BaseModel):
    """节点上报贡献信号"""
    task_id: str
    node_id: str
    holdout_improvement: float = Field(0.0, ge=-1.0, le=1.0, description="相对基准的准确率提升")
    baseline_accuracy: float = Field(0.0, ge=0.0, le=1.0)
    final_accuracy: float = Field(0.0, ge=0.0, le=1.0)
    sample_count: int = Field(0, ge=0, le=1000, description="授权脱敏样本数")
    query_patterns: list[str] = Field(default_factory=list, max_length=50,
                                       description="min-hash 指纹列表（已去标识化）")
    total_steps: int = Field(0, ge=0)
    final_loss: float = Field(0.0, ge=0.0)
    training_time_sec: float = Field(0.0, ge=0.0)
    gpu_model: str = ""
    gpu_vram_gb: float = Field(0.0, ge=0.0)
    os_type: str = ""
    client_version: str = "0.6"
    idempotency_key: str = Field(..., description="防重复上报的幂等键")


class ContribSignalResponse(BaseModel):
    """信号接收确认"""
    task_id: str
    status: str            # "accepted" | "duplicate" | "error"
    contribution_estimated: int = Field(0, description="估算的额外贡献积分（仅供参考）")
    message: str = ""
