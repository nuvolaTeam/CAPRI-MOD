"""CAPRI star 3.0's PMP terms of its 2030 baseline calibration, as CSV (KNOWN_ISSUES K61, decision 5a.5).

CAPMOD simulates 2030 with the PMP terms its baseline calibration writes (baseline/fin_cal.gms l. 143:
pmppar_<NTSLVL><BAS><SIM><CC>...gdx, read by capmod/create_sim_ini_gdx.gms l. 491). They were exported from the
project lead's CAPRI installation with tools/gams/export_pmp_2030.gms (plain gdxdump of every
output/results/baseline/pmppar_21730<CC>defaulta.gdx, plus dat/estnlp/results.gdx VB, VD) on 21 October 2026.

Symbols (supply/supply_model.gms QUADRA_ l. 5284, GRPLEVL_ l. 4892, LandMarket_ l. 4831):
  p_pmpQuadTechn(r, act, a, a1)  quadratic terms per activity and technology (T; crops T1 / T2, CAPRI's high- and
                                 low-yield variants, capmod.gms l. 246)
  p_pmpQuadPact(r, grp, grp1)    quadratic terms on the crop groups' levels (CERE, CER2, OILS, OARA, FARA), stored
                                 for p_ordGrp(grp) <= p_ordGrp(grp1)
  p_pmpCnst(r, act, a)           linear terms
  p_pmpQuadLandTypes(r, lt, lt1), p_pmpCnstLandTypes(r, lt)   land supply / land market (Trustee_land)
  VB, VD (estnlp)                CAPRI's econometric estimates (2004) the terms are derived from
                                 (supply/define_pmp_terms.gms); kept for the record and for checks

Writes (CAPRI region codes, CAPRI activity codes; nothing mapped or changed here):
  capri_data/sources/baseline_pmp/pmp_quad_techn_2030.csv      region, activity, tech1, tech2, value
  capri_data/sources/baseline_pmp/pmp_quad_pact_2030.csv       region, group1, group2, value
  capri_data/sources/baseline_pmp/pmp_quad_landtypes_2030.csv  region, landtype1, landtype2, value
  capri_data/sources/baseline_pmp/pmp_feed_inp_coeff_2030.csv region, activity, tech, feed, coef (CNST / SLOP), value
  capri_data/sources/baseline_pmp/estnlp_vb.csv, estnlp_vd.csv region, ..., level (VB.L, VD.L)
The linear terms p_pmpCnst and p_pmpCnstLandTypes were written to pmp_cnst_2030.csv and pmp_cnst_landtypes_2030.csv
until 30 October 2026; nothing read them (the model derives its linear terms from its own calibration, docs/
PMP_CAPRI_2030.md) and they were removed, the project lead's decision (KNOWN_ISSUES K103).

    python tools/build/build_pmp_2030.py [--dir DIR with pmppar_21730*.txt and estnlp_results_*.txt]
"""
from __future__ import annotations
import argparse, csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "sources" / "baseline_pmp"
SYMBOLS = {"p_pmpQuadTechn": ("pmp_quad_techn_2030.csv", ["region", "activity", "tech1", "tech2", "value"]),
           "p_pmpQuadPact": ("pmp_quad_pact_2030.csv", ["region", "group1", "group2", "value"]),
           "p_pmpQuadLandTypes": ("pmp_quad_landtypes_2030.csv", ["region", "landtype1", "landtype2", "value"]),
           "p_pmpFeedInpCoeff": ("pmp_feed_inp_coeff_2030.csv", ["region", "activity", "tech", "feed", "coef", "value"])}
_REC = re.compile(r"^((?:'[^']*'\.)*'[^']*')(?:\.(L|M|LO|UP|SCALE))?\s+(\S+?),?\s*$")


def _value(tok: str):
    t = tok.strip().rstrip(",")
    u = t.upper()
    if u == "EPS":
        return 0.0
    try:
        return float(t)
    except ValueError:
        return t                                  # an acronym (exogenousLandSupply)


def records(path: Path, symbol: str, field: str = None):
    """Yield (keys, value) of one symbol of a gdxdump text file; for variables, of one field (L, ...)."""
    inside = False
    for line in open(path, errors="ignore"):
        if not inside:
            s = line.lstrip()
            if re.match(r"^(free\s+|positive\s+|negative\s+)?(Parameter|Variable|Set)\s+" + re.escape(symbol) + r"\b", s):
                inside = not s.rstrip().endswith("/ /;")
            continue
        txt = line.strip()
        last = txt.endswith("/;")                 # gdxdump closes a symbol on its last record's line
        if last:
            txt = txt[:-2].strip()
        m = _REC.match(txt) if txt else None
        if not m:
            if last:
                break
            continue
        if (field is not None and m.group(2) != field) or (field is None and m.group(2) is not None):
            if last:
                break
            continue
        keys = re.findall(r"'([^']*)'", m.group(1))
        yield keys, _value(m.group(3))
        if last:
            break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=Path("/home/claude/work/up/pmp2030"))
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(a.dir.glob("pmppar_21730*.txt"))
    assert files, f"no pmppar_21730*.txt in {a.dir}"
    for sym, (name, header) in SYMBOLS.items():
        n = 0
        with open(OUT / name, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            for f in files:
                for keys, v in records(f, sym):
                    if len(keys) != len(header) - 1:
                        continue
                    w.writerow(keys + [repr(v) if isinstance(v, float) else v])
                    n += 1
        print(f"{name}: {n} records from {len(files)} files")
    for sym, name, header in (("VB", "estnlp_vb.csv", ["region", "group1", "group2", "level"]),
                              ("VD", "estnlp_vd.csv", ["region", "activity", "level"])):
        src = a.dir / f"estnlp_results_{sym}.txt"
        if not src.exists():
            print(f"{src.name}: not found")
            continue
        n = 0
        with open(OUT / name, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            for keys, v in records(src, sym, field="L"):
                if len(keys) == len(header) - 1:
                    w.writerow(keys + [repr(v) if isinstance(v, float) else v])
                    n += 1
        print(f"{name}: {n} records")


if __name__ == "__main__":
    main()
