# v0.3+ 里程碑：4 节点 FedAvg 环形聚合（法律 + 医疗 + Python + 财税）

**日期**: 2026-07-26
**状态**: ✅ 完成
**执行时间**: 约 12:50–12:54 UTC+8（AutoDL RTX 4090）

---

## 核心成果

**4 节点异构 FedAvg 环形聚合全链路跑通！**

- 4 个完全不同的知识领域节点各自训练 LoRA adapter
- FedAvg 等权（25%/25%/25%/25%）聚合后，模型同时掌握 4 个领域的知识
- 4 类问题推理验证全部正确
- 数据集定型：法律(10条) + 医疗(31条) + Python(30条) + 财税(30条)

---

## 4 节点配置

| 节点 | 领域 | 数据集 | 样本数 | Final Loss | 耗时 |
|------|------|--------|--------|------------|------|
| Node A | 法律 | 劳动合同法 QA | 10 | 0.0239 | 43s |
| Node B | 医疗 | 高血压/糖尿病等 | 31 | 0.206 | 38s |
| Node C | Python | 编程基础 QA | 30 | 0.2546 | 42s |
| Node D | 财税 | 个税/增值税 QA | 30 | (下载确认) | 54s |

> 注：Node C python_qa.jsonl 初始上传有前导反斜杠问题（`\\\n{...`），修复后成功

### 模型配置（4 节点完全对齐）

- **Base Model**: Qwen2.5-1.5B-Instruct（4-bit NF4 via bitsandbytes）
- **LoRA**: r=8, alpha=16, 7 modules（q_proj/v_proj/k_proj/o_proj/gate_proj/up_proj/down_proj）
- **392 tensors / 节点**，adapter size: 36.1 MB
- **Max Seq Length**: 512, Batch: 1, GradAccum: 4, LR: 2e-4, Steps: 60

### FedAvg 配置

- **算法**: 等权平均（各 25%）
- **聚合张量**: 392 tensors（4 节点完全一致）
- **推理耗时**: ~22s

### 4 类推理验证结果

**Q1（法律）**: "劳动合同试用期最长多久？"
→ ✅ 正确：根据《劳动法》规定，试用期最长为 **6 个月**

**Q2（医疗）**: "糖尿病的典型症状是什么？"
→ ✅ 正确：频繁口渴、多饮、体重变化、易疲劳（回答了多个典型症状）

**Q3（Python）**: "Python 中 list 和 tuple 的主要区别是什么？"
→ ✅ 正确：list 可变 / tuple 不可变，并提到性能差异

**Q4（财税）**: "个人所得税专项附加扣除包括哪几项？"
→ ✅ 正确：子女教育、继续教育、大病医疗、住房贷款/租金、赡养老人等 6 项

---

## 产物清单

GitHub: `firefly-lm-org/firefly-client` → `benchmarks/`

```
benchmarks/
├── fedavg-two-node/
│   ├── node_a_law_v2/adapter_model.safetensors (36 MB)
│   ├── node_b_medical/adapter_model.safetensors (36 MB)
│   └── aggregated_v2/adapter_model.safetensors (36 MB)
└── fedavg-four-node/
    ├── node_c_python/adapter_model.safetensors (36 MB)
    ├── node_d_tax/adapter_model.safetensors (36 MB)
    └── aggregated_4node/adapter_model.safetensors (36 MB) ← 4节点聚合产物
```

---

## 分发基础设施（本次新增）

### requirements 分离
- `requirements-mock.txt`：纯 CLI 依赖，无 torch（Mac/AMD/无 GPU 用户）
- `requirements-gpu.txt`：安装说明 + torch==2.4.0 cu121 安装顺序
- `requirements-gpu-rest.txt`：其余 GPU 依赖（transformers 4.44.0 等）

### install 脚本
- `install.sh`：Linux/macOS 一键安装（含 GPU 检测 + torch cu121 安装）
- `install.ps1`：Windows PowerShell 一键安装（同逻辑）

### Dockerfile
- `Dockerfile`：ghcr.io/firefly-lm-org/client:cu121-torch240-v1
- 基于 nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04
- 锁死所有版本：torch 2.4.0 cu121 / transformers 4.44.0 / peft 0.12.0 / trl 0.8.0 / bitsandbytes 0.50.0
- 用户体验：`docker run --gpus all ghcr.io/firefly-lm-org/client:cu121-torch240-v1 firefly start`

---

## 领域数据集定型

| 文件 | 领域 | 条数 | 状态 |
|------|------|------|------|
| `data/alpaca_demo.jsonl` | 法律（通用） | 29 | ✅ 已用 |
| `data/medical_qa.jsonl` | 医疗（慢病常识） | 31 | ✅ 已用 |
| `data/python_qa.jsonl` | Python 编程 | 30 | ✅ 已用（v0.3+ 新增） |
| `data/tax_qa.jsonl` | 财税（个税/增值税） | 30 | ✅ 已用（v0.3+ 新增） |
| `data/law_qa.jsonl` | 法律（劳动合同专项） | 10 | ✅ 已用 |

---

## v0.4 待完成

- [ ] **不等权 FedAvg**：按样本数加权（law=10 / medical=31 / python=30 / tax=30）
- [ ] **真实节点接入**：firefly-client 端任务认领 + 权重上报 scheduler
- [ ] **阿里云 OSS**：替换 MinIO mock，真实存储节点权重
- [ ] **增量聚合**：多轮 FedAvg（Round > 1）
- [ ] **异构模型 FedAvg**：不同底座（Qwen + Llama）的 LoRA 聚合
- [ ] **Dockerfile GitHub Actions 自动构建 + GHCR 推送**
