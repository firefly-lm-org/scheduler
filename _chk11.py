p = r"D:\firefly-client\firefly-client\app\task_executor.py"
for i, l in enumerate(open(p, encoding="utf-8"), 1):
    s = l.rstrip()
    if "def execute_task" in s or "httpx" in s or "AsyncClient" in s or "submit" in s.lower() or "download" in s.lower() or "presign" in s.lower():
        print(i, s)
