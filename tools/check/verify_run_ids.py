"""Recompute every run id of a capri-mod results store from its tables alone, without capri-mod's code: the recipe
"capri-mod run id 1" of capri_mod/io_results.py (run_id_of, rows_digest), written again here as an independent check.

    python tools/check/verify_run_ids.py RESULTS_STORE
"""
import hashlib, json, math, sys
from deltalake import DeltaTable
root = sys.argv[1]
TEXT = ["block", "region", "dim5", "cols", "rows", "capri_region", "capri_dim5", "capri_cols", "capri_rows", "unit"]
runs = DeltaTable(f"{root}/runs").to_pyarrow_table().to_pylist()
long = DeltaTable(f"{root}/long").to_pyarrow_table().to_pylist()
by = {}
for r in long:
    by.setdefault(r["run_id"], []).append(r)
ok = 0
for rec in runs:
    rows = by.get(rec["run_id"], [])
    t = lambda v: "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)
    n = lambda v: "nan" if v is None or math.isnan(float(v)) else float(v).hex()
    lines = sorted(json.dumps([t(r[c]) for c in TEXT] + [int(r["year"]), n(r["value"])], ensure_ascii=False,
                              separators=(",", ":")) for r in rows)
    dig = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    rid = hashlib.sha256("\n".join(["capri-mod run id 1", rec["kind"], rec["scenario"], rec["reference_run_id"] or "",
                                     rec["fingerprint"], dig]).encode()).hexdigest()
    print(rec["kind"], rec["scenario"][:24], rec["run_id"][:12], "OK" if rid == rec["run_id"] else "MISMATCH", len(rows))
    ok += rid == rec["run_id"]
print(f"{ok}/{len(runs)} ids recomputed")
