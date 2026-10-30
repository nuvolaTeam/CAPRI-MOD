"""CAPRI's organic-to-conventional yield gaps per PESETA macro-region and product group (KNOWN_ISSUES K101), and the
maps of CAPRI's member states and activities to them.

    capri_data/2017/policy/organic_yield_gap.csv          peseta_region, cereals, fruits, grass, maize, milk,
                                                           nonfruit_perm, oilseeds, vegetables, wheat (percent difference)
    capri_data/2017/policy/organic_yield_gap_regions.csv  ms, peseta_region: CAPRI's ms2peseta, every member state of
                                                           its supply models (EU, NO, UK, TUR, the Western Balkans)
    capri_data/2017/policy/organic_yield_gap_groups.csv   activity, group: CAPRI's pact2yieldGap for the model's crops
                                                           (codes/model_activities.csv, CAPRI's supply-model codes: GRAS
                                                           from GRAE and GRAI, CORN from MAIZ, WINE from TWIN); the
                                                           animals' rows (DCOL, DCOH: milk) are left out, as CAPRI
                                                           leaves animal products out of organicCrops (its comment)

From CAPRI's dat/pesticides/yield_effects_ppp.xlsx, sheet yld_gap ("yield gaps organic to conventional: FADN estimates
by JRC used in SUPREMA project"): the macro-region codes in column C, the product groups in the header row, empty
cells where the workbook has none. Until 29 October 2026 the file had no builder and held the values rounded to 3
decimals; the values are now the workbook's. The two maps from CAPRI's inputs/load_organic_yieldgap.gms (sets
ms2peseta and pact2yieldGap); until 30 October 2026 they were literals of capri_mod/supply/supply_module.py
(PESETA_REGION by NUTS-0 country, without the UK, Turkey and the Western Balkans; YIELD_GAP_GROUP).

    python tools/build/build_organic_yield_gap.py [--xlsx FILE] [--gms FILE]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
XLSX = Path("/mnt/user-data/uploads/yield_effects_ppp.xlsx")
GMS = Path("/home/claude/work/allgms/gams/inputs/load_organic_yieldgap.gms")
OUT = ROOT / "capri_data" / "2017" / "policy" / "organic_yield_gap.csv"
OUT_REG = OUT.with_name("organic_yield_gap_regions.csv")
OUT_GRP = OUT.with_name("organic_yield_gap_groups.csv")


def set_pairs(text: str, name: str) -> list[tuple[str, str]]:
    """The (a, b) elements of a two-dimensional GAMS set written as a list a.b between slashes; comments (* in the
    first column) left out."""
    import re
    m = re.search(r"(?im)^\s*set\s+" + re.escape(name) + r"\b[^/]*/(.*?)/\s*;", text, re.S)
    if m is None:
        raise SystemExit(f"set {name} not found")
    out = []
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("*") or line.startswith("*"):
            continue
        a, b = line.split()[0].split(".")
        out.append((a, b))
    return out


def maps(gms: Path) -> tuple[list, list]:
    import sys
    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    import _model_codes as MC
    text = gms.read_text(encoding="latin-1")
    reg = set_pairs(text, "ms2peseta")
    grp_of = dict(set_pairs(text, "pact2yieldGap"))
    groups = []
    for act, codes in MC.CROP_MAP_CAPMOD.items():
        g = {grp_of[c] for c in codes if c in grp_of}
        if len(g) > 1:
            raise SystemExit(f"{act}: its CAPRI activities {codes} are in two yield-gap groups {g}")
        if g and any(c not in grp_of for c in codes):
            raise SystemExit(f"{act}: only part of its CAPRI activities {codes} have a yield-gap group")
        if g:
            groups.append((act, g.pop()))
    return reg, groups


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", type=Path, default=XLSX)
    ap.add_argument("--gms", type=Path, default=GMS)
    a = ap.parse_args()
    import openpyxl
    ws = openpyxl.load_workbook(a.xlsx, data_only=True, read_only=True)["yld_gap"]
    rows = [r for r in ws.iter_rows(values_only=True)]
    hi = next(i for i, r in enumerate(rows) if r and "cereals" in r)
    head = rows[hi]
    c0 = head.index("cereals")
    groups = [h for h in head[c0:] if h]
    data = {}
    for r in rows[hi + 1:]:
        code = r[c0 - 1] if len(r) >= c0 else None
        if not code:
            continue
        data[str(code)] = [float(v) if v is not None else float("nan") for v in r[c0:c0 + len(groups)]]
    df = pd.DataFrame.from_dict(data, orient="index", columns=groups)
    df.index.name = "peseta_region"
    df.to_csv(OUT)
    print(f"{OUT.name}: {len(df)} macro-regions x {len(groups)} product groups from {a.xlsx.name}")
    reg, grp = maps(a.gms)
    pd.DataFrame(reg, columns=["ms", "peseta_region"]).to_csv(OUT_REG, index=False)
    pd.DataFrame(grp, columns=["activity", "group"]).to_csv(OUT_GRP, index=False)
    print(f"{OUT_REG.name}: {len(reg)} member states; {OUT_GRP.name}: {len(grp)} crops (from {a.gms.name})")


if __name__ == "__main__":
    main()
