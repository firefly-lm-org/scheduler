p = r"D:\firefly-client\firefly-client\app\main.py"
lines = open(p, encoding="utf-8").read().splitlines()
print("==== client main.py start() body (lines 87-160) ====")
for i in range(87, min(160, len(lines)+1)):
    print(i, lines[i-1])

print("\n==== admin.py get_current_admin / auth imports ====")
p2 = r"D:\firefly-scheduler\app\routers\admin.py"
for i, l in enumerate(open(p2, encoding="utf-8"), 1):
    s = l.rstrip()
    if "get_current_admin" in s or "from app" in s.lower() and "auth" in s.lower() or "import" in s and "admin" in s.lower():
        print(i, s)
