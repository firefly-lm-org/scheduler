# Firefly Scheduler · 萤火虫调度中心

> 全球分布式志愿算力驱动的 AI 训练调度系统 · v0.1 微光版

## 快速开始

### 前置条件
- Docker + Docker Compose（推荐）
- 或：Python 3.12 + PostgreSQL 15 + Redis 7 + MinIO

### Docker 一键启动（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/firefly-lm-org/firefly-scheduler.git
cd firefly-scheduler

# 2. 复制环境变量
cp .env.example .env
# 编辑 .env，修改 JWT_SECRET 为随机强密钥

# 3. 启动全部服务
docker compose up -d

# 4. 查看日志
docker compose logs -f api

# 5. 访问 API 文档
open http://localhost:8000/docs
```

### 本地开发（不用 Docker）

```bash
# 1. 安装依赖
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. 确保 PostgreSQL / Redis / MinIO 已运行
# （可用 docker-compose 只启动这三个服务）

# 3. 启动 API
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## API 端点一览

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Auth | POST | `/api/v1/auth/register` | 用户注册 |
| Auth | POST | `/api/v1/auth/login` | 用户登录 |
| Auth | POST | `/api/v1/auth/refresh` | 刷新 Token |
| Node | POST | `/api/v1/node/register` | 注册节点 |
| Node | POST | `/api/v1/node/heartbeat` | 心跳上报 |
| Node | GET  | `/api/v1/node/status` | 查询节点状态 |
| Task | POST | `/api/v1/task/claim` | 领取任务 |
| Task | POST | `/api/v1/task/progress` | 上报进度 |
| Task | POST | `/api/v1/task/submit` | 提交结果 |
| Task | GET  | `/api/v1/task/{id}` | 查询任务状态 |
| Admin | POST | `/api/v1/admin/tasks` | 创建任务 |
| Admin | GET  | `/api/v1/admin/stats` | 全局统计 |
| Admin | POST | `/api/v1/admin/tasks/{id}/reset` | 重置失败任务 |

## 项目结构

```
firefly-scheduler/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口 + 生命周期
│   ├── config.py            # 配置管理
│   ├── database.py          # 异步引擎 + 会话
│   ├── models/              # ORM 模型
│   │   ├── user.py
│   │   ├── node.py
│   │   ├── task.py
│   │   └── contribution.py
│   ├── schemas/             # Pydantic 请求/响应
│   │   ├── auth.py
│   │   ├── node.py
│   │   └── task.py
│   ├── routers/             # API 路由
│   │   ├── auth.py
│   │   ├── node.py
│   │   ├── task.py
│   │   └── admin.py
│   ├── services/            # 业务逻辑
│   │   ├── contribution_service.py
│   │   └── background_tasks.py
│   └── utils/               # 工具函数
│       ├── security.py
│       ├── redis_client.py
│       └── minio_client.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 开发路线图

| 版本 | 目标 | 状态 |
|------|------|------|
| v0.1 微光版 | 调度闭环验证（模拟任务） | 🚧 进行中 |
| v0.5 训练版 | 接入真实 QLoRA 微调 | 📋 待启动 |
| v1.0 成炬版 | 发布社区持续优化版 7B 模型 | 📋 规划中 |

## 许可证

Apache 2.0
