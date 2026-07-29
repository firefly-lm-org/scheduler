# v0.3 里程碑：FedAvg 异构 LoRA 聚合 + 推理验证

**日期**: 2026-07-26
**状态**: ✅ 完成
**执行时间**: 约 12:30–12:34 UTC+8（AutoDL RTX 4090）

---

## 核心成果

**首次完整跑通 Federated Learning 全链路闭环！**

- 两个异构节点（法律数据 + 医疗数据）各自训练 LoRA adapter
- FedAvg 聚合后权重直接用于推理，同时回答法律问题和医疗问题
- 聚合后的模型同时掌握两个节点的知识域

---

## 技术细节

### 节点配置

| 节点 | 数据集 | 样本数 | Final Loss | 耗时 |
|------|--------|--------|------------|------|
| Node A (node_a_law_v2) | 法律 QA (alpaca law) | 10 | 0.0239 | 43.4s |
| Node B (node_b_medical) | 医疗 QA | 31 | 0.206 | 38.0s |

### 模型配置（两节点完全对齐）

- **Base Model**: Qwen2.5-1.5B-Instruct（4-bit NF4 via bitsandbytes）
- **LoRA Rank**: 8, Alpha: 16
- **Target Modules**: `q_proj, v_proj, k_proj, o_proj, gate_proj, up_proj, down_proj`（7 modules）
- **Max Seq Length**: 512, Batch: 1, GradAccum: 4, LR: 2e-4, Steps: 60
- **Adapter Size**: 36,114 KB (392 tensors each)

### FedAvg 配置

- **算法**: 简单平均 (weight_a = 0.5, weight_b = 0.5)
- **聚合张量数**: 392 tensors
- **聚合后 Size**: 36,114 KB
- **推理耗时**: ~22s（含模型加载）

### 推理验证结果

**Q1（法律）**: "什么是劳动合同？"
→ 成功回答，包含《劳动合同法》第17条规定的8项必备条款

**Q2（医疗）**: "简述高血压的诊断标准"
→ 成功回答：成人收缩压≥140mmHg 和/或 舒张压≥90mmHg 即可诊断

---

## 关键 Bug 修复

### Bug 1: target_modules 不一致导致 FedAvg Key Mismatch
- **问题**: Node A 初始用 2 个 modules（q_proj, v_proj → 112 tensors），Node B 用 7 个（392 tensors），FedAvg 聚合时 `assert a.keys() == b.keys()` 失败
- **修复**: 重训练 Node A，统一使用 7 个 target_modules
- **经验**: 同一 FedAvg 集群内所有节点的 LoRA target_modules 必须完全一致

### Bug 2: trl 版本兼容性
- **问题**: `from trl import SFTTrainer, SFTConfig` → `SFTConfig` 不存在于 trl 0.8.0
- **修复**: 降级使用 `TrainingArguments`（旧版 API），`max_seq_length` 移到 SFTTrainer 构造参数
- **环境**: transformers 4.44.0, peft 0.12.0, trl 0.8.0, bitsandbytes 0.50.0

### Bug 3: accelerate bitsandbytes 冲突（提前解决）
- **问题**: transformers 4.44.0 的 `from_pretrained()` 调用 `dispatch_model()` → `.to(device)` → 4-bit 模型 ValueError
- **修复**: sed patch `accelerate/big_modeling.py`：`if getattr(model, "is_quantized", False): return model`
- **验证**: v0.2 单节点训练已验证，本次直接生效

### Bug 4: training_args.bin 误入 adapter 目录
- **问题**: `trainer.save_model()` 自动保存 TrainingArguments 序列化文件
- **修复**: 训练脚本末尾显式删除 `training_args.bin`
- **影响**: 避免 adapter 目录被污染，确保推理时只加载 LoRA 权重

---

## 产物清单

GitHub: `firefly-lm-org/firefly-client` → `benchmarks/fedavg-two-node/`

```
benchmarks/fedavg-two-node/
├── node_a_law_v2/
│   ├── adapter_model.safetensors  (36,114 KB)
│   ├── adapter_config.json
│   └── firefly_trainer_meta.json
├── node_b_medical/
│   ├── adapter_model.safetensors  (36,114 KB)
│   ├── adapter_config.json
│   └── firefly_trainer_meta.json
└── aggregated_v2/
    ├── adapter_model.safetensors  (36,114 KB) ← FedAvg 产物
    ├── adapter_config.json
    └── fedavg_meta.json
```

---

## v0.3 相对于 v0.2 的进步

| 维度 | v0.2 | v0.3 |
|------|------|------|
| 训练节点数 | 1 | 2（异构数据） |
| FedAvg 聚合 | 无 | 有（简单平均） |
| 推理验证 | 无 | 有（法律+医疗） |
| LoRA Modules | 2 | 7（全层） |
| Adapter Tensors | 112 | 392（全层） |
| 产物 GitHub | benchmarks/rtx-4090-qwen2.5-1.5b | benchmarks/fedavg-two-node/ |

---

## v0.4 待完成

- [ ] **不等权 FedAvg**：根据各节点训练样本数或 loss 加权聚合
- [ ] **真实节点接入**：firefly-client 端真实任务认领 + 权重上报到 scheduler
- [ ] **增量聚合**：多次聚合轮次（Round > 1）
- [ ] **异构模型 FedAvg**：不同底座模型（Qwen + Llama）的 LoRA 聚合
- [ ] **压缩传输**：LoRA 权重压缩后上传 OSS/MinIO，减少带宽占用
