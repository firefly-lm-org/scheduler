"""
firefly-scheduler · Pydantic Schemas · Task
任务领取 / 进度 / 提交 / 响应
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class TaskClaimResponse(BaseModel):
    """节点领取任务后返回的详情"""
    task_id: str
    task_name: str
    task_level: int
    task_package_url: Optional[str] = None  # 预签名下载链接（无任务包时为 None）
    config: Dict[str, Any]      # 训练超参数等配置
    deadline: datetime          # 最迟完成时间


class TaskProgressRequest(BaseModel):
    """节点上报训练进度（firefly-client v0.2 每10步调用一次）"""
    task_id: Optional[str] = Field(None, description="任务ID，可省略（服务端从 claimed_by 推导）")
    step: int = Field(..., ge=0, alias="current_step", description="当前训练步数")
    total_steps: int = Field(..., ge=1, description="总步数")
    progress_pct: float = Field(0.0, ge=0, le=100, description="进度百分比 0~100")
    loss: Optional[float] = Field(None, description="当前 loss 值")
    peak_vram_mb: Optional[float] = Field(None, description="峰值显存 MB")

    class Config:
        populate_by_name = True  # 允许用 step 或 current_step


class TaskSubmitRequest(BaseModel):
    """节点提交任务结果"""
    result_object_name: str = Field(..., description="MinIO 中的结果对象路径")
    result_sha256: str = Field(..., min_length=64, max_length=64)
    execution_time_sec: float = Field(..., ge=0)
    peak_vram_mb: Optional[float] = None
    total_steps: int = Field(..., ge=0)


class TaskResponse(BaseModel):
    """任务状态查询响应"""
    task_id: str
    status: str
    level: int
    claimed_by: Optional[str] = None
    retry_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None
