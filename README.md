# Firefly Scheduler

> 萤火虫大模型 · 分布式志愿算力调度中心

## 概述

萤火虫计划调度中心（Scheduler）是节点与任务的协调中枢，为参与分布式训练的志愿者节点提供任务分发、状态追踪和贡献积分管理。

## 技术栈

- **API**: FastAPI (async)
- **Database**: PostgreSQL 15 + SQLAlchemy 2.0 (async)
- **Cache / Lock**: Redis 7
- **Object Storage**: MinIO (S3-compatible)
- **Auth**: JWT (python-jose + passlib)

## 项目结构

```
scheduler/
├── app/
│   ├── api/          # FastAPI routers
│   │   ├── auth.py       # /auth/*  — 注册/登录/JWT
│   │   ├── nodes.py      # /nodes/* — 节点注册/心跳
│   │   ├── tasks.py      # /tasks/* — 任务查询/领取/启动
│   │   ├── submissions.py # /tasks/{id}/result|fail — 结果提交
│   │   └── users.py      # /users/me/contributions — 积分查询
│   ├── core/
│   │   └── config.py     # 环境变量配置 (pydantic-settings)
│   ├── models/       # SQLAlchemy ORM models
│   │   ├── user.py           # 用户 + 积分余额
│   │   ├── node.py            # 计算节点
│   │   ├── task.py            # 训练任务
│   │   └── contribution.py    # 积分流水
│   ├── schemas/      # Pydantic request/response models
│   └── services/     # 业务逻辑
│       ├── auth_service.py     # JWT / 密码哈希
│       ├── node_service.py     # 节点管理
│       ├── task_service.py     # 任务状态机
│       ├── contribution_service.py  # 积分原子操作
│       └── redis_lock.py       # Redis SETNX 分布式锁
├── tests/            # pytest + httpx async tests
├── docker-compose.yml # 本地开发完整栈
├── Dockerfile        # 生产镜像 (multi-stage)
└── requirements.txt
```

## 快速启动

### 本地开发（Docker Compose）

```bash
git clone https://github.com/firefly-lm-org/scheduler.git
cd scheduler
docker compose up
```

服务将在 `http://localhost:8000` 启动。

- API 文档: `http://localhost:8000/docs`
- MinIO Console: `http://localhost:9001` (admin / changeme_minio_password)

### 本地开发（裸机）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
export DATABASE_URL="postgresql+asyncpg://firefly:changeme@localhost:5432/firefly_scheduler"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET_KEY="your-secret-key-here"
# ... (见 .env.example)

# 3. 启动服务
uvicorn app.main:app --reload --port 8000
```

## API 文档

完整的 OpenAPI 文档在服务启动后访问 `/docs`（Swagger UI）。

### 认证流程

```
POST /api/v1/auth/register   → 注册账号
POST /api/v1/auth/login     → 登录获取 JWT
GET  /api/v1/auth/me        → 当前用户信息
```

所有后续请求在 Header 中携带：
```
Authorization: Bearer <access_token>
```

### 节点注册与心跳

```
POST /api/v1/nodes/register  → 注册节点（需 JWT）
POST /api/v1/nodes/heartbeat → 节点心跳（保持在线状态）
GET  /api/v1/nodes/me       → 我的所有节点
```

### 任务生命周期

```
GET  /api/v1/tasks/available           → 查询可领取任务
POST /api/v1/tasks/claim              → 原子领取任务（Redis 锁）
POST /api/v1/tasks/{id}/start         → 开始训练
POST /api/v1/tasks/{id}/result        → 提交训练结果
POST /api/v1/tasks/{id}/fail          → 报告失败（自动重试）
```

### 贡献积分

```
GET /api/v1/users/me/contributions  → 积分余额 + 流水记录
```

## 任务状态机

```
pending ──claim──> claimed ──start──> running ──result──> archived
   ^                    │                              │
   │                    │ fail                         │
   └─retry (≤3) ────────┘                              │
                    (max_retries reached) ──────────────┴──> archived (permanent)
```

## 分布式锁

任务领取使用 Redis `SETNX` 分布式锁，防止多节点同时认领同一任务：

```
SET lock:task:<task_id> 1 NX EX 600   ← 领取锁（10分钟 TTL）
SET running:task:<task_id> running EX 7200   ← 运行中（2小时 TTL）
```

心跳持续延长 running TTL，超时则任务自动回归队列。

## 数据库模型

| 表 | 说明 |
|---|---|
| `users` | 用户账户 + 积分余额 |
| `nodes` | 计算节点（属于某用户） |
| `tasks` | 训练任务（pending/claimed/running/archived） |
| `contribution_logs` | 积分流水（每笔交易一条） |

## 测试

```bash
pip install pytest pytest-asyncio httpx aiosqlite
pytest tests/ -v
```

## License

AGPL-3.0
