import os
p = r"D:\firefly-client\firefly-client\app\heartbeat.py"
print("exists:", os.path.exists(p))
if os.path.exists(p):
    for i, l in enumerate(open(p, encoding="utf-8"), 1):
        s = l.rstrip()
        if "def " in s and ("heart" in s.lower() or "start" in s.lower()):
            print(i, s)
