import base64, json, os, subprocess, sys, tempfile

GH = "GITHUB_TOKEN_PLACEHOLDER"
ORG = "firefly-lm-org"
REPO = "scheduler"

def gh_api(args, method="GET", input_data=None):
    cmd = ["gh", "api", "--header", f"Authorization: Bearer {GH}"] + args
    kw = {}
    if method != "GET":
        cmd += ["--method", method]
    if input_data:
        # write JSON to temp file and use --input
        fd, tmp = tempfile.mkstemp(suffix=".json")
        try:
            os.write(fd, json.dumps(input_data, ensure_ascii=False).encode("utf-8"))
            os.close(fd)
            cmd += ["--input", tmp]
            kw["capture_output"] = True
            kw["text"] = True
            r = subprocess.run(cmd, **kw)
        finally:
            os.unlink(tmp)
    else:
        kw["capture_output"] = True
        kw["text"] = True
        r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        print(f"GH FAIL {' '.join(args[:3])}: {r.stderr[:200]}", file=sys.stderr)
        return None
    if r.stdout.strip():
        try:
            return json.loads(r.stdout)
        except:
            return r.stdout.strip()
    return {}

files = {
    "requirements.txt": "requirements.txt",
    "app/routers/node.py": "app/routers/node.py",
    "app/utils/minio_client.py": "app/utils/minio_client.py",
}

# Step 1: Create blobs
print("=== Creating blobs ===")
blobs = {}
for dest, src in files.items():
    raw = open(src, 'rb').read()
    b64 = base64.b64encode(raw).decode()
    resp = gh_api([
        "repos", ORG, REPO, "git", "blobs",
        "--field", f"content={b64}",
        "--field", "encoding=base64",
        "--method", "POST"
    ])
    if resp and isinstance(resp, dict) and 'sha' in resp:
        blobs[dest] = resp['sha']
        print(f"  {dest} => {resp['sha'][:12]}")
    else:
        print(f"  FAILED: {dest} => {resp}", file=sys.stderr)

if len(blobs) != 3:
    print("Not all blobs created, aborting.", file=sys.stderr)
    sys.exit(1)

# Step 2: Get current HEAD
ref = gh_api(["repos", ORG, REPO, "git", "ref", "refs", "heads", "main"])
head_sha = ref['object']['sha']
print(f"\nHEAD: {head_sha}")

commit_info = gh_api(["repos", ORG, REPO, "git", "commits", head_sha])
base_tree = commit_info['tree']['sha']
print(f"Base tree: {base_tree}")

# Step 3: Create tree
tree_items = [
    {"path": k, "sha": v, "mode": "100644", "type": "blob"}
    for k, v in blobs.items()
]
tree_resp = gh_api(
    ["repos", ORG, REPO, "git", "trees", "--method", "POST"],
    input_data={"base_tree": base_tree, "tree": tree_items}
)
if not tree_resp or 'sha' not in tree_resp:
    print(f"Tree creation failed: {tree_resp}", file=sys.stderr)
    sys.exit(1)
tree_sha = tree_resp['sha']
print(f"New tree: {tree_sha}")

# Step 4: Create commit
msg = """fix: bcrypt pin, ORM query, datetime, minio timedelta

- Pin bcrypt==4.0.1 (bcrypt>=4.1 breaks passlib backend detection)
- node.py: select(Node) -> scalar_one_or_none() (was Row -> AttributeError)
- node.py: last_heartbeat = datetime.utcnow() (was str -> asyncpg DataError)
- minio_client.py: expires=int -> timedelta(seconds=int) (minio API)"""
commit_resp = gh_api(
    ["repos", ORG, REPO, "git", "commits", "--method", "POST"],
    input_data={"message": msg, "tree": tree_sha, "parents": [head_sha]}
)
if not commit_resp or 'sha' not in commit_resp:
    print(f"Commit creation failed: {commit_resp}", file=sys.stderr)
    sys.exit(1)
new_sha = commit_resp['sha']
print(f"New commit: {new_sha}")

# Step 5: Update branch
r2 = subprocess.run(
    ["gh", "api", "--header", f"Authorization: Bearer {GH}",
     "repos", ORG, REPO, "git", "refs", "heads", "main",
     "--method", "PATCH",
     "-f", f"sha={new_sha}"],
    capture_output=True, text=True
)
if r2.returncode == 0:
    print(f"\nBranch main updated to {new_sha[:12]}!")
    # Check CI
    import time; time.sleep(3)
    runs = gh_api(["repos", ORG, REPO, "actions", "runs"])
    if runs and 'workflow_runs' in runs and runs['workflow_runs']:
        latest = runs['workflow_runs'][0]
        print(f"CI Run #{latest['run_number']}: {latest['status']} / {latest['conclusion']}")
else:
    print(f"Ref update FAIL: {r2.stderr[:200]}", file=sys.stderr)
