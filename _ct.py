import httpx, json, time, os
BASE = "http://localhost:8000"
u = "ct_%d" % int(time.time())
pw = "ct_pass_123"
r = httpx.post(f"{BASE}/api/v1/auth/register", json={"username": u, "password": pw})
print("register:", r.status_code, r.text[:120])
tk = r.json()["access_token"]
H = {"Authorization": f"Bearer {tk}"}
# upload package
pkg = r"D:\firefly-scheduler\_e2e\sample_package.zip"
files = {"package": ("package.zip", open(pkg, "rb"), "application/zip")}
data = {"name": "ct1", "level": "1", "config": "{}"}
r2 = httpx.post(f"{BASE}/api/v1/admin/tasks", headers=H, data=data, files=files)
print("create_task:", r2.status_code, r2.text[:300])
# check minio
try:
    from app.utils.minio_client import minio_client, settings
    objs = list(minio_client.list_objects(settings.minio_bucket, prefix="tasks/", recursive=True))
    print("minio objects:", [o.object_name for o in objs])
except Exception as e:
    print("minio err:", repr(e))
