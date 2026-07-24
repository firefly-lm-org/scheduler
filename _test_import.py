try:
    import app.main as m
    print("IMPORT OK, app =", type(m.app).__name__, flush=True)
    print("routes:", [getattr(r, 'path', '?') for r in m.app.routes], flush=True)
except Exception as e:
    import traceback
    print("IMPORT ERROR:", type(e).__name__, str(e), flush=True)
    traceback.print_exc()
