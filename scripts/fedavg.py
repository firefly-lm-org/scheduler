#!/usr/bin/env python3
"""FedAvg 等权聚合脚本：将多个同-shape 的 LoRA adapter 权重平均聚合"""
import argparse
import os
from safetensors.torch import load_file, save_file
import torch


def fedavg(adapter_paths, output_path):
    """等权 FedAvg：对所有 adapter 的同名张量求平均"""
    assert len(adapter_paths) >= 2, "至少需要 2 个 adapter"

    # 加载第一个作为模板
    tensors = load_file(adapter_paths[0])
    aggregated = {k: v.clone().float() for k, v in tensors.items()}

    # 累加其余所有
    for path in adapter_paths[1:]:
        t = load_file(path)
        assert t.keys() == aggregated.keys(), f"Tensor keys mismatch: {path}"
        for k in aggregated:
            aggregated[k] += t[k].float()

    # 等权平均
    n = len(adapter_paths)
    for k in aggregated:
        aggregated[k] = (aggregated[k] / n).to(tensors[k].dtype)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    save_file(aggregated, output_path)
    print(f"[FedAvg] {n} adapters averaged -> {output_path}")
    print(f"[FedAvg] Tensors: {len(aggregated)}, Size: {os.path.getsize(output_path)/1024/1024:.2f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FedAvg equal-weight aggregation")
    parser.add_argument("adapters", nargs="+", help="adapter_model.safetensors files")
    parser.add_argument("--output", "-o", required=True, help="Output path")
    args = parser.parse_args()
    fedavg(args.adapters, args.output)
