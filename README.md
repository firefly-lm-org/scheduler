# Firefly Scheduler · 萤火虫调度中心

> v0.1 · 2024

## 项目概述

萤火虫大模型分布式志愿算力调度中心。志愿者节点注册后领取训练任务，提交结果后获得贡献积分。

## 技术栈

| 组件 | 技术 |
|------|------|
| API | FastAPI (async) |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 (async) |
| Cache / Lock | Redis 7 |
| Object Storage | MinIO (S3-compatible) |
| Auth | JWT + bcrypt |

## 快速启动

`ash
# 克隆
git clone https://github.com/firefly-lm-org/scheduler.git
cd scheduler

# 启动全部服务
docker compose up -d

# 查看日志
docker compose logs -f api

# 打开 API 文档
open http://localhost:8000/docs
`

## 环境变量

参考 .env.example。关键变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DATABASE_URL | postgresql+asyncpg://firefly:firefly123@db:5432/firefly | 数据库连接 |
| REDIS_URL | edis://redis:6379/0 | Redis |
| MINIO_ENDPOINT | minio:9000 | MinIO |
| JWT_SECRET | change-me... | JWT 密钥（必须修改） |
| JWT_ACCESS_EXPIRE | 86400 | Access Token 有效期（秒） |
| TASK_HEARTBEAT_TIMEOUT | 90 | 心跳超时（秒） |
| TASK_MAX_RETRIES | 3 | 任务最大重试次数 |

## API 路由

### 认证

`
POST /api/v1/auth/register   注册（自动签发 Token）
POST /api/v1/auth/login       登录
POST /api/v1/auth/refresh    刷新 Token
`

### 节点

`
POST /api/v1/node/register    注册节点（自动评级 L1-L3）
POST /api/v1/node/heartbeat   心跳（建议 30s 一次）
GET  /api/v1/node/me         我的节点列表
`

### 任务

`
POST /api/v1/task/claim      领取任务（Redis SETNX 乐观锁）
POST /api/v1/task/progress    上报训练进度
POST /api/v1/task/submit     提交结果（SHA256 校验）
GET  /api/v1/task/{id}       查询任务状态
`

### 管理

`
POST /api/v1/admin/tasks           创建任务
GET  /api/v1/admin/stats           全局统计
POST /api/v1/admin/tasks/reset    重置失败任务
`

## 任务状态机

`
pending → claimed → running → completed
                        ↓
                      failed → (≤3 retry) → pending
`

## 后台守护

- **超时回收**：每 60s 扫描 claimed/running 超时任务，回退到 pending
- **离线检测**：每 30s 检测 Redis 心跳，超时标记 offline
- **信誉恢复**：每 6h 为近 10 个任务节点恢复 +1 信誉分（上限 100）

## 目录结构

`
app/
├── config.py           配置管理（.env + 环境变量）
├── database.py        SQLAlchemy 异步引擎
├── main.py            FastAPI 入口 + 生命周期
├── models/            ORM 模型
│   ├── user.py
│   ├── node.py
│   ├── task.py
│   └── contribution.py
├── schemas/           Pydantic 请求/响应
├── routers/           API 路由
│   ├── auth.py
│   ├── node.py
│   ├── task.py
│   └── admin.py
├── services/          业务逻辑
│   ├── contribution_service.py
│   └── background_tasks.py
└── utils/
    ├── security.py       JWT + bcrypt
    ├── redis_client.py  分布式锁 + 心跳
    └── minio_client.py  对象存储
`

## License

AGPL-3.0
