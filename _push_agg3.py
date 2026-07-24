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
        print(f"ERR {method} {path} -> {r.status_code}: {r.text[:300]}")
        return None
    return r.json() if r.content else {}

# 1) remote main sha
ref = gh("GET", f"repos/{ORG}/{REPO}/git/ref/heads/main")
remote_sha = ref["object"]["sha"]
print("remote main:", remote_sha[:8])

# 2) remote commit tree
commit = gh("GET", f"repos/{ORG}/{REPO}/git/commits/{remote_sha}")
remote_tree = commit["tree"]["sha"]
print("remote tree:", remote_tree[:8])

# 3) create blobs
files = [
    ("app/models/aggregation.py",           "app/models/aggregation.py"),
    ("app/models/task.py",                   "app/models/task.py"),
    ("app/services/aggregation_service.py", "app/services/aggregation_service.py"),
    ("app/routers/aggregation.py",           "app/routers/aggregation.py"),
    ("app/services/background_tasks.py",    "app/services/background_tasks.py"),
    ("app/main.py",                          "app/main.py"),
    ("app/config.py",                        "app/config.py"),
    ("test_aggregation.py",                 "test_aggregation.py"),
]
blobs = []
for local_rel, repo_path in files:
    abs_path = os.path.join(LOCAL_BASE, local_rel)
    content = open(abs_path, "rb").read()
    b = gh("POST", f"repos/{ORG}/{REPO}/git/blobs",
           {"content": base64.b64encode(content).decode(), "encoding": "base64"})
    blobs.append((repo_path, b["sha"]))
    print(f"  blob {repo_path}: {b['sha'][:8]}")

# 4) create tree
tree_items = [{"path": p, "mode": "100644", "type": "blob", "sha": sha} for p, sha in blobs]
tree = gh("POST", f"repos/{ORG}/{REPO}/git/trees",
          {"base_tree": remote_tree, "tree": tree_items})
print("new tree:", tree["sha"][:8])

# 5) create commit (single parent = remote main)
nc = gh("POST", f"repos/{ORG}/{REPO}/git/commits",
        {"message": "feat: weight aggregation worker v0.1\n\n- FedAvg aggregation service (simple mean)\n- AggregationRecord model + db table\n- Auto polling every 5min + manual trigger API\n- POST /api/v1/admin/aggregate\n- GET /api/v1/admin/aggregation-records\n- asyncio.Lock prevents concurrent aggregation",
         "tree": tree["sha"],
         "parents": [remote_sha]})
print("new commit:", nc["sha"][:8])

# 6) update ref
ok = gh("PATCH", f"repos/{ORG}/{REPO}/git/refs/heads/main", {"sha": nc["sha"]})
if ok:
    print("PUSHED OK:", nc["sha"][:8])
else:
    print("REF UPDATE FAILED - trying force...")
    ok2 = gh("PATCH", f"repos/{ORG}/{REPO}/git/refs/heads/main", {"sha": nc["sha"], "force": True})
    if ok2:
        print("FORCE PUSHED OK:", nc["sha"][:8])
