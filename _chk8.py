import os, glob
base = r"D:\firefly-scheduler\app"
for f in glob.glob(base + "/**/*.py", recursive=True):
    txt = open(f, encoding="utf-8").read()
    if "get_current_admin" in txt or "get_current_user" in txt or "oauth2" in txt.lower() or "HTTPBearer" in txt:
        rel = os.path.relpath(f, base)
        print("FILE:", rel)
        for i, l in enumerate(txt.splitlines(), 1):
            if "get_current_admin" in l or "get_current_user" in l or "def require" in l or "HTTPBearer" in l or "oauth2" in l or "SecurityScopes" in l:
                print("  L%d" % i, l.rstrip())
