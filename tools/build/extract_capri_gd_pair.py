"""CAPRI's Green Deal 2030 step against its reference: the scenario's effect, for comparison with capri-mod's
greendeal2030 run (capri_data/validation/HOW_TO_RUN_A_VALIDATION_SCENARIO.md).

Two CAPRI capmod result files from the project lead's installation (received 10 November 2026):

  res_2_1730greendeal_refdefaulta.gdx      the reference: CAPRI's shipped run (META: 5 November 2025, GAMS 45.7, not
                                           a run of the project lead's), the GDX of the dump the model is calibrated
                                           to (res_2_1730greendeal_refdefaulta.zip, tools/lib/paths.py BASELINE_REF):
                                           the two agree in all 891,502 records of the member states and EU27yr19 in
                                           2030, to the dump's 15 digits (the same run in two formats)
  res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA.gdx
                                           the project lead's run from that reference (META: 10 November 2026, GAMS
                                           53.3): pol_input/greendeal/greendeal_scenarios.gms with landscape elements 8%,
                                           organic 18%, pesticides -20%, mineral fertiliser 13crp, N surplus -30%
                                           (META of the run; the model's scenario folder
                                           capri_data/scenarios/greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00)

Kept, year 2030, as tools/build/extract_capri_vcs_pair.py keeps the coupled-support pair (its selection, _keep):
supply rows (region, activity, item) with item LEVL, PRME (and PROD, YILD at EU and member-state level) for EU27yr19,
the member states and their NUTS 2 regions; market rows (region, item, product) with UVAP, UVAG, MAPR, HCON, IMPT,
EXPT at EU and member-state level. Added for the Green Deal pair (13 November 2026, the results browser's Green Deal
tab): the crop yields (YILD) of the NUTS 2 regions as well, and the N balance items (dataOut '' . item . NITF, 1000 t
N; N_ITEMS) of every kept region, with item NITF; and (18 November 2026, K171) the market prices PMRK and gross
production GROF of the member states and EU27yr19, for the check's market prices (the model's market prices are
CAPRI's PMRK; UVAP is another price).

Output: capri_data/validation/greendeal_2030/capri_gd_effect.csv (region, activity, item, ref, scen, pct_change); and
capri_gd_effect_outside_eu.csv, the same columns, the levels (LEVL) of the regional units outside the EU and Norway
(the UK, the Western Balkans, Turkey) apart

    python tools/build/extract_capri_gd_pair.py [REF.gdx SCEN.gdx] [--lib-dir DIR]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT / "tools" / "build"))
from paths import EXPORTS, SOURCES  # noqa: E402
from extract_capri_vcs_pair import read_gdx, _keep, REG, EU_MS  # noqa: E402  (the coupled-support pair's selection)

REF = EXPORTS / "res_2_1730greendeal_refdefaulta.gdx"
SCEN = EXPORTS / "res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA.gdx"
OUT = ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_gd_effect.csv"
#: the levels (LEVL) of CAPRI's regional units outside the EU and Norway (the UK, the Western Balkans, Turkey), apart:
#: the file above holds the member states' (27 November 2026: for the GUI's regional maps of the comparison,
#: capri_gradio results_data.gd_regional)
OUT_OUT = ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_gd_effect_outside_eu.csv"
#: those units (capri_data/codes/regional_units.csv: neither a member state's, by CAPRI's code, nor Norway's)
OUTSIDE_UNITS = frozenset(u for u in pd.read_csv(ROOT / "capri_data" / "codes" / "regional_units.csv", dtype=str).region
                          if u[:2] not in EU_MS and u[:2] != "NO")
#: CAPRI's N balance items (dataOut '' . item . NITF, 1000 t N), as tools/build/extract_gd2030_nbalance.py reads them,
#: and the total surplus SURTOT
N_ITEMS = ("MINFER", "GASMIN", "RUNMIN", "NH3MIN", "EXPPRD", "IMPORT", "ATMOSD", "CRESID", "BIOFIX", "EXCRET",
           "GASANI", "RUNANI", "MTRADE", "SURSOI", "SURTOT", "LEACHI")


def _keep_gd(r, q, a, i):
    """The coupled-support pair's selection (_keep), plus NUTS 2 yields and the N balance items."""
    key = _keep(r, q, a, i)
    if key is not None:
        return key
    if q == "" and a in ("PMRK", "GROF") and REG.match(r) and (r == "EU27yr19" or (r[:2] in EU_MS and r.endswith("000000"))):
        return (r, i, a)                     # market price and gross production (K171: the check's market prices)
    if q != "" or not REG.match(r) or not (r == "EU27yr19" or r[:2] in EU_MS):
        return None
    if i == "YILD" or (i == "NITF" and a in N_ITEMS):
        return (r, a, i)
    return None


def _keep_outside(r, q, a, i):
    """The activity levels (LEVL) of the regional units outside the EU and Norway."""
    if q == "" and i == "LEVL" and r in OUTSIDE_UNITS:
        return (r, a, i)
    return None


def _pair(ref, scen):
    keys = sorted(set(ref) | set(scen))
    df = pd.DataFrame([(r, act, it, ref.get((r, act, it)), scen.get((r, act, it))) for (r, act, it) in keys],
                      columns=["region", "activity", "item", "ref", "scen"])
    df["pct_change"] = 100.0 * (df["scen"] / df["ref"] - 1.0)
    df.loc[~(df["ref"].abs() > 1e-9), "pct_change"] = float("nan")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref_gdx", type=Path, nargs="?", default=REF)
    ap.add_argument("scen_gdx", type=Path, nargs="?", default=SCEN)
    ap.add_argument("--lib-dir", default=os.environ.get("CAPRI_GDXLIB", str(SOURCES / "gdxlib")))
    a = ap.parse_args()
    ref = read_gdx(a.ref_gdx, a.lib_dir, keep=_keep_gd)
    scen = read_gdx(a.scen_gdx, a.lib_dir, keep=_keep_gd)
    df = _pair(ref, scen)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    out = _pair(read_gdx(a.ref_gdx, a.lib_dir, keep=_keep_outside), read_gdx(a.scen_gdx, a.lib_dir, keep=_keep_outside))
    out.to_csv(OUT_OUT, index=False)
    print(f"wrote {OUT_OUT.relative_to(ROOT)}: {len(out)} rows, {out.region.nunique()} of the {len(OUTSIDE_UNITS)} units "
          f"outside the EU and Norway")
    eu = df[(df.region == "EU27yr19") & (df.item == "LEVL")].set_index("activity")["pct_change"].dropna()
    print(f"wrote {OUT.relative_to(ROOT)}: {len(df)} rows ({len(ref)} reference, {len(scen)} scenario)")
    print("EU27 levels, % change:", eu.reindex(["SWHE", "DWHE", "BARL", "MAIZ", "RAPE", "PULS", "FALL", "GRAE", "GRAI",
                                               "DCOL", "SCOW", "PIGF", "SHGM"]).round(1).dropna().to_dict())


if __name__ == "__main__":
    main()
