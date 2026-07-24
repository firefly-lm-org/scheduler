import importlib
for m in ["safetensors", "numpy", "torch"]:
    try:
        mod = importlib.import_module(m)
        print(m, "OK", getattr(mod, "__version__", "?"))
    except ImportError:
        print(m, "MISSING")
