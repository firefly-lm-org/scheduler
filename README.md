# Firefly Scheduler

> 分布式联邦学习调度系统 v0.6 — 萤火虫计划核心组件

## 快速开始

### 前提条件

- Python 3.10+
- PostgreSQL 15+ / SQLite（开发模式）
- Redis 7+（可选，本地开发使用内存 mock）
- NVIDIA GPU（≥8GB VRAM）用于训练节点

### 安装

```bash
git clone git@github.com:firefly-lm-org/scheduler.git
cd scheduler
pip install -r requirements.txt
```

### 启动调度中心

**开发模式（SQLite，无需 PostgreSQL）：**

```bash
python -m app.main
```

**生产模式（PostgreSQL + Redis）：**

```bash
cp .env.example .env
# 编辑 .env，修改 DATABASE_URL 和 REDIS_URL
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

访问 API 文档：http://localhost:8000/docs

### 节点认领训练任务

```bash
# 1. 注册节点
curl -X POST http://localhost:8000/api/v1/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"name":"my-gpu-node","hardware":"RTX 4090 24GB"}'

# 2. 认领任务
curl -X POST http://localhost:8000/api/v1/tasks/claim \
  -H "Authorization: Bearer <node_token>" \
  -d '{"domain":"law"}'

# 3. 上报进度
curl -X POST http://localhost:8000/api/v1/tasks/progress \
  -H "Authorization: Bearer <node_token>" \
  -d '{"task_id":"<task_id>","progress_pct":50}'

# 4. 完成任务
curl -X POST http://localhost:8000/api/v1/tasks/complete \
  -H "Authorization: Bearer <node_token>" \
  -d '{"task_id":"<task_id>","final_loss":0.38}'
```

### 查看节点状态

```bash
# 节点信誉分
curl http://localhost:8000/api/v1/reputation/my-gpu-node

# 节点信号统计
curl http://localhost:8000/api/v1/contrib/stats/my-gpu-node

# 调度中心统计
curl http://localhost:8000/api/v1/admin/stats
```

### 下载聚合权重

```bash
# 下载最新聚合权重
curl -O http://localhost:8000/api/v1/weights/latest
```

## 架构

```
┌─────────────────────────────────────────────────────┐
│              Firefly Scheduler (调度中心)            │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  信誉分  │  │  信号回流 │  │  权重聚合 FedAvg │  │
│  │ Reputation│  │  Signal  │  │                  │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  任务调度: claim → train → complete → stats  │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
           │                    ▲
           ▼                    │
  ┌────────────────┐    ┌──────────────────┐
  │ GPU 训练节点 A  │    │ GPU 训练节点 B   │
  │ (Law Domain)   │    │ (Medical Domain) │
  │ RTX 4090       │    │ RTX 4090         │
  └────────────────┘    └──────────────────┘
```

## API 路由（v0.6，共 17 条）

| 模块 | 方法 | 路由 | 说明 |
|------|------|------|------|
| 认证 | POST | `/api/v1/auth/register` | 注册 |
| 认证 | POST | `/api/v1/auth/login` | 登录 |
| 节点 | POST | `/api/v1/nodes/register` | 注册节点 |
| 节点 | POST | `/api/v1/nodes/heartbeat` | 节点心跳 |
| 节点 | GET | `/api/v1/nodes` | 节点列表 |
| 任务 | GET | `/api/v1/tasks/pending` | 待领取任务 |
| 任务 | POST | `/api/v1/tasks/claim` | 认领任务 |
| 任务 | POST | `/api/v1/tasks/progress` | 上报进度 |
| 任务 | POST | `/api/v1/tasks/complete` | 完成任务 |
| 任务 | GET | `/api/v1/tasks` | 任务列表 |
| 信誉分 | GET | `/api/v1/reputation/{node_id}` | 查询信誉分 |
| 信誉分 | POST | `/api/v1/reputation/adjust` | 调整信誉分 |
| 信誉分 | GET | `/api/v1/reputation/{node_id}/history` | 信誉分历史 |
| 信号回流 | POST | `/api/v1/contrib/signal` | 上报训练信号 |
| 信号回流 | GET | `/api/v1/contrib/stats/{node_id}` | 节点信号统计 |
| 管理 | GET | `/api/v1/admin/stats` | 调度统计 |
| 健康 | GET | `/health` | 健康检查 |

## 信誉分规则

| 事件 | 信誉分变化 |
|------|-----------|
| 初始注册 | 100 分 |
| 任务完成（正常） | +5 分 |
| 任务完成（优秀 loss） | +7 分 |
| 任务超时 | -10 分 |
| 虚假数据 | -50 分 |
| 连续失败 ≥3 次 | -5 分 |
| 最低分 | 0 分（封禁） |
| 单次上限 | ±20 分 |

## 部署

### 阿里云轻量服务器

```bash
# SSH 连接服务器
ssh root@106.14.220.169

# 进入调度中心目录
cd /root/scheduler

# 安装依赖
pip install fastapi uvicorn sqlalchemy python-multipart httpx passlib pyjwt bcrypt

# 启动（Python 3.6 兼容模式）
PYTHONDONTWRITEBYTECODE=1 python3 -B main.py
```

### Docker 部署

```bash
git clone git@github.com:firefly-lm-org/scheduler.git
cd scheduler
docker compose up -d
```

## 相关仓库

- [firefly-lm-org/firefly-client](https://github.com/firefly-lm-org/firefly-client) — 节点训练客户端
- [firefly-lm-org/docs](https://github.com/firefly-lm-org/docs) — 文档与基准测试
- [firefly-lm-org/website](https://github.com/firefly-lm-org/website) — 官网

## License

MIT License
