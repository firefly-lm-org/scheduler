# AutoDL 租卡执行清单

> 租卡后按顺序执行，~50 分钟完成全部补训 + 聚合 + 验证

## 租卡前准备（本地操作）

- [ ] AutoDL 账号余额充足（预估 ¥1.5 × 1h = ¥1.5）
- [ ] 下载 `scripts/rent_and_run.sh` 到本地备用

---

## Step 1：租卡（5 min）

1. 登录 [AutoDL 控制台](https://console.autodl.com)
2. 实例管理 → 租用实例
3. 选择：**RTX 4090 / 24GB** / 按量计费 / 镜像：PyTorch 2.4 + Python 3.10
4. 启动，SSH 连接到实例

---

## Step 2：执行补训脚本（~45 min）

在 AutoDL 终端执行：

```bash
# 方式 A：一键脚本（如已上传）
bash ~/rent_and_run.sh

# 方式 B：手动分步
# 2a. 环境
conda create -n firefly_clean python=3.10 -y
conda activate firefly_clean
pip install torch transformers peft accelerate datasets sentencepiece safetensors trl
pip install unsloth -i https://pypi.tuna.tsinghua.edu.cn/simple || true

# 2b. 代码
cd ~
git clone git@github.com:firefly-lm-org/firefly-client.git firefly-client
cd firefly-client
pip install -e .

# 2c. 补训 12 个 adapter
for DOMAIN in medical python tax; do
  for R in 2 3 4 5; do
    bash scripts/_train_one.sh "${DOMAIN}" "$R" "30" \
      "data/${DOMAIN}_extended.jsonl" "deep" \
      "$HOME/firefly/train_output" "data" "scripts"
    sleep 3
  done
done

# 2d. 聚合 Round 5
python scripts/fedavg.py \
  $(ls ~/firefly/train_output/law_r5_*/lora.safetensors | head -1) \
  $(ls ~/firefly/train_output/medical_r5_*/lora.safetensors | head -1) \
  $(ls ~/firefly/train_output/python_r5_*/lora.safetensors | head -1) \
  $(ls ~/firefly/train_output/tax_r5_*/lora.safetensors | head -1) \
  --output ~/firefly/train_output/aggregated_r5_full/adapter_model.safetensors

# 2e. 推理验证
python scripts/infer_law_test.py \
  --adapter ~/firefly/train_output/aggregated_r5_full/adapter_model.safetensors \
  --questions data/test_questions_v2.jsonl
```

---

## Step 3：回传本机（5 min）

```bash
# 在 AutoDL 终端
tar czf ~/p0_complete.tar.gz -C ~ firefly/train_output

# 在本机 PowerShell（先查本机 IP）
# 本机 IP: 192.168.x.x（查 AutoDL 提供的访问密钥文档）
scp root@<autodl-ip>:/root/p0_complete.tar.gz D:\firefly-fed-weights\
```

---

## 预期产物

| 产物 | 位置 | 大小 |
|------|------|------|
| medical round 2-5 | `~/firefly/train_output/medical_r{2-5}_*/lora.safetensors` | 4 × ~35MB |
| python round 2-5 | `~/firefly/train_output/python_r{2-5}_*/lora.safetensors` | 4 × ~35MB |
| tax round 2-5 | `~/firefly/train_output/tax_r{2-5}_*/lora.safetensors` | 4 × ~35MB |
| FedAvg 聚合权重 | `~/firefly/train_output/aggregated_r5_full/adapter_model.safetensors` | ~35MB |
| 签名 manifest | `~/firefly/train_output/aggregated_r5_full/manifest.json` | ~1KB |
| 打包文件 | `~/p0_complete.tar.gz` | ~150MB |

---

## 故障排查

| 问题 | 解法 |
|------|------|
| `ModuleNotFoundError: No module named 'unsloth'` | 跳过，unsloth 是可选加速包 |
| 训练 OOM（显存不足） | 减小 batch_size 或 max_seq_length |
| 网络超时（git clone 失败） | 换 GitHub SSH：`git clone git@github.com:...` |
| 磁盘空间不足 | `rm -rf ~/firefly/train_output/law_r2_*` 等，先跑 medical/python/tax |
| `Permission denied`（scp） | 检查 AutoDL 密钥是否正确 |
