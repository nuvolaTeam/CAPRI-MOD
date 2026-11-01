"""Extract the ammonia-technology cost tables written in CAPRI's envind/ammo_tech.gms to CSV.

CAPRI keeps the cost model of its ammonia technologies in the code itself (source tables
A1-A10 of ammo_tech.gms): investment coefficients, storage time, extra input demands,
fixed operating shares, input prices, application-technique costs, grassland shares,
nitrogen per m3 of manure. This script reads those tables and writes one long-format CSV
each to capri_data/2017/abatement/ammonia/costs/, so the model reads them as data.

GAMS tables are POSITIONAL: a value belongs to the column whose header sits above it, and
rows may stop early (storage time gives only the liquid columns). Values are therefore
matched to headers by character position, not by order.

Usage:  python tools/build/build_ammonia_cost_tables.py <path to ammo_tech.gms>
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "ammonia" / "costs"

# table name -> (row-key column names, name of the column dimension)
TABLES = {
    "p_invCoeff": (["technology", "animal_cat", "manure_system"], "coefficient"),
    "p_storTime": (["region", "manure_system"], "animal_cat"),
    "p_addDemand": (["technology", "animal_cat", "manure_system"], "input"),
    "p_inputCost": (["country"], "item"),
    "p_costParAppl": (["technology", "animal_cat", "manure_system"], "coefficient"),
    "p_sharGL": (["country", "manure_system"], "animal_cat"),
    "p_kgNPerM3": (["activity"], "manure_system"),
    "p_minStorCapND": (["region", "manure_system", "nvz"], "animal_cat"),
    "p_applic": (["country", "animal_cat", "manure_system"], "technology"),
}
# parameter lists ( / key value ... / )
PARAMS = {
    "p_fixedOpCost": ["technology", "animal_cat", "manure_system"],
}
SCALARS = ("p_r",)

_NUM = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")


def _lines(path: Path):
    return [l.rstrip("\r\n") for l in open(path, encoding="latin-1")]


def _strip_comment(l: str) -> str:
    return "" if l.lstrip().startswith("*") else l


def parse_table(lines, name):
    """Return list of (rowkeys tuple, column, value) for Table <name>."""
    start = next(i for i, l in enumerate(lines)
                 if re.match(rf"^\s*Table\s+{name}\s*\(", l, re.I))
    i = start + 1
    out = []
    header = None
    while i < len(lines):
        raw = _strip_comment(lines[i])
        i += 1
        if not raw.strip():
            continue
        if raw.strip().startswith(";") or raw.strip() == ";":
            break
        if raw.strip().startswith("+"):          # continuation block: new header
            header = None
            raw = raw.replace("+", " ", 1)
        toks = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", raw)]
        if header is None:
            header = toks                       # column names with their positions
            continue
        key, rest = toks[0], toks[1:]
        rowkeys = tuple(key[2].split("."))
        for s, e, v in rest:
            if v.endswith(";"):
                v = v[:-1]
            if not _NUM.match(v):
                continue
            # the header whose span overlaps the value, else the nearest by centre
            best, bd = None, None
            for hs, he, hn in header:
                if s < he and e > hs:
                    best, bd = hn, -1
                    break
                d = abs((s + e) / 2 - (hs + he) / 2)
                if bd is None or d < bd:
                    best, bd = hn, d
            out.append((rowkeys, best, float(v)))
        if raw.rstrip().endswith(";"):
            break
    return out


def parse_param(lines, name):
    start = next(i for i, l in enumerate(lines)
                 if re.match(rf"^\s*Parameter\s+{name}\s*\(", l, re.I))
    out = []
    for raw in lines[start + 1:]:
        l = _strip_comment(raw).strip()
        if not l or l == "/":
            if out and l == "/":
                break
            continue
        if l.startswith("/;") or l == ";":
            break
        m = re.match(r"^([\w.]+)\s+([-+0-9.eE]+)", l)
        if m:
            out.append((tuple(m.group(1).split(".")), float(m.group(2))))
    return out


def main(src: Path):
    lines = _lines(src)
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    for name, (keys, coldim) in TABLES.items():
        rows = parse_table(lines, name)
        with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(keys + [coldim, "value"])
            for rk, col, v in rows:
                rk = list(rk) + [""] * (len(keys) - len(rk))
                w.writerow(rk[:len(keys)] + [col, repr(v)])
        report.append((name, len(rows)))
    for name, keys in PARAMS.items():
        rows = parse_param(lines, name)
        with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(keys + ["value"])
            for rk, v in rows:
                w.writerow(list(rk) + [repr(v)])
        report.append((name, len(rows)))
    # (scalars.csv, the discount rate p_r, was written here until 29 October 2026: read by no code, K102)
    return report


if __name__ == "__main__":
    for n, c in main(Path(sys.argv[1])):
        print(f"{n:16s} {c:5d} values")
