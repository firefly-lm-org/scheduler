import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000"


def call(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
        except Exception:
            err = e.read().decode()
        return e.code, err


import time as _t
_uname = "smoke_%d" % int(_t.time())
print("=== 1) register user (%s) ===" % _uname)
st, reg = call("POST", "/api/v1/auth/register", {
    "username": _uname, "password": "smoke123"})
print(st, reg)
access = reg.get("access_token")
if not access:
    print("REGISTER FAILED - aborting")
    raise SystemExit(1)

print("=== 2) register node (GPU 24GB -> level3) ===")
st, node = call("POST", "/api/v1/node/register", {
    "node_name": "smoke-node-01",
    "cpu_cores": 16,
    "total_memory_gb": 64.0,
    "gpu_model": "RTX4090",
    "gpu_vram_gb": 24.0,
    "os_type": "Windows",
}, token=access)
print(st, node)

print("=== 3) heartbeat online ===")
st, hb = call("POST", "/api/v1/node/heartbeat", {"status": "online"}, token=access)
print(st, hb)

print("=== 4) node status ===")
st, ns = call("GET", "/api/v1/node/status", token=access)
print(st, ns)

print("=== 5) admin create task ===")
st, ct = call("POST", "/api/v1/admin/tasks", {
    "name": "smoke-task-A", "level": 1, "base_contribution": 10,
    "timeout_sec": 3600, "config": {"lr": 0.001, "epochs": 1}})
print(st, ct)
task_id = ct.get("task_id")

print("=== 6) claim task ===")
st, cl = call("POST", "/api/v1/task/claim", token=access)
print(st, cl)

print("=== 7) progress report ===")
st, pr = call("POST", "/api/v1/task/progress",
              {"current_step": 5, "total_steps": 10, "loss": 0.5}, token=access)
print(st, pr)

print("=== 8) submit task ===")
st, sb = call("POST", "/api/v1/task/submit",
              {"result_object_name": f"tasks/{task_id}/result.bin",
               "result_sha256": "a" * 64,
               "execution_time_sec": 12.5, "total_steps": 10}, token=access)
print(st, sb)

print("=== 9) get task status ===")
st, gt = call("GET", f"/api/v1/task/{task_id}")
print(st, gt)

print("=== 10) admin stats ===")
st, stats = call("GET", "/api/v1/admin/stats")
print(st, json.dumps(stats, ensure_ascii=False, indent=2))

print("\nSMOKE TEST DONE")
