import os
# 1) admin.py 路由与鉴权
p = r"D:\firefly-scheduler\app\routers\admin.py"
print("==== admin.py: routes & dependencies ====")
for i, l in enumerate(open(p, encoding="utf-8"), 1):
    s = l.rstrip()
    if "@router" in s or "Depends" in s or "get_current_admin" in s or "def " in s and "admin" in s.lower():
        print(i, s)

# 2) client main.py start + signal handler
p2 = r"D:\firefly-client\firefly-client\app\main.py"
print("==== client main.py: start & signal ====")
text = open(p2, encoding="utf-8").read()
for i, l in enumerate(text.splitlines(), 1):
    s = l.rstrip()
    if "def start" in s or "add_signal" in s or "signal" in s.lower() or "asyncio.run" in s or "await" in s and "heart" in s.lower():
        print(i, s)

# 3) client heartbeat.py start func
p3 = r"D:\firefly-client\firefly-client\app\heartbeat.py"
print("==== client heartbeat.py: start func  ====")
for i, l in enumerate(open(p3, encoding="utf-8"), 1):
    s = l.rstrip()
    if "def start" in s or "add_signal" in s or "signal" in s.lower() or "asyncio" in s.lower():
        print(i, s)
