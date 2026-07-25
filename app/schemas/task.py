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
    """节点上报训练进度"""
    current_step: int = Field(..., ge=0)
    total_steps: int = Field(..., ge=1)
    loss: Optional[float] = None
    peak_vram_mb: Optional[float] = None


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
