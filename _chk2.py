p = r"D:\firefly-client\firefly-client\app\auth.py"
lines = open(p, encoding="utf-8").read().splitlines()
for i, l in enumerate(lines, 1):
    if "def register" in l or "register(" in l or "async def register" in l:
        print(i, l)
print("---- main.py calls to register ----")
p2 = r"D:\firefly-client\firefly-client\app\main.py"
lines2 = open(p2, encoding="utf-8").read().splitlines()
for i, l in enumerate(lines2, 1):
    if "register(" in l or "register," in l or "register)" in l:
        print(i, l)
