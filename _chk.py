base = r"D:\firefly-client\firefly-client\app"
for fn in ["auth.py", "config.py", "main.py"]:
    p = base + "\\" + fn
    print("==== ", fn, " ====")
    for i, line in enumerate(open(p, encoding="utf-8"), 1):
        s = line.rstrip("\n")
        if any(k in s for k in ["save_config", "json.dumps", "model_dump", "server_url", "CONFIG_DIR", "FIREFLY_HOME", "def save_config"]):
            print(f"{i}: {s}")
