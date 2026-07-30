# v0.4 Weighted FedAvg 结果

## 权重方案（按样本数加权）

| 节点 | 领域 | 样本数 | 权重 |
|------|------|--------|------|
| Node A | Law | 10 | 0.10 |
| Node B | Medical | 31 | 0.31 |
| Node C | Python | 30 | 0.30 |
| Node D | Tax | 29 | 0.29 |
| **合计** | - | **100** | **1.00** |

## 节点详情

- Law: loss=0.0239（7 target_modules, aligned for FedAvg）
- Medical: loss=0.2060（31条 医疗 QA）
- Python: loss=0.1388（domain_python.jsonl 30条 Python 专项）
- Tax: loss=0.1403（domain_tax.jsonl 29条 财税专项）

## 聚合结果

- 算法: FedAvg（不等权加权平均）
- 聚合方式: W_i = n_i / Σn
- 总 tensors: 392
- 输出: aggregated_weighted/adapter_model.safetensors

## 推理验证

四领域问答均正确（法律/医疗/Python/财税）

生成时间: 2026-07-26 13:29:48
