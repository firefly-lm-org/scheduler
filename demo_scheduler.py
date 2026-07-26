"""
firefly · DEMO Scheduler（本机链路验证专用）
=================================================
零依赖：内存存储 + 无 auth，仅用于验证
  claim → progress → complete
全链路。不覆盖现有 PostgreSQL/Redis 版 scheduler。

启动:
    python demo_scheduler.py        # 监听 0.0.0.0:8000
"""
import time
import uuid
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("firefly.demo.scheduler")

# ── 内存存储（v0.3 demo：验证后迁移到 PostgreSQL）──
_task_pool: Dict[str, dict] = {}
_task_queue: list = []  # 待认领任务 id 列表


# ── 请求模型 ──
class CreateTaskRequest(BaseModel):
    model_path: str = "Qwen2.5-1.5B-Instruct"
    dataset_path: Optional[str] = None
    hyperparams: Optional[Dict[str, Any]] = None
    round_id: int = 1


class ProgressRequest(BaseModel):
    task_id: str
    step: int
    loss: float
    lr: Optional[float] = None
    eta_seconds: Optional[float] = None


class CompleteRequest(BaseModel):
    task_id: str
    loss: float
    weights_path: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


# ── 种子任务 ──
def seed_demo_tasks():
    domains = [
        ("law",     "data/law_qa.jsonl"),
        ("medical", "data/medical_qa.jsonl"),
        ("python",  "data/python_qa.jsonl"),
        ("tax",     "data/tax_qa.jsonl"),
    ]
    for i, (name, ds) in enumerate(domains):
        tid = f"demo-task-{i+1:03d}"
        task = {
            "task_id": tid,
            "model_path": "Qwen2.5-1.5B-Instruct",
            "dataset_path": ds,
            "hyperparams": {"lora_r": 8, "max_steps": 60},
            "round_id": 1,
            "status": "pending",
            "assigned_to": None,
            "created_at": time.time(),
            "started_at": None,
            "completed_at": None,
            "progress": {},
            "result": {},
        }
        _task_pool[tid] = task
        _task_queue.append(tid)
    logger.info(f"[Seed] 创建 {len(domains)} 个 demo 任务（法律/医疗/Python/财税）")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("Firefly DEMO Scheduler starting (in-memory, no-auth)")
    seed_demo_tasks()
    logger.info("=" * 50)
    yield


app = FastAPI(title="Firefly Demo Scheduler", version="0.3-demo", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "firefly-demo-scheduler",
        "pending": len(_task_queue),
        "total": len(_task_pool),
    }


@app.post("/api/v1/task/create")
def create_task(req: CreateTaskRequest):
    tid = f"task-{uuid.uuid4().hex[:12]}"
    task = {
        "task_id": tid,
        "model_path": req.model_path,
        "dataset_path": req.dataset_path,
        "hyperparams": req.hyperparams or {"lora_r": 8, "max_steps": 60},
        "round_id": req.round_id,
        "status": "pending",
        "assigned_to": None,
        "created_at": time.time(),
        "started_at": None,
        "completed_at": None,
        "progress": {},
        "result": {},
    }
    _task_pool[tid] = task
    _task_queue.append(tid)
    logger.info(f"[Create] {tid}")
    return {"status": "created", "task_id": tid}


@app.post("/api/v1/task/claim")
async def claim_task(request: Request):
    """客户端认领一个 pending 任务（无 auth）"""
    if not _task_queue:
        return {"status": "no_task", "task_id": None}

    tid = _task_queue.pop(0)
    task = _task_pool[tid]
    if task["status"] != "pending":
        return {"status": "no_task", "task_id": None}

    task["status"] = "running"
    task["assigned_to"] = request.client.host
    task["started_at"] = time.time()
    logger.info(f"[Claim] {tid} -> {task['assigned_to']}")
    return {
        "status": "claimed",
        "task_id": tid,
        "model_path": task["model_path"],
        "dataset_path": task["dataset_path"],
        "hyperparams": task["hyperparams"],
        "round_id": task["round_id"],
    }


@app.post("/api/v1/task/progress")
def report_progress(req: ProgressRequest):
    """客户端每 N 步上报训练进度"""
    task = _task_pool.get(req.task_id)
    if not task:
        return {"status": "error", "msg": "task not found"}
    task["progress"] = {
        "step": req.step,
        "loss": req.loss,
        "lr": req.lr,
        "eta_seconds": req.eta_seconds,
        "reported_at": time.time(),
    }
    logger.info(f"[Progress] {req.task_id} step={req.step} loss={req.loss:.4f}")
    return {"status": "ok"}


@app.post("/api/v1/task/complete")
def complete_task(req: CompleteRequest):
    """客户端报告训练完成，回传权重信息"""
    task = _task_pool.get(req.task_id)
    if not task:
        return {"status": "error", "msg": "task not found"}
    task["status"] = "completed"
    task["completed_at"] = time.time()
    task["result"] = {
        "loss": req.loss,
        "weights_path": req.weights_path,
        "meta": req.meta or {},
    }
    elapsed = (task["completed_at"] - task["started_at"]) if task["started_at"] else 0
    logger.info(f"[Complete] {req.task_id} loss={req.loss:.4f} elapsed={elapsed:.1f}s")

    # 检查本轮是否全部完成（v0.3 预演聚合触发）
    _maybe_aggregate(task["round_id"])
    return {"status": "completed", "task_id": req.task_id}


def _maybe_aggregate(round_id: int):
    round_tasks = [t for t in _task_pool.values() if t["round_id"] == round_id]
    completed = [t for t in round_tasks if t["status"] == "completed"]
    if len(completed) == len(round_tasks) and round_tasks:
        logger.info(
            f"[Aggregate] round={round_id} 全部完成 "
            f"({len(completed)}/{len(round_tasks)}) → 触发聚合（v0.5 实现 FedAvg）"
        )


@app.get("/api/v1/task/list")
def list_tasks():
    return {
        "count": len(_task_pool),
        "pending": len(_task_queue),
        "tasks": list(_task_pool.values()),
    }


@app.get("/api/v1/task/{task_id}")
def get_task(task_id: str):
    task = _task_pool.get(task_id)
    if not task:
        return {"status": "error", "msg": "not found"}
    return task


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
