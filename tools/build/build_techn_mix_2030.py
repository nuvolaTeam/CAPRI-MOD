"""The coefficients of CAPRI's crop technologies T1 and T2 that the model's mix columns carry (S1,
docs/design/S1_MIX_COLUMNS.md): per model region and crop with both technologies, the difference T1 - T2 per ha of
each item the technology factors move.

CAPRI (intens/techf.gms l. 64-108, fert/fertned.gms l. 206-207, policy/rd_logic.gms l. 330-334, policy/prmcut.gms
l. 306, supply/supply_model.gms NUTNED_ l. 1095-1137): a technology's coefficient is the crop's x (1 + p_technFact(row,
T)), the premium of a scheme PRME x (1 + p_technFact(scheme, T)), and its nutrient need is the crop's x
SQRT(1 + p_technFact("Yield", T)) x (1 + p_technFact(nutrient, T)), the nutrient factor being the yield factor
(fertned.gms l. 206-207: the sum of the output factors over PACT_TO_Y). At the calibration point the crop is split
50-50 (p_technFact LEVL 0.5).

Columns (one row per model region and crop with a T1/T2 PMP block in pmp_quad_techn_2030.parquet; each is checked to
have its LEVL T1 and T2 in p_technFact):
  yield_diff         Yield factor T1 - T2 (0.4): outputs, residues and the crop's nutrient removal per unit z
  need_diff          (g_T1 - g_T2) / gbar, g_t = SQRT(1 + y_t) x (1 + y_t), gbar the LEVL-weighted mean: the nutrient
                     need per unit z over the crop's need per ha (0.590 at +-0.2)
  rest_cost_diff_eur_ha  sum over SEED, REPM, REPB, ELEC, EGAS, EFUL, ELUB of (factor T1 - T2) x the input's cost per
                     ha (CAPREG 2017 coefficient x its unit value / 1000, as build_plant_protection_cost.py; the
                     model's money of 2017)
  inpo_diff, plap_diff   factor T1 - T2 of other inputs (0.5) and plant protection (0.8), applied in the model to
                     their current cost (which the Green Deal targets change)
  prem_diff_share    sum over the schemes of (PRME of the scheme / DPTOTAL) x (factor T1 - T2): the premium per unit
                     z over the crop's premium (CAPRI's 2030 reference, dataOut PRME by scheme; schemes with a factor:
                     DPRD_AE1..8, DPRD_N2K, DPRD_SeBete, DPRD_SeExte, DPRD_SeVall; a factor counts only where the
                     scheme pays, policy.gms l. 420)
  capri_region

Not carried: irrigation water (factor 0), the fertiliser cost (through the nutrient need), sugar beet's VCOF
(sugar/techf.gms l. 103, the sugar quota regime's variable cost share, without effect since the quotas ended in 2017;
to be confirmed, docs/design/S1_MIX_COLUMNS.md section 6).

Sources: capri_data/sources/intermediate/technology/techn_fact_2030.parquet (tools/build/build_techn_2030.py),
capri_data/sources/intermediate/baseline_pmp/pmp_quad_techn_2030.parquet, CAPREG's 2017 results res_17<MS>.txt (input
coefficients, LEVL, UVAG), CAPRI's 2030 Green Deal baseline res_2_1730greendeal_refdefaulta (PRME by
scheme; tools/lib/paths.BASELINE_REF, its calibration run refpol_endotech_all_ini until 9 November 2026; extracted to
capri_data/sources/raw/capri/results/res_2_1730greendeal_refdefaulta/prme_schemes_2030.parquet).
Output: capri_data/2030/supply/techn_mix_2030.csv

    python tools/build/build_techn_mix_2030.py [--dump-dir DIR] [--ref FILE]
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))  # tools/lib/paths.py
from _grep import grep  # noqa: E402  (grep -E in Python: any system)
from paths import SOURCES, BASELINE_REF  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)
import _model_codes as _MC  # noqa: E402  the model's activities and their CAPRI activities (codes/model_activities.csv)

_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
FACT = ROOT / "capri_data" / "sources" / "intermediate" / "technology" / "techn_fact_2030.parquet"
QUAD = ROOT / "capri_data" / "sources" / "intermediate" / "baseline_pmp" / "pmp_quad_techn_2030.parquet"
REF = BASELINE_REF
PRME = (ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "res_2_1730greendeal_refdefaulta"
        / "prme_schemes_2030.parquet")
OUT = ROOT / "capri_data" / "2030" / "supply" / "techn_mix_2030.csv"
#: the inputs with a technology factor (techf.gms l. 92-96, 104-105), the Green Deal's two apart
REST = ("SEED", "REPM", "REPB", "ELEC", "EGAS", "EFUL", "ELUB")
INPUTS = REST + ("INPO", "PLAP")
SCHEMES = ("DPRD_AE1", "DPRD_AE2", "DPRD_AE3", "DPRD_AE4", "DPRD_AE5", "DPRD_AE6", "DPRD_AE7", "DPRD_AE8",
           "DPRD_N2K", "DPRD_SeBete", "DPRD_SeExte", "DPRD_SeVall")
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Za-z0-9_]+)'\.'(" + "|".join(INPUTS + ("LEVL",)) + r")'\.'Y'\s+"
                 r"(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")
COLS = ["region", "activity", "yield_diff", "need_diff", "rest_cost_diff_eur_ha", "inpo_diff", "plap_diff",
        "prem_diff_share", "capri_region"]


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def prme_schemes(ref: Path) -> dict:
    """{(CAPRI region, activity): {scheme: PRME}} of CAPRI's 2030 reference (dataOut(R, 'PRME', act, scheme, '2030')),
    the factored schemes and DPTOTAL; extracted from the export when present, else read from the extract."""
    if ref.exists():
        pat = rf"^'[A-Z0-9]{{8}}'\.'PRME'\.'[A-Z]+'\.'({'|'.join(SCHEMES + ('DPTOTAL',))})'\.'2030'"
        rx = re.compile(r"^'([A-Z0-9]{8})'\.'PRME'\.'([A-Z]+)'\.'([A-Za-z0-9_]+)'\.'2030'\s+([-\d.Ee+]+)")
        rows = [m.groups() for m in map(rx.match, grep(pat, str(ref)).splitlines()) if m]
        df = pd.DataFrame(rows, columns=["capri_region", "activity", "scheme", "value"]).astype({"value": float})
        PRME.parent.mkdir(parents=True, exist_ok=True)
        write_source(df, PRME, index=False)
        print(f"extracted {len(df)} PRME rows by scheme -> {PRME.relative_to(ROOT)}")
    df = read_source(PRME)
    out = defaultdict(dict)
    for r in df.itertuples(index=False):
        out[(r.capri_region, r.activity)][r.scheme] = float(r.value)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=SOURCES / "capreg")
    ap.add_argument("--ref", type=Path, default=REF)
    a = ap.parse_args()

    fact = read_source(FACT)
    fact = fact[fact.tech.isin(["T1", "T2"])]
    F = defaultdict(dict)                            # (region, act) -> {(row, tech): value}
    for r in fact.itertuples(index=False):
        F[(r.region, r.activity)][(r.row, r.tech)] = float(r.value)
    quad = read_source(QUAD)
    # a block with both technologies (FALL has T1 alone in most regions, T2 in 24: no mix there, the decision of
    # 7 November 2026)
    _t = quad[quad.tech1.isin(["T1", "T2"])].groupby(["region", "activity"]).tech1.agg(set)
    quad_pairs = {k for k, s in _t.items() if s == {"T1", "T2"}}
    # the crops with a T1/T2 PMP block (the regions CAPRI's supply model solves); each has its two levels (the levels
    # exist also for national aggregates and NONF, which have no PMP block)
    lev = {k for k, d in F.items() if d.get(("LEVL", "T1")) and d.get(("LEVL", "T2"))}
    assert quad_pairs <= lev, f"T1/T2 PMP blocks without technology levels: {sorted(quad_pairs - lev)[:5]}"
    both = quad_pairs

    cost = defaultdict(dict)                         # CAPRI region -> {(act, item): value}
    for f in glob.glob(str(a.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = ROW.match(line)
            if m:
                cost[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    prme = prme_schemes(a.ref)

    mr = _load(ROOT / "tools" / "lib" / "_model_regions.py")
    to_c8 = mr.region_to_capri()
    model_of = {c: m for m, cs in dict(_MC.CROP_MAP_CAPMOD).items() for c in cs}
    multi = {m: cs for m, cs in dict(_MC.CROP_MAP_CAPMOD).items() if len(cs) > 1}
    rows, miss_cost = [], 0
    for reg in mr.model_regions():
        c8 = to_c8.get(reg)
        if c8 is None:
            continue
        for (cr, act) in sorted(k for k in both if k[0] == c8):
            mc = model_of.get(act)
            if mc is None or mc in multi:
                # a model crop of several CAPRI activities has one mix column only if they are one activity (none
                # since S2, 7 November 2026)
                assert mc is None, f"{mc} = {multi[mc]}: a mix column per CAPRI activity is not defined"
                continue
            d = F[(cr, act)]
            fd = lambda row: d.get((row, "T1"), 0.0) - d.get((row, "T2"), 0.0)
            l1, l2 = d[("LEVL", "T1")], d[("LEVL", "T2")]
            y1, y2 = d.get(("Yield", "T1"), 0.0), d.get(("Yield", "T2"), 0.0)
            g = lambda y: math.sqrt(1.0 + y) * (1.0 + y)
            gbar = (l1 * g(y1) + l2 * g(y2)) / (l1 + l2)
            cd = cost.get(cr, {})
            rest = 0.0
            for i in REST:
                q, uv = cd.get((act, i)), cd.get(("UVAG", i))
                if q and uv and fd(i):
                    rest += fd(i) * q * uv / 1000.0
            if not cd.get((act, "LEVL")):
                miss_cost += 1
            p = prme.get((cr, act), {})
            tot = p.get("DPTOTAL", 0.0)
            prem = sum(p.get(s, 0.0) / tot * fd(s) for s in SCHEMES if p.get(s, 0.0) > 0) if tot > 0 else 0.0
            rows.append([reg, mc, fd("Yield"), (g(y1) - g(y2)) / gbar, rest, fd("INPO"), fd("PLAP"), prem, cr])
    out = pd.DataFrame(rows, columns=COLS)
    out.to_csv(OUT, index=False)
    print(f"{OUT.name}: {len(out)} region x crop, {out.region.nunique()} regions; {miss_cost} without a CAPREG 2017 "
          f"level (their input costs 0)")
    print(out.groupby("activity")[COLS[2:8]].median().round(3).to_string())


if __name__ == "__main__":
    main()
