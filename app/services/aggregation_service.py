"""
firefly-scheduler · Service · Weight Aggregation
权重聚合服务 — v0.1 简化版 FedAvg

功能：
1. find_ready_aggregation()  — 检测达到触发阈值的已完成任务组
2. aggregate_for_version()  — 对一组已完成任务执行 FedAvg 权重聚合
3. settle_aggregation()     — 为参与节点结算贡献积分
4. mark_tasks_aggregated()  — 标记任务为已聚合
"""
import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.task import Task
from app.models.node import Node
from app.models.aggregation import AggregationRecord
from app.utils.minio_client import minio_client


# ═══════════════════════════════════════════════
#  Step 1 · 检测可聚合的已完成任务组
# ═══════════════════════════════════════════════

async def find_ready_aggregation(db: AsyncSession) -> dict[str, list[dict[str, Any]]]:
    """
    扫描所有 completed 状态且有 result_sha256 的任务，
    按 (model_version, aggregation_key) 分组，
    当某组完成任务数 >= aggregation_threshold 时返回。

    Returns:
        {
            "v0.1_default": [
                {"task_id": "...", "node_id": "...", "result_sha256": "..."},
                ...
            ]
        }
    """
    # 查找已完成但尚未聚合的任务
    result = await db.execute(
        select(Task).where(
            Task.status == "completed",
            Task.result_sha256.isnot(None),
            Task.model_version.isnot(None),
        ).limit(500)
    )
    tasks: list[Task] = list(result.scalars().all())

    # 按 (model_version, aggregation_key) 分组
    groups: dict[tuple[str, str], list[Task]] = defaultdict(list)
    for task in tasks:
        key = (task.model_version, task.aggregation_key or "default")
        groups[key].append(task)

    # 过滤达到阈值的组
    ready: dict[str, list[dict[str, Any]]] = {}
    for (model_version, agg_key), group_tasks in groups.items():
        if len(group_tasks) >= settings.aggregation_threshold:
            # 选取最早完成的任务（按 completed_at 排序，取前 threshold 个）
            sorted_tasks = sorted(
                group_tasks,
                key=lambda t: (t.completed_at or datetime.min, t.id),
            )
            selected = sorted_tasks[: settings.aggregation_threshold]

            # 同一 aggregation_key 不再重复聚合同一批任务
            # （因为 selected 只取前 threshold 个，不会包含已被标记的）
            key_str = f"{model_version}___{agg_key}"
            ready[key_str] = [
                {
                    "task_id": t.id,
                    "node_id": t.claimed_by,
                    "result_sha256": t.result_sha256,
                    "completed_at": t.completed_at,
                    "base_contribution": t.base_contribution,
                    "quality_score": t.quality_score,
                }
                for t in selected
            ]

    return ready


# ═══════════════════════════════════════════════
#  Step 2 · 执行 FedAvg 聚合
# ═══════════════════════════════════════════════

async def aggregate_for_version(
    db: AsyncSession,
    model_version: str,
    aggregation_key: str,
    task_infos: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    对指定 model_version + aggregation_key 下的任务列表执行 FedAvg：
    1. 从 MinIO 下载各节点 result.zip
    2. 解压并读取 safetensors 权重文件
    3. 简单平均（每节点权重 = 1/N）
    4. 保存聚合结果到 checkpoints/{model_version}/agg_{timestamp}/
    5. 上传聚合结果到 MinIO
    6. 返回聚合统计

    Returns:
        {
            "aggregation_id": str,
            "status": "completed",
            "num_participants": int,
            "num_tasks": int,
            "checkpoint_url": str,
            "aggregated_sha256": str,
            "total_contribution": float,
        }
    """
    agg_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    local_ckpt_dir = Path(tempfile.mkdtemp(prefix="agg_"))
    try:
        # ── 2a. 创建聚合记录（pending → running） ──
        record = AggregationRecord(
            id=agg_id,
            model_version=model_version,
            aggregation_key=aggregation_key,
            num_participants=len(set(t["node_id"] for t in task_infos if t["node_id"])),
            num_tasks=len(task_infos),
            status="running",
        )
        db.add(record)
        await db.flush()

        # ── 2b. 下载并解压各节点 result.zip ──
        weight_data: dict[str, dict] = {}  # layer_name → {param_name: np_array}

        for info in task_infos:
            task_id = info["task_id"]
            object_name = f"results/{task_id}/result.zip"
            local_zip = local_ckpt_dir / f"{task_id}.zip"

            try:
                # 下载
                await asyncio.to_thread(
                    minio_client.fget_object,
                    settings.minio_bucket,
                    object_name,
                    str(local_zip),
                )
            except Exception as e:
                # 下载失败则跳过该任务（容错）
                print(f"[Aggregation] Skip task {task_id}: download error — {e}")
                continue

            # 解压到临时目录
            task_extract_dir = local_ckpt_dir / task_id
            try:
                shutil.unpack_archive(str(local_zip), str(task_extract_dir), "zip")
            except Exception as e:
                print(f"[Aggregation] Skip task {task_id}: unzip error — {e}")
                continue

            # 收集 safetensors 文件
            weights_dir = task_extract_dir / "weights"
            if not weights_dir.exists():
                weights_dir = task_extract_dir  # 容错：可能在根目录

            for st_file in weights_dir.glob("*.safetensors"):
                await _merge_safetensors(
                    str(st_file),
                    weight_data,
                    factor=1.0 / len(task_infos),  # FedAvg 平均权重
                )

        if not weight_data:
            raise RuntimeError("No valid weight data collected from any node")

        # ── 2c. 保存聚合结果到本地文件 ──
        agg_dir = local_ckpt_dir / "aggregated"
        agg_dir.mkdir(parents=True, exist_ok=True)

        await _save_aggregated_weights(weight_data, str(agg_dir))

        # 计算聚合结果 SHA256
        sha256_hash = await _compute_dir_sha256(agg_dir)

        # ── 2d. 上传到 MinIO ──
        agg_object_name = f"checkpoints/{model_version}/agg_{timestamp}_{agg_id[:8]}.zip"
        local_agg_zip = local_ckpt_dir / "aggregated.zip"
        shutil.make_archive(
            str(local_agg_zip.with_suffix("")), "zip", str(agg_dir)
        )

        await asyncio.to_thread(
            minio_client.fput_object,
            settings.minio_bucket,
            agg_object_name,
            str(local_agg_zip),
        )

        # ── 2e. 更新聚合记录 ──
        record.aggregated_checkpoint_url = agg_object_name
        record.aggregated_sha256 = sha256_hash
        record.status = "completed"
        record.completed_at = datetime.utcnow()
        await db.flush()

        return {
            "aggregation_id": agg_id,
            "status": "completed",
            "num_participants": record.num_participants,
            "num_tasks": record.num_tasks,
            "checkpoint_url": agg_object_name,
            "aggregated_sha256": sha256_hash,
            "total_contribution": record.total_contribution_settled,
        }

    except Exception as e:
        # 更新记录为失败状态
        await db.execute(
            update(AggregationRecord)
            .where(AggregationRecord.id == agg_id)
            .values(status="failed", error_message=str(e))
        )
        raise

    finally:
        # 清理本地临时目录
        shutil.rmtree(local_ckpt_dir, ignore_errors=True)


# ═══════════════════════════════════════════════
#  Step 3 · 结算贡献积分
# ═══════════════════════════════════════════════

async def settle_aggregation(
    db: AsyncSession,
    task_infos: list[dict[str, Any]],
    aggregation_result: dict[str, Any],
) -> float:
    """
    为每个参与聚合的任务节点结算贡献积分。
    公式（v0.1）：final = base_contribution × quality_score
    """
    total_settled = 0.0
    for info in task_infos:
        task_id = info["task_id"]
        node_id = info["node_id"]
        if not node_id:
            continue

        # 获取节点
        node_result = await db.execute(
            select(Node).where(Node.id == node_id)
        )
        node: Node | None = node_result.scalar_one_or_none()
        if not node:
            continue

        # 获取任务
        task_result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        task: Task | None = task_result.scalar_one_or_none()
        if not task:
            continue

        quality = task.quality_score or 1.0
        amount = int(task.base_contribution * quality)

        # 写入贡献流水
        from app.models.contribution import ContributionLog
        log = ContributionLog(
            id=str(uuid.uuid4()),
            user_id=node.user_id,
            node_id=node.id,
            task_id=task.id,
            amount=amount,
            type="earn",
            reason=(
                f"Aggregation {aggregation_result['aggregation_id'][:8]} "
                f"participant, model={task.model_version}"
            ),
        )
        db.add(log)

        # 更新节点完成任务计数
        node.total_tasks_completed += 1

        # 更新聚合记录中的总贡献
        total_settled += amount

    # 更新聚合记录总贡献
    agg_id = aggregation_result["aggregation_id"]
    await db.execute(
        update(AggregationRecord)
        .where(AggregationRecord.id == agg_id)
        .values(total_contribution_settled=total_settled)
    )

    return total_settled


# ═══════════════════════════════════════════════
#  Step 4 · 标记任务为已聚合
# ═══════════════════════════════════════════════

async def mark_tasks_aggregated(
    db: AsyncSession,
    task_ids: list[str],
    aggregation_id: str,
) -> int:
    """
    将指定任务标记为已聚合状态（status → aggregated）。
    返回实际更新的任务数。
    """
    if not task_ids:
        return 0

    result = await db.execute(
        update(Task)
        .where(Task.id.in_(task_ids))
        .values(status="aggregated")
    )
    return result.rowcount


# ═══════════════════════════════════════════════
#  主驱动：轮询 + 执行完整聚合流程
# ═══════════════════════════════════════════════

# 全局锁：防止并发聚合同一 model_version
_agg_locks: dict[str, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()


async def get_lock(model_version: str) -> asyncio.Lock:
    """获取指定 model_version 的聚合锁"""
    async with _locks_guard:
        if model_version not in _agg_locks:
            _agg_locks[model_version] = asyncio.Lock()
        return _agg_locks[model_version]


async def run_pending_aggregations(db: AsyncSession) -> list[dict[str, Any]]:
    """
    被 background_tasks 调用：检测并执行所有就绪的聚合。
    返回本次执行的聚合结果列表。
    """
    results: list[dict[str, Any]] = []

    ready_groups = await find_ready_aggregation(db)

    for key_str, task_infos in ready_groups.items():
        # 解析 model_version 和 aggregation_key
        parts = key_str.split("___", 1)
        model_version = parts[0]
        aggregation_key = parts[1] if len(parts) > 1 else "default"

        lock = await get_lock(model_version)
        if not lock.locked():
            async with lock:
                try:
                    agg_result = await aggregate_for_version(
                        db, model_version, aggregation_key, task_infos
                    )
                    await settle_aggregation(db, task_infos, agg_result)
                    task_ids = [t["task_id"] for t in task_infos]
                    await mark_tasks_aggregated(db, task_ids, agg_result["aggregation_id"])
                    await db.commit()
                    results.append(agg_result)
                    print(f"[Aggregation] Done: {model_version}/{aggregation_key} → {agg_result['aggregation_id'][:8]}")
                except Exception as e:
                    await db.rollback()
                    print(f"[Aggregation] Failed for {model_version}: {e}")

    return results


# ═══════════════════════════════════════════════
#  内部辅助函数
# ═══════════════════════════════════════════════

async def _merge_safetensors(
    path: str,
    weight_data: dict[str, dict],
    factor: float,
) -> None:
    """读取 safetensors 文件并累加权重（按 layer 分组）"""
    try:
        from safetensors import safe_open
    except ImportError:
        print("[Aggregation] safetensors not installed, skipping weight merge")
        return

    await asyncio.to_thread(_merge_safetensors_sync, path, weight_data, factor)


def _merge_safetensors_sync(
    path: str,
    weight_data: dict[str, dict],
    factor: float,
) -> None:
    """同步版本的 safetensors 合并（线程内执行）"""
    import numpy as np

    try:
        with safe_open(path, framework="numpy") as f:
            for key in f.keys():
                tensor = f.get_tensor(key) * factor
                if key not in weight_data:
                    weight_data[key] = tensor
                else:
                    weight_data[key] = weight_data[key] + tensor
    except Exception as e:
        print(f"[Aggregation] Error reading {path}: {e}")


async def _save_aggregated_weights(weight_data: dict, output_dir: str) -> None:
    """将聚合后的权重保存为 safetensors 文件"""
    try:
        from safetensors import safe_open
        from safetensors.torch import save_file
    except ImportError:
        print("[Aggregation] safetensors not installed, saving as numpy fallback")
        await _save_aggregated_weights_numpy(weight_data, output_dir)
        return

    import torch

    tensors = {}
    for key, arr in weight_data.items():
        if hasattr(arr, "numpy"):
            tensors[key] = torch.from_numpy(arr.numpy())
        else:
            tensors[key] = torch.tensor(arr)

    out_path = os.path.join(output_dir, "aggregated.safetensors")
    await asyncio.to_thread(save_file, tensors, out_path)


async def _save_aggregated_weights_numpy(
    weight_data: dict,
    output_dir: str,
) -> None:
    """Fallback：没有 safetensors 时保存为 numpy"""
    import numpy as np

    out_path = os.path.join(output_dir, "aggregated.npz")
    arrays = {k: (v.numpy() if hasattr(v, "numpy") else np.array(v))
              for k, v in weight_data.items()}
    await asyncio.to_thread(np.savez, out_path, **arrays)


async def _compute_dir_sha256(directory: str) -> str:
    """计算目录下所有文件的合并 SHA256"""

    def _sync_compute():
        h = hashlib.sha256()
        for root, _, files in os.walk(directory):
            for fname in sorted(files):
                fpath = os.path.join(root, fname)
                with open(fpath, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
        return h.hexdigest()

    return await asyncio.to_thread(_sync_compute)
