import subprocess, base64, json, os, sys

PAT = "GITHUB_TOKEN_PLACEHOLDER"
ORG = "firefly-lm-org"

def gh(args, data=None):
    cmd = ["gh", "api", "--header", "Authorization: Bearer " + PAT] + args
    if data is not None:
        cmd += ["--input", "-"]
    p = subprocess.run(cmd, input=json.dumps(data).encode("utf-8") if data is not None else None,
                       capture_output=True)
    out = p.stdout.decode("utf-8", "replace")
    if p.returncode != 0:
        sys.stderr.write("GH ERR (" + " ".join(args[:3]) + "): " + out + "\n" + p.stderr.decode("utf-8","replace") + "\n")
        raise SystemExit(1)
    return out

def push_files(repo, branch, files):
    # files: list of (abs_path, repo_path)
    base = gh(["repos/%s/%s" % (ORG, repo)])  # get default branch / sha
    # get ref
    ref = json.loads(gh(["repos/%s/%s/git/ref/heads/%s" % (ORG, repo, branch)]))
    base_sha = ref["object"]["sha"]
    # get commit + tree
    commit = json.loads(gh(["repos/%s/%s/git/commits/%s" % (ORG, repo, base_sha)]))
    base_tree = commit["tree"]["sha"]
    blobs = []
    for abs_path, repo_path in files:
        content = open(abs_path, "rb").read()
        b = json.loads(gh(["repos/%s/%s/git/blobs" % (ORG, repo)],
                          {"content": base64.b64encode(content).decode(), "encoding": "base64"}))
        blobs.append((repo_path, b["sha"]))
    tree_items = [{"path": p, "mode": "100644", "type": "blob", "sha": sha} for p, sha in blobs]
    tree = json.loads(gh(["repos/%s/%s/git/trees" % (ORG, repo)],
                         {"base_tree": base_tree, "tree": tree_items}))
    new_commit = json.loads(gh(["repos/%s/%s/git/commits" % (ORG, repo)],
                               {"message": "fix: admin auth guard + client register/login recursion + windows signal handler",
                                "tree": tree["sha"], "parents": [base_sha]}))
    gh(["repos/%s/%s/git/refs/heads/%s" % (ORG, repo, branch)],
       {"sha": new_commit["sha"], "force": True})
    print("pushed %s -> %s (%s)" % (repo, branch, new_commit["sha"][:8]))

# scheduler: admin.py auth fix
push_files("scheduler", "main", [
    (r"D:\firefly-scheduler\app\routers\admin.py", "app/routers/admin.py"),
])
# client: main.py recursion + windows signal fix
push_files("firefly-client", "main", [
    (r"D:\firefly-client\firefly-client\app\main.py", "app/main.py"),
])
print("ALL DONE")
