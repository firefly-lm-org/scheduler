import requests, base64, json, os

PAT = "GITHUB_TOKEN_PLACEHOLDER"
ORG = "firefly-lm-org"
REPO = "scheduler"
LOCAL_BASE = r"D:\firefly-scheduler"
H = {"Authorization": f"Bearer {PAT}", "Accept": "application/vnd.github+json",
     "X-GitHub-Api-Version": "2022-11-28"}

def gh(method, path, data=None):
    url = f"https://api.github.com/{path}"
    r = requests.request(method, url, headers=H, json=data, timeout=60)
    if r.status_code >= 400:
        print(f"ERR {method} {path} -> {r.status_code}: {r.text[:200]}")
        return None
    return r.json() if r.content else {}

print("=== 1) remote main sha ===")
ref = gh("GET", f"repos/{ORG}/{REPO}/git/ref/heads/main")
if not ref: raise SystemExit(1)
remote_sha = ref["object"]["sha"]
print("remote main:", remote_sha[:8])

print("=== 2) remote commit tree ===")
commit = gh("GET", f"repos/{ORG}/{REPO}/git/commits/{remote_sha}")
if not commit: raise SystemExit(1)
remote_tree = commit["tree"]["sha"]
print("remote tree:", remote_tree[:8])

files = [
    ("app/models/aggregation.py",          "app/models/aggregation.py"),
    ("app/models/task.py",                  "app/models/task.py"),
    ("app/services/aggregation_service.py",  "app/services/aggregation_service.py"),
    ("app/routers/aggregation.py",          "app/routers/aggregation.py"),
    ("app/services/background_tasks.py",   "app/services/background_tasks.py"),
    ("app/main.py",                          "app/main.py"),
    ("app/config.py",                        "app/config.py"),
    ("test_aggregation.py",                 "test_aggregation.py"),
]

print("=== 3) create blobs ===")
blobs = []
for local_rel, repo_path in files:
    abs_path = os.path.join(LOCAL_BASE, local_rel)
    if not os.path.exists(abs_path):
        print(f"  SKIP: {local_rel} (not found)")
        continue
    content = open(abs_path, "rb").read()
    b = gh("POST", f"repos/{ORG}/{REPO}/git/blobs",
           {"content": base64.b64encode(content).decode(), "encoding": "base64"})
    if b:
        blobs.append((repo_path, b["sha"]))
        print(f"  blob {repo_path}: {b['sha'][:8]}")

print("=== 4) create tree ===")
tree_items = [{"path": p, "mode": "100644", "type": "blob", "sha": sha} for p, sha in blobs]
tree = gh("POST", f"repos/{ORG}/{REPO}/git/trees",
          {"base_tree": remote_tree, "tree": tree_items})
if not tree: raise SystemExit(1)
print("new tree:", tree["sha"][:8])

local_sha = "cb80436b38c7c77a4abd3d2e3cc4a40e9c487624"
print("=== 5) create commit (merge parents: remote + local) ===")
nc = gh("POST", f"repos/{ORG}/{REPO}/git/commits",
        {"message": "feat: weight aggregation worker v0.1\n\n- FedAvg aggregation service\n- AggregationRecord model\n- Auto polling (5min) + manual trigger API\n- POST /api/v1/admin/aggregate\n- GET /api/v1/admin/aggregation-records",
         "tree": tree["sha"],
         "parents": [remote_sha, local_sha]})
if not nc: raise SystemExit(1)
print("new commit:", nc["sha"][:8])

print("=== 6) update ref ===")
ok = gh("PATCH", f"repos/{ORG}/{REPO}/git/refs/heads/main",
         {"sha": nc["sha"]})
if ok:
    print("PUSHED OK:", nc["sha"][:8])
else:
    print("REF UPDATE FAILED")
