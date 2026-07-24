import os
base = r"D:\firefly-scheduler"
for f in ["app/services/contribution_service.py", "app/routers/task.py", "app/schemas/task.py"]:
    p = os.path.join(base, f)
    if os.path.exists(p):
        lines = open(p, encoding="utf-8").read().splitlines()
        print("====", f, "====")
        for i, l in enumerate(lines, 1):
            s = l.rstrip()
            if "def " in s or "class " in s or "aggreg" in s.lower() or "contribution" in s.lower() or "weight" in s.lower() or "merge" in s.lower():
                print(i, s)
        print()
