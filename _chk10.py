import os
base = r"D:\firefly-scheduler\app\routers"
# admin create_task body (upload to minio)
p = os.path.join(base, "admin.py")
lines = open(p, encoding="utf-8").read().splitlines()
print("==== admin.py create_task 27-90 ====")
for i in range(27, min(90, len(lines)+1)):
    print(i, lines[i-1])
# task router: download / package endpoint
p2 = os.path.join(base, "task.py")
txt = open(p2, encoding="utf-8").read()
for i, l in enumerate(txt.splitlines(), 1):
    if "package" in l.lower() or "minio" in l.lower() or "@router.get" in l or "presign" in l.lower() or "download" in l.lower():
        print("task.py L%d" % i, l.rstrip())
