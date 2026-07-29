# v0.2 里程碑：真实 QLoRA 训练跑通

**日期**：2026-07-26  
**状态**：✅ 完成  
**执行人**：Firefly LM Core Team

---

## 背景

v0.1 阶段训练模块使用 mock（`simulate_training()`），v0.2 目标是用真实 GPU 跑通 QLoRA 微调流程，产出第一份社区贡献的 LoRA adapter。

---

## 硬件环境

| 项目 | 值 |
|------|-----|
| 平台 | AutoDL（华东-杭州） |
| GPU | NVIDIA GeForce RTX 4090 |
| 显存 | 24 GB |
| CUDA | 12.4 |
| PyTorch | 2.4.0 |
| Python | 3.12 |

---

## 训练配置

| 参数 | 值 |
|------|-----|
| 底座模型 | `unsloth/Qwen3-1.5B-Instruct-4bit` |
| LoRA rank | 8 |
| LoRA alpha | 16 |
| 序列长度 | 512 |
| Batch size | 1 |
| 梯度累积 | 4（effective batch = 4） |
| 最大步数 | 60 |
| 学习率 | 2e-4 |
| 数据集 | `data/alpaca_demo.jsonl`（29 条法律领域中文 QA） |

---

## 训练结果

| 指标 | 值 |
|------|-----|
| 最终 loss | `<!-- 填写：X.XXXX -->` |
| 训练耗时 | `<!-- 填写：XX 分钟 -->` |
| 平均 GPU 利用率 | `<!-- 填写：估算或观察值 -->` |
| 峰值显存占用 | `<!-- 填写：XX GB -->` |
| 训练产物 | `lora_weights.safetensors` |

---

## 训练产物

产物存放路径：`.firefly/train_output/`

```
.firefly/train_output/
├── lora_weights.safetensors   # LoRA adapter 权重
├── firefly_trainer_meta.json  # 训练元数据
└── config.json                # 训练配置快照
```

### firefly_trainer_meta.json 示例字段

```json
{
  "model_name": "unsloth/Qwen3-1.5B-Instruct-4bit",
  "lora_rank": 8,
  "lora_alpha": 16,
  "dataset": "data/alpaca_demo.jsonl",
  "max_steps": 60,
  "final_loss": "<!-- 填写 -->",
  "elapsed_seconds": "<!-- 填写 -->",
  "gpu_name": "NVIDIA GeForce RTX 4090",
  "vram_peak_gb": "<!-- 填写 -->",
  "timestamp": "2026-07-26Txx:xx:xx+08:00"
}
```

---

## 验证方式

```bash
# 1. 确认产物存在
ls -lh ~/.firefly/train_output/

# 2. 加载 adapter（需要 base model）
python -c "
from safetensors.torch import load_file
weights = load_file('.firefly/train_output/lora_weights.safetensors')
print(f'Adapter 参数数量: {len(weights)}')
print(f'Keys: {list(weights.keys())[:5]}')
"
```

---

## 下一步（v0.3）

1. **两节点 FedAvg 聚合**：在不同数据集上训练 2 份 LoRA adapter，触发调度中心聚合，验证聚合后权重可 load
2. **断点续训**：补全 `resume_from_checkpoint` 逻辑
3. **进度上报**：联调 `/api/v1/task/progress` 接口，实现训练过程实时上报

---

## 相关文件

- `app/trainer/real_trainer.py`（SHA `8f229c81`）
- `data/alpaca_demo.jsonl`（SHA `ba256681`）
- `docs/benchmarks/meta.json`
