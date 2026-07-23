# Firefly Scheduler

> 萤火虫大模型 · 分布式志愿算力调度中心 v0.1

## 概述

调度中心为参与分布式训练的志愿者节点提供任务分发、状态追踪和贡献积分管理。

## 技术栈

| 组件 | 技术 |
|---|---|
| API | FastAPI (async) |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 (async) |
| Cache / Lock | Redis 7 |
| Object Storage | MinIO (S3-compatible) |
| Auth | JWT (python-jose + passlib/bcrypt) |
| Background | asyncio background tasks |

## 快速开始

### Docker Compose（一键启动）

```bash
git clone https://github.com/firefly-lm-org/scheduler.git
cd scheduler
cp .env.example .env        # 务必修改 JWT_SECRET_KEY
docker compose up -d
```

访问 `http://localhost:8000/docs` 查看 API 文档。

### 本地开发

```bash
pip install -r requirements.txt
cp .env.example .env         # 修改 JWT_SECRET_KEY
uvicorn app.main:app --reload --port 8000
```

## API 概览

### 认证

```
POST /api/v1/auth/register   — 注册
POST /api/v1/auth/login      — 登录（拿 JWT）
POST /api/v1/auth/refresh    — 刷新 Token
```

### 节点

```
POST /api/v1/node/register   — 注册节点（自动等级评定）
POST /api/v1/node/heartbeat  — 心跳（30s 一次）
GET  /api/v1/node/me        — 我的节点列表
```

### 任务

```
GET  /api/v1/task/available  — 可领取任务列表
POST /api/v1/task/claim      — 乐观锁领取任务
POST /api/v1/task/progress  — 更新进度（延长 running TTL）
POST /api/v1/task/submit     — 提交结果 + 结算积分
```

### 管理

```
POST /api/v1/admin/tasks      — 手动创建任务
GET  /api/v1/admin/stats      — 全局统计
POST /api/v1/admin/tasks/reset-failed — 重置失败任务
```

## 任务状态机

```
pending → running → completed
              ↓
            failed → (≤3 retry) → pending
```

## 核心能力

- ✅ 用户注册/登录/Token 刷新（bcrypt + JWT）
- ✅ 节点注册（自动等级 L1-L3）+ 心跳（Redis 滑动窗口限频）
- ✅ 任务乐观锁领取（Redis SETNX + PostgreSQL FOR UPDATE）
- ✅ 进度心跳（自动延长 running TTL）
- ✅ 结果提交（SHA256 校验 + MinIO 预签名 URL）
- ✅ 后台清理：超时回收 / 离线检测 / 信誉恢复
- ✅ 积分原子结算（SELECT FOR UPDATE 行锁）

## License

AGPL-3.0
