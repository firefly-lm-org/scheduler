import os
base = r"D:\firefly-scheduler"
for f in [
    "app/models/task.py",
    "app/models/contribution.py",
    "app/routers/task.py",
    "app/services/contribution_service.py",
]:
    p = os.path.join(base, f)
    if os.path.exists(p):
        print("====", f, "====")
        for i, l in enumerate(open(p, encoding="utf-8"), 1):
            s = l.rstrip()
            if "def " in s or "class " in s or "status" in s.lower() and "=" in s or "Field" in s or "Column" in s:
                print(i, s)
        print()
