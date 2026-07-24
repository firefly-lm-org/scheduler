# 1) user model: is_admin?
p = r"D:\firefly-scheduler\app\models\user.py"
for i, l in enumerate(open(p, encoding="utf-8"), 1):
    s = l.rstrip()
    if "is_admin" in s or "admin" in s.lower() or "class User" in s:
        print("user.py L%d" % i, s)
# 2) get_current_user impl in node.py
p2 = r"D:\firefly-scheduler\app\routers\node.py"
for i, l in enumerate(open(p2, encoding="utf-8"), 1):
    if 24 <= i <= 52:
        print("node.py L%d" % i, l.rstrip())
