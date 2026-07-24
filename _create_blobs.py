import base64, json, os, subprocess, sys

GH = "GITHUB_TOKEN_PLACEHOLDER"
ORG = "firefly-lm-org"
REPO = "scheduler"

def gh(args, capture=True):
    cmd = ["gh", "api", "--header", f"Authorization: Bearer {GH}"] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
        print(r.stderr[:500], file=sys.stderr)
        return None
    if capture:
        try:
            return json.loads(r.stdout)
        except:
            return r.stdout.strip()
    return True

files = {
    "requirements.txt": "requirements.txt",
    "app/routers/node.py": "app/routers/node.py",
    "app/utils/minio_client.py": "app/utils/minio_client.py",
}

# Step 1: Create blobs
print("Creating blobs...")
blobs = {}
for dest, src in files.items():
    raw = open(src, 'rb').read()
    b64 = base64.b64encode(raw).decode()
    resp = gh(["repos", ORG, REPO, "git", "blobs", "--field", f"content={b64}", "--field", "encoding=base64"])
    if resp and 'sha' in resp:
        blobs[dest] = resp['sha']
        print(f"  {dest} => {resp['sha'][:12]}")
    else:
        print(f"  FAILED: {dest}", file=sys.stderr)

# Step 2: Get current HEAD
ref = gh(["repos", ORG, REPO, "git", "ref", "refs/heads/main"])
head_sha = ref['object']['sha']
print(f"HEAD: {head_sha}")

commit_info = gh(["repos", ORG, REPO, "git", "commits", head_sha])
base_tree = commit_info['tree']['sha']
print(f"Base tree: {base_tree}")

# Step 3: Create tree
tree_items = [
    {"path": k, "sha": v, "mode": "100644", "type": "blob"}
    for k, v in blobs.items()
]
tree_body = json.dumps({"base_tree": base_tree, "tree": tree_items}, ensure_ascii=False)
tree_tmp = os.path.join(os.environ['TEMP'], "_tree.json")
with open(tree_tmp, 'w', encoding='utf-8') as f:
    f.write(tree_body)
print(f"Tree JSON written ({len(tree_body)} bytes)")

r = subprocess.run(
    ["gh", "api", "--header", f"Authorization: Bearer {GH}",
     "repos", ORG, REPO, "git", "trees", "--method", "POST",
     "--input", tree_tmp],
    capture_output=True, text=True
)
if r.returncode != 0:
    print(f"Tree FAIL: {r.stderr[:300]}", file=sys.stderr)
else:
    tree_resp = json.loads(r.stdout)
    print(f"Tree SHA: {tree_resp.get('sha', 'NO_SHA')}")

# Step 4: Create commit
msg = "fix: bcrypt pin, ORM query, datetime, minio timedelta\n\n- Pin bcrypt==4.0.1\n- node.py: select(Node) -> scalar_one_or_none() (was Row)\n- node.py: last_heartbeat = datetime.utcnow() (was str)\n- minio_client.py: expires=int -> timedelta(seconds=int)"
commit_body = json.dumps({
    "message": msg,
    "tree": tree_resp.get('sha'),
    "parents": [head_sha]
}, ensure_ascii=False)
commit_tmp = os.path.join(os.environ['TEMP'], "_commit.json")
with open(commit_tmp, 'w', encoding='utf-8') as f:
    f.write(commit_body)
print(f"Commit JSON written ({len(commit_body)} bytes)")

r = subprocess.run(
    ["gh", "api", "--header", f"Authorization: Bearer {GH}",
     "repos", ORG, REPO, "git", "commits", "--method", "POST",
     "--input", commit_tmp],
    capture_output=True, text=True
)
if r.returncode != 0:
    print(f"Commit FAIL: {r.stderr[:300]}", file=sys.stderr)
else:
    commit_resp = json.loads(r.stdout)
    new_sha = commit_resp.get('sha', '')
    print(f"Commit SHA: {new_sha}")

    # Step 5: Update branch
    r2 = subprocess.run(
        ["gh", "api", "--header", f"Authorization: Bearer {GH}",
         "repos", ORG, REPO, "git", "refs", "heads", "main",
         "--method", "PATCH",
         "-f", f"sha={new_sha}"],
        capture_output=True, text=True
    )
    if r2.returncode == 0:
        print(f"Branch main updated to {new_sha[:12]}!")
    else:
        print(f"Ref update FAIL: {r2.stderr[:300]}", file=sys.stderr)
