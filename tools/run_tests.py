"""Minimal test runner for environments without pytest installed."""
import sys, warnings, inspect, pathlib
warnings.filterwarnings("ignore")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import capri_python.tests.test_capri as T
from capri_python.data.loaders import load_all_data
from capri_python.model import CAPRIModel

data = load_all_data("capri_data")
model = CAPRIModel(data_dir="capri_data", verbose=False)
fx = {"data": data, "model": model}
p = f = 0
for name, fn in sorted(vars(T).items()):
    if not name.startswith("test_") or not callable(fn):
        continue
    kw = {a: fx[a] for a in inspect.signature(fn).parameters if a in fx}
    try:
        fn(**kw); print(f"PASS  {name}"); p += 1
    except Exception as e:
        print(f"FAIL  {name}: {str(e)[:120]}"); f += 1
print(f"\n{p} passed, {f} failed")
sys.exit(1 if f else 0)
