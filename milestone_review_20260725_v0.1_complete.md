# 萤火虫大模型 v0.1 基础设施里程碑存档

**完成时间**：2026-07-25 13:22 GMT+8
**里程碑**：v0.1 基础设施完整闭环（Demo 阶段）

---

## 🎯 里程碑意义

v0.1 不是产品上线，而是 **「项目能不能跑通 + 信誉能不能建立」** 的两个最小证明。本次完成：

1. **技术可信**：代码可运行、E2E 闭环、CI 全绿
2. **机构可信**：官网、GitHub、爱发电、品牌域名互链闭环
3. **法律可信**：PRIVACY / CLA / CONTRIBUTING / LICENSE / SECURITY / GOVERNANCE 全部就位

---

## 📦 代码交付（4 个 GitHub 仓库）

### 1. firefly-lm-org/scheduler — 调度中心
- **栈**：FastAPI + SQLAlchemy + PostgreSQL + Redis + MinIO (mock)
- **关键能力**：
  - 用户认证（bcrypt + JWT）
  - 节点注册 + heartbeat
  - 任务领取 / 提交 / 状态机
  - 权重聚合 worker（FedAvg）
  - admin 鉴权
- **测试**：pytest 基础用例
- **CI**：✅ GitHub Actions
- **HEAD**：bd3839314d86（main，含 PR #1 合并修复）

### 2. firefly-lm-org/firefly-client — 火种客户端
- **栈**：Python CLI（typer/click）+ safetensors
- **关键能力**：
  - 硬件检测（CPU/GPU/内存）
  - 任务领取 → 下载 → 训练 → 上传
  - QLoRA 量化配置（4-bit/8-bit）
  - 断点续训
- **测试**：pytest 42/42 通过
- **CI**：✅
- **HEAD**：0008b9a0（main）

### 3. firefly-lm-org/docs — 文档中心
- **文件清单**：
  - PRIVACY.md / CLA.md / CONTRIBUTING.md / LICENSE (MIT)
  - SECURITY.md / GOVERNANCE.md / MILESTONE.md
  - ROADMAP.md / VALUATION_GATES.md / v0.1-scheduler-design.md
  - FINANCE.md / MODEL_LICENSE.md / TRADEMARK_SEARCH.md
  - .github/FUNDING.yml（爱发电链接）
- **README**：✅ 含 firefly-lm.com + afdian.net 链接

### 4. firefly-lm-org/website — 官网仓库
- **文件**：index.html / style.css / _headers / vercel.json
- **部署**：Vercel（项目 ID: prj_QZKDoqLYXvHAXnlAT5lBV9xafBBE）
- **HEAD**：9e749256（含 vercel.json 安全头）
- **URL**：https://firefly-lm.com

---

## 🌐 上线资产

| 资产 | 状态 | 备注 |
|------|------|------|
| https://firefly-lm.com | ✅ 生产 READY | Vercel + 阿里云 DNS |
| https://www.firefly-lm.com | 🟡 308 重定向配置中 | 待阿里云加 www CNAME |
| https://firefly-website-two.vercel.app | ✅ 测试域名 | Vercel 自动分配 |
| https://github.com/firefly-lm-org | ✅ 组织主页 | 4 仓库 |
| https://afdian.net/a/firefly-lm | ✅ 爱发电主页 | 简介含官网链接 |

---

## 🔒 安全配置

### vercel.json（website 仓库）
| Header | 值 | 作用 |
|--------|-----|------|
| X-Content-Type-Options | nosniff | 防 MIME 嗅探 |
| X-Frame-Options | DENY | 防点击劫持 |
| X-XSS-Protection | 1; mode=block | 旧浏览器 XSS 兜底 |
| Referrer-Policy | strict-origin-when-cross-origin | 跨域隐私 |
| Permissions-Policy | camera=(), microphone=(), geolocation() | 禁用特权 API |
| Strict-Transport-Security | max-age=63072000; includeSubDomains; preload | 强制 HTTPS 2年 |

### 缓存策略
- HTML：no-cache（改文案 5 分钟内生效）
- CSS：max-age=86400（1 天）
- 图片：max-age=2592000（30 天）

---

## 🔗 三端闭环验证

```
firefly-lm.com（官网）
  ├── 底部版权 → 上海凌泷科技有限公司 ✅
  ├── 赞助链接 → afdian.net/a/firefly-lm ✅
  └── GitHub 链接 → github.com/firefly-lm-org ✅

GitHub 各仓库 README（scheduler / firefly-client / docs）
  └── 顶部 → firefly-lm.com + afdian.net ✅

爱发电主页
  └── 简介 → 官网 firefly-lm.com ✅（用户补全）
```

**投资人 / Core 候选从任意入口进入，都能找到另两个，信任链条完整。**

---

## 📋 VALUATION_GATES v0.1 进度

| 编号 | 名称 | 状态 |
|------|------|------|
| 1 | 项目注册 + README | ✅ |
| 2 | 调度中心 + E2E 闭环 | ✅ |
| 3 | 客户端可用 + 测试通过 | ✅ |
| 4 | 官网可访问 + PRIVACY 公开 | ✅ |
| 5 | CLA / CONTRIBUTING 落地 | ✅ |
| 6 | Trademark search | ⚠️ 框架已建，待 USPTO/CNIPA |
| 7 | 代码签名（SignPath） | ⚠️ 待申请 |
| 8 | 客户端真实训练接入 | ⚠️ 当前 mock |
| 9 | 推广素材 | ⚠️ 三平台文案待发 |
| 10 | 公益基金/企业赞助通道 | ⚠️ 凌泷科技协议待签 |

**当前进度：8/17 通过（47%）**

---

## 🚧 已知 blocker（v0.1 阶段不阻塞）

1. **MinIO 依赖**：已替换为本地 mock（`~/.firefly/scheduler-storage/`），v0.2 需公网 OSS 替代
2. **Python 包名冲突**：客户端 `app` 与调度中心冲突，本地跑需在各自目录下
3. **bcrypt 版本**：钉死 `bcrypt==4.0.1`（新版本兼容性问题）
4. **Windows 11 22631 无 WSL**：Docker Desktop 不可用，所有服务走原生 Python 启动

---

## 🎯 v0.2 路线图（待启动）

| 优先级 | 目标 | 时间 |
|--------|------|------|
| P0 | 真实训练接入（替换 mock 数据） | 1~2 周 |
| P0 | 公网对象存储（阿里云 OSS） | 1 周 |
| P1 | 商标搜索 + 注册 | 2 周 |
| P1 | 代码签名（SignPath 申请） | 1 周 |
| P2 | 推广文案 + V2EX/HN/知乎发布 | 1 周 |
| P2 | 第二份权重 / 微调任务类型 | 2 周 |

---

## 🔑 关键账户与凭证（敏感，已脱敏）

| 资源 | 标识 |
|------|------|
| GitHub PAT（Classic） | ghp_6TG05***（含 repo+workflow scope） |
| Vercel Token | vcp_6MSfg*** |
| 爱发电创作者主页 | firefly-lm |
| 域名注册商 | 阿里云（凌泷科技名下） |
| 公司主体 | 上海凌泷科技有限公司 |

---

## 📜 文档版本

- 创建：2026-07-25 13:22 GMT+8
- 适用：萤火虫 v0.1 收尾存档
- 下次更新：v0.2 完成时