# 萤火虫大模型 v0.1 微光版 — 里程碑对照报告

**盘点时间：** 2026-07-25 08:50
**盘点人：** QClaw Agent
**版本：** v0.1 微光版（调度闭环）

---

## 一、v0.1 退出标准完成情况

### 后端调度中心（firefly-lm-org/scheduler）

| # | 检查项 | 状态 | 备注 |
|---|--------|------|------|
| 1 | FastAPI + PostgreSQL + Redis + MinIO | ⚠️ | PostgreSQL ✅ / Redis ✅ / MinIO 本地 Mock ✅（无二进制依赖） |
| 2 | 用户注册/登录（JWT）+ 节点注册 | ✅ | auth router + node register ✅ |
| 3 | 心跳保活 + 节点状态查询 | ✅ | node heartbeat + status ✅ |
| 4 | 任务生命周期（create→claim→progress→submit→validate→completed） | ✅ | 完整 5 态状态机 ✅ |
| 5 | 分布式锁防抢 | ✅ | Redis SETNX claim lock ✅ |
| 6 | 三级校验 L1 落地，L2/L3 留接口 | ✅ | L1 实装，L2/L3 接口已定义 ✅ |
| 7 | 贡献值结算 + contribution_logs 不可篡改流水 | ✅ | ContributionLog 实体 ✅ |
| 8 | 后台协程：超时回收、离线检测、信誉恢复 | ✅ | 3 个后台协程 ✅ |
| 9 | 管理 API：建任务、统计、重置 | ✅ | admin router ✅ |
| 10 | 权重聚合 Worker（FedAvg ≥3 份触发） | ✅ | aggregation_loop ✅ E2E 已验证 ✅ |
| 11 | pytest 测试套件 | ⚠️ | firefly-client 42/42 ✅ / scheduler pytest 待补充 |
| 12 | CI/CD pipeline | ⚠️ | workflow 文件存在，需推送最新代码后验证 |

### 客户端（firefly-lm-org/firefly-client）

| # | 检查项 | 状态 | 备注 |
|---|--------|------|------|
| 1 | CLI：register/login/node-register/start/status | ✅ | 7 核心命令 ✅ |
| 2 | CLI：task-claim/task-submit/task-status/checkpoint-info | ✅ | 10 个命令完整 ✅ |
| 3 | 硬件检测（torch.cuda 降级处理） | ✅ | HardwareDetector ✅ |
| 4 | 任务下载（预签名 URL）→ 模拟执行 → 结果上传 | ✅ | E2E 全链路跑通 ✅ |
| 5 | 30s 心跳线程 | ✅ | ✅ |
| 6 | 42/42 pytest 绿 | ✅ | 42/42 全部通过 ✅ |
| 7 | PyInstaller 打包 | ❌ | 未实现 |

### 文档与合规

| # | 检查项 | 状态 | 备注 |
|---|--------|------|------|
| 1 | README.md | ⚠️ | 需更新至最新版本 |
| 2 | ROADMAP.md | ⚠️ | docs 仓库有，需同步至最新修正版 |
| 3 | ARCHITECTURE.md | ✅ | docs/v0.1-scheduler-design.md ✅ |
| 4 | PRIVACY.md | ❌ | **缺失** |
| 5 | MODEL_LICENSE.md | ❌ | **缺失** |
| 6 | CLA（贡献者许可协议） | ❌ | **缺失** |
| 7 | GOVERNANCE.md | ❌ | **缺失** |
| 8 | LICENSE | ⚠️ | 需确认（未推送至仓库） |
| 9 | ADR（架构决策记录） | ❌ | 需补 7 条 |
| 10 | docs/TRADEMARK.md | ❌ | **缺失** |

### 项目基础设施

| # | 检查项 | 状态 | 备注 |
|---|--------|------|------|
| 1 | GitHub org `firefly-lm-org` | ✅ | 4 仓库就位 |
| 2 | 4 仓库：scheduler/client/docs/website | ⚠️ | website 仓库未建 |
| 3 | 域名注册（firefly-lm.com/org） | ❌ | 未注册 |
| 4 | 官网（Cloudflare Pages + 自定义域名） | ❌ | 未搭建 |
| 5 | 5 人种子测试群 | ❌ | 未启动 |

### v0.1 总体退出标准

| 标准 | 状态 | 备注 |
|------|------|------|
| 本地 3 节点跑通全链路 | ✅ | E2E 单机 3 节点已跑通 |
| 42+42 测试全绿 | ⚠️ | firefly-client 42/42 ✅ / scheduler 待补充 |
| 有官网 | ❌ | |
| 有隐私政策 | ❌ | |
| 有 5 人种子测试群 | ❌ | |
| 有估值锚（10-30 万/年运维覆盖） | ✅ | 纸面已修正 |

---

## 二、v0.1 完成度评估

```
核心调度链路   ████████████░░░░░  80%  （E2E+聚合已通，pytest未全）
合规与文档     ██░░░░░░░░░░░░░░░  15%  （架构文档有，其余全缺）
项目推广       ░░░░░░░░░░░░░░░░░   0%  （官网/域名/社群均未启动）
基础设施       ████████░░░░░░░░░  50%  （CI有，website未建）
─────────────────────────────────────────────
综合完成度     █████░░░░░░░░░░░░  35%
```

---

## 三、v0.5 训练版前置依赖（v0.1 缺口分析）

以下 v0.1 缺陷会阻碍 v0.5 推进：

1. **scheduler pytest 缺失** → CI 不完整，无法验证重构
2. **无隐私政策 / CLA** → 无法合规接收外部节点贡献
3. **无官网** → 无法发布 v0.5 公测招募节点
4. **scheduler 代码未推送** → 协作者无法参与

---

## 四、GitHub 推送状态

| 问题 | 详情 |
|------|------|
| 阻塞原因 | GitHub 网络不稳定（443 连接超时） |
| 解决方式 | 通过 GitHub API 推送关键修复，PR #1 已合并 ✅ |
| 远程 main 最新 | commit `bd383931`（含 safetensors 修复 + MinIO mock）✅ |
| 本地待推送 | minio_client.py 本地 Mock 版本（未 push，因网络断）|

---

## 五、立即行动项（Priority Order）

### P0 — 今天必须完成
1. [ ] **补 scheduler pytest**（10-15 个核心用例，覆盖 auth / task lifecycle / aggregation）
2. [ ] **推送 scheduler 最新代码到 GitHub**（等网络恢复后 force-push main）
3. [ ] **创建 website 仓库**（官网骨架，Cloudflare Pages）

### P1 — 本周内完成
4. [ ] **PRIVACY.md**（隐私政策）
5. [ ] **CLA.md**（贡献者许可协议）
6. [ ] **更新 docs/ROADMAP.md**（同步最新修正版）
7. [ ] **注册域名** firefly-lm.com / .org

### P2 — v0.5 前完成
8. [ ] MODEL_LICENSE.md
9. [ ] GOVERNANCE.md
10. [ ] 7 条 ADR
11. [ ] 真实 QLoRA 训练链路（Unsloth 集成）
12. [ ] PyInstaller 打包脚本

---

## 六、v0.5 核心规划预览

| 组件 | v0.5 目标 | 前置条件 |
|------|-----------|---------|
| 底座 | Qwen3-1.5B 4bit | 底座锁定 |
| 训练 | Unsloth QLoRA rank=32 | 客户端集成 |
| 任务包 | config.yaml + data.jsonl | 标准化协议 |
| 聚合 | FedAvg 分域触发 | 已实现 ✅ |
| 校验 | L2/L3 实装 | 接口已留 |
| 节点 | 300~1000 节点 | 官网 + 公测招募 |
| 发布 | V2EX/HN/Reddit/知乎首发 | 隐私政策 + CLA 先到位 |
