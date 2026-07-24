p = r"D:\firefly-client\firefly-client\app\main.py"
for i, l in enumerate(open(p, encoding="utf-8"), 1):
    s = l.rstrip()
    if any(c in s for c in ["register(", "login(", "refresh_token(", "ensure_authenticated(",
                             "register_node(", "query_status(", "execute_task(", "start_heart", "heartbeat_with_status"]):
        print(i, s)
