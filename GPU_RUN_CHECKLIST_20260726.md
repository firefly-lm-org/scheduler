# v0.2 真实训练跑卡清单
> 目标：在 GPU 机器上完成第一次真实 QLoRA 训练，产出第一份 LoRA adapter + firefly_trainer_meta.json

---

## 阶段 0：准备工作（今天做完 ✅）

- [x] scheduler `/api/v1/task/progress` 接口就绪（TaskProgressRequest schema 已修正）
- [x] 本地训练数据集已准备：`data/alpaca-demo.jsonl`（20 条，中文 QA）
- [x] firefly-client 仓库已同步（trainer 模块 + requirements.txt）
- [x] 所有代码已推 GitHub（real_trainer.py `8f229c81`）

**今天还需要你手动确认一件事：**
> scheduler 现在跑在哪台机器上？如果在你的 Windows 本机，远程 GPU 机器需要能访问 `http://<你的IP>:8000`。
> 如果 scheduler 也迁移到云服务器，两边都要更新 `FIREFLY_SERVER_URL`。

---

## 阶段 1：GPU 机器环境准备（约 15 分钟）

```powershell
# 1. 克隆代码（首次）
git clone https://github.com/firefly-lm-org/firefly-client.git
cd firefly-client

# 2. 建虚拟环境
python -m venv .venv
.\.venv\Scripts\activate

# 3. 装依赖（清华源，约 3-5 GB）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 4. 验证 GPU 可见（预期输出 True + GPU名称 + VRAM）
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, '
      f'GPU: {torch.cuda.get_device_name(0)}, '
      f'VRAM: {torch.cuda.get_device_properties(0).total_mem/1e9:.1f}GB')"
```

---

## 阶段 2：scheduler 端冒烟测试（约 5 分钟）

> 目标：验证 claim→progress→submit 链路全通（无需 GPU，mock 即可）

**在运行 scheduler 的机器上（Windows 本机）：**

```powershell
cd D:\firefly-scheduler
# 确认 scheduler 正在运行
python -c "import httpx; r=httpx.get('http://localhost:8000/docs'); print('scheduler UP' if r.status_code==200 else 'DOWN')"

# 运行冒烟测试
python smoke_test.py
```

预期输出：10 个步骤全部 200/201，无红色 ERROR。

---

## 阶段 3：client 端 mock 链路测试（约 3 分钟）

> 目标：验证 client→scheduler 通信全通（mock 训练，无需 GPU）

```powershell
# 在 GPU 机器上：
set FIREFLY_SERVER_URL=http://<scheduler机器IP>:8000
set FIREFLY_MOCK=1
set FIREFLY_E2E=1

# 注册用户（如已有可跳过）
firefly register --username testnode --password Test1234

# 注册节点
firefly node-register smoke-node

# 启动（mock 模式，5步快跑）
firefly start --mock
```

预期：看到 `claim task` → `Mock训练` → `upload result` → `任务完成`。

---

## 阶段 4：真实训练首跑（约 20-40 分钟）

> 3.9GB 显存限定配置：Qwen3-1.5B-Instruct-4bit + LoRA r=8 + seq_len=512 + batch=1

```powershell
# 环境变量（全部走环境变量，不改代码）
set FIREFLY_SERVER_URL=http://<scheduler机器IP>:8000
set FIREFLY_MOCK=0
set FIREFLY_MODEL_PATH=unsloth/Qwen3-1.5B-Instruct-4bit
set FIREFLY_LORA_RANK=8
set FIREFLY_MAX_SEQ_LENGTH=512
set FIREFLY_BATCH_SIZE=1
set FIREFLY_MAX_STEPS=60
set FIREFLY_DATASET=D:\firefly-client\firefly-client\data\alpaca-demo.jsonl

# 注册（如首次）
firefly register --username yourname --password YourPass
firefly node-register your-machine-name

# 启动
firefly start
```

**预期时间：** 模型下载（首次 1-2GB）+ 训练 60 步 ≈ 20-40 分钟（取决于 GPU）
**预期显存峰值：** ~2.8 GB（3.9 GB 足够）

---

## 阶段 5：验证产物（约 2 分钟）

```powershell
# 查看输出目录
dir %USERPROFILE%\.firefly\train_output\

# 验证产物
type %USERPROFILE%\.firefly\train_output\firefly_trainer_meta.json
```

预期看到：
```json
{
  "task_id": "xxx",
  "model_base": "unsloth/Qwen3-1.5B-Instruct-4bit",
  "lora_r": 8,
  "final_loss": 0.xxxx,
  "elapsed_sec": 1234,
  "framework": "unsloth+peft+trl",
  "vram_gb": 3.9
}
```

把 `final_loss` + `elapsed_sec` + VRAM 截图发给我 → 我帮你建 `docs/benchmarks/rtx-3.9gb-qwen1.5b-r8.md` → v0.2 第一个里程碑 ✅

---

## 已知约束与注意事项

| 约束 | 说明 |
|------|------|
| **scheduler 和 client 必须互通** | 若在不同机器，检查防火墙 + scheduler 绑定 `0.0.0.0` 而非 `127.0.0.1` |
| **FIREFLY_DATASET 优先** | 设为本地路径跳过 HF 下载；空则自动拉 `yahma/alpaca-cleaned` |
| **OOM 应急降级** | 若 3.9GB 跑 r=8 仍 OOM：降 `FIREFLY_MAX_SEQ_LENGTH=256`，或 `FIREFLY_LORA_RANK=4` |
| **训练产物不自动上报调度中心** | v0.2 首跑手动验证；`/submit-file` 上传链路已通，后续接自动触发 |
| **无 GPU 机器只能用 mock** | `FIREFLY_MOCK=1 firefly start --mock` 走模拟，不触发真实训练 |

---

## 下一步（跑通后）

1. 把 meta.json 截图发给我 → 建 benchmarks 文档
2. 用两份 LoRA adapter 手动跑 FedAvg 聚合（scheduler 上有 `services/aggregation_service.py`）
3. 验证聚合后权重可加载推理
4. → v0.2 核心目标达成 ✅
