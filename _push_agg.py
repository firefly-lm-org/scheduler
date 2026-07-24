import subprocess, base64, json, os, sys, re

PAT = "GITHUB_TOKEN_PLACEHOLDER"
ORG = "firefly-lm-org"
REPO = "scheduler"

def gh(args, data=None, token=PAT):
    cmd = ["gh", "api"] + args
    if data is not None:
        cmd += ["--input", "-"]
    p = subprocess.run(cmd, input=json.dumps(data).encode("utf-8") if data is not None else None,
                       capture_output=True, env={**os.environ, "GH_TOKEN": token, "HTTP_TIMEOUT": "60"})
    out = p.stdout.decode("utf-8", "replace")
    if p.returncode != 0:
        sys.stderr.write("GH ERR " + " ".join(args[:3]) + ": " + out[:300] + "\n")
        raise SystemExit(p.returncode)
    return out

# Get remote main sha
remote_ref = json.loads(gh(["repos", ORG, REPO, "git", "ref", "heads", "main"]))
remote_sha = remote_ref["object"]["sha"]
print("remote main sha:", remote_sha[:8])

# Get remote commit to find its tree
remote_commit = json.loads(gh(["repos", ORG, REPO, "git", "commits", remote_sha]))
remote_tree = remote_commit["tree"]["sha"]
print("remote tree sha:", remote_tree[:8])

# Files to push (from local working directory, relative to D:\firefly-scheduler)
LOCAL_BASE = r"D:\firefly-scheduler"
files = [
    ("app/models/aggregation.py",          "app/models/aggregation.py"),
    ("app/models/task.py",                  "app/models/task.py"),
    ("app/services/aggregation_service.py",  "app/services/aggregation_service.py"),
    ("app/routers/aggregation.py",          "app/routers/aggregation.py"),
    ("app/services/background_tasks.py",     "app/services/background_tasks.py"),
    ("app/main.py",                          "app/main.py"),
    ("app/config.py",                        "app/config.py"),
    ("test_aggregation.py",                 "test_aggregation.py"),
]

blobs = []
for local_rel, repo_path in files:
    abs_path = os.path.join(LOCAL_BASE, local_rel)
    if not os.path.exists(abs_path):
        print(f"SKIP (not found): {local_rel}")
        continue
    content = open(abs_path, "rb").read()
    b = json.loads(gh(["repos", ORG, REPO, "git", "blobs"],
                      {"content": base64.b64encode(content).decode(), "encoding": "base64"}))
    blobs.append((repo_path, b["sha"]))
    print(f"  blob {repo_path}: {b['sha'][:8]}")

# Build tree on top of remote main tree
tree_items = [{"path": p, "mode": "100644", "type": "blob", "sha": sha} for p, sha in blobs]
tree = json.loads(gh(["repos", ORG, REPO, "git", "trees"],
                     {"base_tree": remote_tree, "tree": tree_items}))
print("new tree sha:", tree["sha"][:8])

# Create merge commit (parent1 = remote main, parent2 = local aggregation commit)
local_commit_sha = "cb80436b38c7c77a4abd3d2e3cc4a40e9c487624"
new_commit = json.loads(gh(["repos", ORG, REPO, "git", "commits"],
                          {"message": "feat: weight aggregation worker v0.1\n\n- FedAvg weight aggregation (simple mean)\n- AggregationRecord model + service\n- Manual trigger + auto polling (5min)\n- POST /api/v1/admin/aggregate\n- GET /api/v1/admin/aggregation-records\n- asyncio.Lock prevents concurrent aggregation",
                           "tree": tree["sha"],
                           "parents": [remote_sha, local_commit_sha]}))
print("new commit sha:", new_commit["sha"][:8])

# Update remote main ref
gh(["repos", ORG, REPO, "git", "refs", "heads", "main"],
   {"sha": new_commit["sha"]})
print("PUSHED OK ->", new_commit["sha"][:8])
