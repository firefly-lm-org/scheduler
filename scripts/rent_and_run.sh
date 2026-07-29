#!/bin/bash
# =============================================================================
# Firefly LM 补训脚本 - AutoDL 一键执行
# 用法: 在 AutoDL RTX 4090 实例中执行此脚本
# 预计耗时: ~50 分钟
# =============================================================================

set -e

echo "=== Firefly LM P0 补训脚本 ==="
echo "开始时间: $(date)"
echo "================================"

# ============================================================================
# 步骤 1: 创建干净环境
# ============================================================================
echo "[1/9] 创建 Python 3.10 环境..."
conda create -n firefly_clean python=3.10 -y
conda activate firefly_clean

echo "[1/9] 安装 PyTorch + 训练依赖..."
pip install torch transformers peft accelerate datasets sentencepiece safetensors trl

echo "[1/9] 安装 unsloth（加速训练，可选）..."
pip install unsloth -i https://pypi.tuna.tsinghua.edu.cn/simple || true

# ============================================================================
# 步骤 2: 克隆代码
# ============================================================================
echo "[2/9] 克隆 firefly-client..."
cd ~
git clone git@github.com:firefly-lm-org/firefly-client.git firefly-client
cd firefly-client
pip install -e .

# ============================================================================
# 步骤 3: 扩展数据集
# ============================================================================
echo "[3/9] 扩展数据集（medical/python/tax 各 30 条）..."
python scripts/expand_all_domains.py || true

# ============================================================================
# 步骤 4: 补训 3 域 round 2-5（共 12 个 adapter）
# ============================================================================
echo "[4/9] 补训 medical/python/tax round 2-5..."

for DOMAIN in medical python tax; do
  for R in 2 3 4 5; do
    echo "  >>> $DOMAIN round $R"
    bash scripts/_train_one.sh \
      "${DOMAIN}" \
      "$R" \
      "30" \
      "data/${DOMAIN}_extended.jsonl" \
      "deep" \
      "$HOME/firefly/train_output" \
      "data" \
      "scripts"
    sleep 3
  done
done

# ============================================================================
# 步骤 5: 出收敛曲线
# ============================================================================
echo "[5/9] 生成收敛曲线..."
for D in law medical python tax; do
  python scripts/plot_convergence.py ~/firefly/train_output "$D" || true
done

# ============================================================================
# 步骤 6: FedAvg 聚合 Round 5
# ============================================================================
echo "[6/9] FedAvg 聚合 Round 5..."

LAW_ADAPTER=$(ls ~/firefly/train_output/law_r5_*/lora.safetensors 2>/dev/null | head -1)
MED_ADAPTER=$(ls ~/firefly/train_output/medical_r5_*/lora.safetensors 2>/dev/null | head -1)
PY_ADAPTER=$(ls ~/firefly/train_output/python_r5_*/lora.safetensors 2>/dev/null | head -1)
TAX_ADAPTER=$(ls ~/firefly/train_output/tax_r5_*/lora.safetensors 2>/dev/null | head -1)

python scripts/fedavg.py \
  "$LAW_ADAPTER" \
  "$MED_ADAPTER" \
  "$PY_ADAPTER" \
  "$TAX_ADAPTER" \
  --output ~/firefly/train_output/aggregated_r5_full/adapter_model.safetensors

# ============================================================================
# 步骤 7: 推理验证
# ============================================================================
echo "[7/9] 推理验证..."
python scripts/infer_law_test.py \
  --adapter ~/firefly/train_output/aggregated_r5_full/adapter_model.safetensors \
  --questions data/test_questions_v2.jsonl

# ============================================================================
# 步骤 8: 签名权重
# ============================================================================
echo "[8/9] 签名权重..."
mkdir -p ~/firefly/train_output/aggregated_r5_full
python -c "
from app.models.weight_signing import WeightSigner
signer = WeightSigner()
manifest = signer.create_manifest(
    '/root/firefly/train_output/aggregated_r5_full/adapter_model.safetensors',
    'r5_full',
    ['law','medical','python','tax'],
    ['law_r5_*','medical_r5_*','python_r5_*','tax_r5_*'],
    {'law':28,'medical':50,'python':50,'tax':50}
)
signer.save_manifest(manifest, '/root/firefly/train_output/aggregated_r5_full/manifest.json')
print('Manifest created successfully')
" || echo "Weight signing skipped (module not available)"

# ============================================================================
# 步骤 9: 打包产物
# ============================================================================
echo "[9/9] 打包产物..."
mkdir -p ~/firefly/train_output/aggregated_r5_full
tar czf ~/p0_complete.tar.gz -C ~ firefly/train_output

echo ""
echo "================================"
echo "=== 全部完成！ ==="
echo "完成时间: $(date)"
echo "产物: ~/p0_complete.tar.gz"
echo ""
echo "请执行以下命令回传本机:"
echo "  scp ~/p0_complete.tar.gz user@<本机IP>:/d/firefly-fed-weights/"
echo "================================"
