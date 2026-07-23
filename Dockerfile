# ── 基础镜像 ────────────────────────
FROM python:3.12-slim

# ── 环境变量 ────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ── 安装依赖 ────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── 复制代码 ────────────────────────
COPY . .

# ── 暴露端口 ────────────────────────
EXPOSE 8000

# ── 启动命令（开发模式 + 热重载） ──
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
