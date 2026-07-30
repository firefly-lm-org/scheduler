# Round 1: 5-Domain Federated Learning (2026-07-30)

## Training
- **Base Model**: Qwen/Qwen2.5-1.5B-Instruct (float16)
- **Framework**: transformers + peft + trl (pure, no unsloth)
- **GPU**: AutoDL RTX 4090 (24GB VRAM)
- **Duration**: ~46s per domain × 5 = ~4 minutes total

## Results
| Domain | Steps | Train Loss | VRAM | Time |
|--------|-------|-----------|------|------|
| law | 30 | 1.7802 | 25.3GB | 42.7s |
| education | 30 | 1.3554 | 25.3GB | 43.8s |
| medical | 30 | 1.5437 | 25.3GB | 43.5s |
| python | 30 | 1.7690 | 25.3GB | 45.9s |
| tax | 30 | 1.7958 | 25.3GB | 43.3s |

## Verification (5/5 correct)
- Law: 劳动合同法 → ✅
- Medical: 多饮 → ✅
- Python: 列表/元组 → ✅
- Tax: 5000元起征点 → ✅
- Education: 阅读习惯 → ✅

## SHA256
- `law_r1.safetensors`: ff2bdcf0efdc624e...
- `edu_r1.safetensors`: 119fc3c9fa14543c...
- `med_r1.safetensors`: 770ca17ec7978353...
- `py_r1.safetensors`: 76dc8e2f90f81744...
- `tax_r1.safetensors`: eda52cd10d61f5ae...
- `fedavg_5node.safetensors`: c57fa9531c7259a0...
