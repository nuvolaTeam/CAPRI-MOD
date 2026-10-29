"""CAPRI inputs of the remaining mitigation options (feed additives, genetics, soil), to CSV.

  trends_1730 (results\\baseline, gdxdump)  -> dairy milk yields COMI per region (the genetics
                                               options benchmark against DK, FI, PT, SE;
                                               envind/breeding.gms l. 101). Only these
                                               records are kept (552 of 252,000).
  fedcof.gms (dat\\feed)                     -> p_nutCont (nutrient contents of feedstuffs;
                                               line_nitr.gms uses the OOIL row)

Usage: python tools/build/build_mitigation_inputs.py <uploads folder>
"""
import csv, importlib.util, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))         # tools/lib/paths.py
OUT = ROOT / "capri_data" / "2017" / "abatement" / "mitigation"


def _mod(name):
    from paths import tool_file as _tool_file      # tools/lib/paths.py: a tool by name, in whichever tools/ folder
    spec = importlib.util.spec_from_file_location(name, _tool_file(name))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def write(name, header, rows):
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    return len(rows)


def main(up: Path):
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {}
    # 1) dairy milk yields from the baseline trends (stream, keep COMI of dairy activities, year Y)
    pat = re.compile(r"^'([^']+)'\.'(DCO[LHW])'\.'COMI'\.'Y'\s+([-+0-9.eE]+)")
    rows = []
    with open(up / "trends_1730.csv", encoding="latin-1") as f:
        for line in f:
            m = pat.match(line)
            if m:
                rows.append([m.group(1), m.group(2), float(m.group(3))])
    rep["trends_milk_yield_1730"] = write("trends_milk_yield_1730", ["region", "activity", "milk_yield_kg"], rows)
    # (tillageCover, ccEfa and the winter-cover shares p_winterCoverShare0 were written here until 29 October 2026: read
    # by no code, the project lead's decision that the extractors write only what is read, KNOWN_ISSUES K102)
    # 4) nutrient contents of feedstuffs (positional table)
    ct = _mod("build_ammonia_cost_tables")
    lines = [l.rstrip("\r\n") for l in open(up / "fedcof.gms", encoding="latin-1")]
    t = ct.parse_table(lines, "p_nutCont")
    rep["p_nutCont"] = write("p_nutCont", ["feed", "nutrient", "value"], [[rk[0], col, v] for rk, col, v in t])
    return rep


if __name__ == "__main__":
    for k, n in main(Path(sys.argv[1])).items():
        print(f"{k:26s} {n:6d} values")
