"""compare_rekeyed.py for JSON files keyed by region: the value under each one-to-one region (old NUTS-2016 code) must
equal the value under its CAPRI unit, number by number (relative tolerance --tol).

    python tools/check/compare_rekeyed_json.py capri_data/2017/environment/nh3_factors_capri.json [--key regions]
"""
import argparse
import csv
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def show(ref, path):
    return subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def diff(a, b, tol, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out.append((path + "/" + str(k), "missing in " + ("new" if k not in b else "old")))
            else:
                diff(a[k], b[k], tol, path + "/" + str(k), out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, f"length {len(a)} -> {len(b)}"))
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, tol, f"{path}[{i}]", out)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if abs(a - b) > tol * max(abs(a), 1e-12):
            out.append((path, f"{a} -> {b}"))
    elif a != b:
        out.append((path, f"{a!r} -> {b!r}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--old-ref", default="next")
    ap.add_argument("--key", default=None, help="the top-level key holding the regions (default: the top level)")
    ap.add_argument("--tol", type=float, default=1e-9)
    a = ap.parse_args()
    old = json.loads(show(a.old_ref, a.path))
    new = json.loads((ROOT / a.path).read_text())
    o, n = old, new
    for k in (a.key.split("/") if a.key else []):      # a path of keys: regional/herds
        o, n = o[k], n[k]
    rmap = list(csv.DictReader(io.StringIO(show(a.old_ref, "capri_data/shared/region_capri_map.csv"))))
    one = {r["region"]: r["capri_region"] for r in rmap if r["relation"] == "one-to-one"}
    out, cmp_ = [], 0
    for r, c in one.items():
        if r in o:
            cmp_ += 1
            if c not in n:
                out.append((c, "missing in new"))
            else:
                diff(o[r], n[c], a.tol, c, out)
    print(f"{a.path}: {cmp_} one-to-one regions compared; {len(out)} differences")
    for x in out[:15]:
        print("  ", *x)
    extra = sorted(set(n) - set(one.values()))
    print(f"  new keys without a one-to-one old region ({len(extra)}): {extra[:30]}")
    return bool(out)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
