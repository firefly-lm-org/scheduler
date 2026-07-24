import importlib.util, inspect
spec = importlib.util.find_spec("app.main")
print("app.main origin:", spec.origin if spec else None)
import app.main as m
print("=== register source ===")
print("\n".join(inspect.getsource(m.register).splitlines()[:14]))
print("=== call with explicit kwargs to test binding ===")
# 模拟 typer 解析：用 --username/--password 实际调用
import asyncio
from app.config import ClientConfig, load_config
cfg = load_config()
print("before: server_url=", cfg.server_url)
# 直接调用底层 auth.register 验证业务层
async def t():
    ok = await m.register.__wrapped__ if hasattr(m.register,'__wrapped__') else None
try:
    # 用 typer 的方式无法直接，改为打印 main module 文件 mtime
    import os
    print("file mtime:", os.path.getmtime(spec.origin))
except Exception as e:
    print("err", e)
