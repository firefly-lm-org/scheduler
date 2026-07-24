import base64, json, os, subprocess, sys, tempfile, time

GH = "GITHUB_TOKEN_PLACEHOLDER"
ORG = "firefly-lm-org"
REPO = "scheduler"
BASE = r"D:\firefly-scheduler"

def run(args, method="GET", input_data=None):
    cmd = ["gh", "api"]
    if method != "GET":
        cmd += ["--method", method]
    for a in args:
        cmd.append(a)
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = GH
    kw = {"capture_output": True, "text": True, "env": env}
    if input_data is not None:
        fd, tmp = tempfile.mkstemp(suffix=".json")
        try:
            os.write(fd, json.dumps(input_data, ensure_ascii=False).encode("utf-8"))
            os.close(fd)
            cmd += ["--input", tmp]
        finally:
            pass  # don't delete tmp yet
    r = subprocess.run(cmd, **kw)
    if input_data is not None and 'tmp' in dir():
        try: os.unlink(tmp)
        except: pass
    if r.returncode != 0:
        print(f"FAIL {args[0] if args else '?'}: {r.stderr[:200]}", file=sys.stderr)
        return None
    if r.stdout.strip():
        try:
            return json.loads(r.stdout)
        except:
            return r.stdout.strip()
    return {}

files = {
    "requirements.txt": os.path.join(BASE, "requirements.txt"),
    "app/routers/node.py": os.path.join(BASE, "app", "routers", "node.py"),
    "app/utils/minio_client.py": os.path.join(BASE, "app", "utils", "minio_client.py"),
}

print("=== Creating blobs ===")
blobs = {}
for dest, src in files.items():
    raw = open(src, 'rb').read()
    b64 = base64.b64encode(raw).decode()
    resp = run(
        [f"repos/{ORG}/{REPO}/git/blobs", "--method", "POST",
         "--field", f"content={b64}", "--field", "encoding=base64"],
        method="POST"
    )
    if resp and isinstance(resp, dict) and 'sha' in resp:
        blobs[dest] = resp['sha']
        print(f"  {dest} => {resp['sha'][:12]}")
    else:
        print(f"  FAILED: {dest}", file=sys.stderr)
        sys.exit(1)

print("\n=== HEAD info ===")
ref = run([f"repos/{ORG}/{REPO}/git/ref/heads/main"])
head_sha = ref['object']['sha']
print(f"HEAD: {head_sha}")
commit_info = run([f"repos/{ORG}/{REPO}/git/commits/{head_sha}"])
base_tree = commit_info['tree']['sha']
print(f"Base tree: {base_tree}")

print("\n=== Creating tree ===")
tree_items = [{"path": k, "sha": v, "mode": "100644", "type": "blob"} for k, v in blobs.items()]
tree_resp = run(
    [f"repos/{ORG}/{REPO}/git/trees", "--method", "POST"],
    method="POST",
    input_data={"base_tree": base_tree, "tree": tree_items}
)
tree_sha = tree_resp.get('sha', '')
print(f"New tree: {tree_sha}")

print("\n=== Creating commit ===")
msg = """fix: bcrypt pin, ORM query, datetime, minio timedelta

- Pin bcrypt==4.0.1 (bcrypt>=4.1 breaks passlib backend detection)
- node.py: select(Node) -> scalar_one_or_none() (was Row -> AttributeError)
- node.py: last_heartbeat = datetime.utcnow() (was str -> asyncpg DataError)
- minio_client.py: expires=int -> timedelta(seconds=int) (minio API)"""
commit_resp = run(
    [f"repos/{ORG}/{REPO}/git/commits", "--method", "POST"],
    method="POST",
    input_data={"message": msg, "tree": tree_sha, "parents": [head_sha]}
)
new_sha = commit_resp.get('sha', '')
print(f"New commit: {new_sha}")

print("\n=== Updating branch ===")
r2 = run(
    [f"repos/{ORG}/{REPO}/git/refs/heads/main", "--method", "PATCH"],
    method="PATCH",
    input_data={"sha": new_sha}
)
if r2 is not None:
    print(f"Branch main updated to {new_sha[:12]}!")
    time.sleep(4)
    runs = run([f"repos/{ORG}/{REPO}/actions/runs"])
    if runs and runs.get('workflow_runs'):
        latest = runs['workflow_runs'][0]
        print(f"CI #{latest['run_number']}: {latest['status']} / {latest['conclusion']}")
else:
    print("Branch update response:", r2)
