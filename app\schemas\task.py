"""task 请求/响应 Pydantic 模型."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import hashlib, re


class TaskCreateRequest(BaseModel):
    name: str = Field(..., max_length=200)
    level: int = Field(default=1, ge=1, le=3)
    base_contribution: int = Field(default=10, ge=1)
    timeout_sec: int = Field(default=3600, ge=60, le=86400)
    config: Optional[dict] = None


class TaskClaimResponse(BaseModel):
    task_id: str
    name: str
    level: int
    base_contribution: int
    timeout_sec: int
    config: Optional[dict]
    started_at: Optional[datetime]


class TaskProgressRequest(BaseModel):
    task_id: str
    progress_pct: int = Field(ge=0, le=100)


class TaskSubmitRequest(BaseModel):
    task_id: str
    result_url: str = Field(..., description="MinIO 预签名下载 URL")
    result_hash: Optional[str] = Field(
        default=None,
        description="结果文件 SHA256 (可选但强烈建议填入)"
    )

    @field_validator("result_hash")
    @classmethod
    def validate_hash(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.fullmatch(r"[a-fA-F0-9]{64}", v):
            raise ValueError("result_hash must be a 64-char lowercase hex SHA256")
        return v.lower() if v else None


class TaskRead(BaseModel):
    id: str
    name: str
    level: int
    base_contribution: int
    status: str
    claimed_by_node_id: Optional[str]
    claimed_by_user_id: Optional[str]
    result_url: Optional[str]
    result_hash: Optional[str]
    retry_count: int
    timeout_sec: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
