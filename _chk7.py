import os
base = r"D:\firefly-scheduler"
# find get_current_admin / get_current_user
for fn in ["app/auth.py", "app/deps.py", "app/routers/admin.py"]:
    p = os.path.join(base, fn)
    if not os.path.exists(p):
        print("MISSING", fn); continue
    print("==== ", fn, "====")
    for i, l in enumerate(open(p, encoding="utf-8"), 1):
        s = l.rstrip()
        if "get_current_admin" in s or "get_current_user" in s or "require" in s.lower() and "admin" in s.lower():
            print(i, s)
    if fn.endswith("admin.py"):
        for i, l in enumerate(open(p, encoding="utf-8"), 1):
            if i <= 30:
                print(i, l.rstrip())
