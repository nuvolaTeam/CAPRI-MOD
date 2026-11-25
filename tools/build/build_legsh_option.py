"""CAPRI's increased legume share in temporary grassland (LegSh; envind/leg_share.gms) per model region, for the
regional model's legume share column (capri_mod/supply/abatement.py _legsh_spec).

CAPRI's Green Deal settings (pol_input/greendeal/refpol_endotech_all_sup.gms: ghgAbatement on, %ghgTechLegSh% 1 l. 148,
LegSh in the active list l. 213-222, premCapMitTech off) give the option where the member state has it in mitiTech_map
(27 member states in sim_ini_21730): one share v of other arable fodder (OFAR), 0 <= v <= MaxShare (1), IniShare 0
(miti_data_jul15 has none); OFAR's fixation x (1 + othImpact x v) in NUTNED_, e_BIOFIX and the fixation's N2O; its cost
per ha of OFAR. The statements as named functions: capri_mod/supply/equations/leg_share.py.

Per region the table carries:
  - othImpact (the member state's, l. 33-36 and 45-47) and the part of OFAR's N need in NUTNED_ the option removes at
    v = 1 (need_share: D b o k / (D (1 - b) k + a), NUTNED_LegSh_needShare), from CAPRI's simulation data:
    DATA(r, OFAR, NITF, Y) and p_nitrFact(r, OFAR, BioFix) as fertned.gms and fertpar.gms set them
    (capri_crop_n_coefs_2030.csv: data_nitf, biofix_rate; tools/build/build_capri_crop_n_coefs.py),
    v_cropNutNeedMultFact(r, NITF, T) (crop_nut_need_mult_fact_2030.csv: the same for T, T1 and T2 in sim_ini_21730) and
    v_cropNutNeedAddFact(r, NITF) (sim_ini_21730);
  - the cost parameters of the member state (miti_data_jul15: costParLin, pmpParLin = Subs0 - costParLin, pmpParSqr =
    Subs1 - Subs0), inflated to the simulation year as envind/ghgMiti.gms l. 155-158 does (p_infl^(2030 - 2017)), on
    the temporary grassland part of OFAR (x (1 - FLEG), l. 40-42), over the model's deflator(2030) (tools/lib/_money.py),
    so in the model's (2017) money; leg_share.gms's p_fertCostGains (l. 53-73) is not in the table: the model
    calibrates the linear term with its own value of N (DEP-30's rule).
Rows only where the option acts: othImpact > 0 (it is 0 where the member state's grassland rate is at least 0.15: EE,
EL, HU, IT among those with the option; EL, HU and IT have no cost data either) and OFAR has data in the region.

Sources: capri_data/sources/raw/capri/dat/scen/ghgtech/miti_data_jul15_p_ghgMiti.parquet (CAPRI's miti_data_jul15.gdx),
capri_sources/reference/sets/simini_21730/mitiTech_map.csv, capri_sources/gams/fert/fertpar.gms (p_nitrFact's RALL rates,
p_nfixRate_gras; read as build_capri_crop_n_coefs.py reads them), capri_sources/reference/simini/simini_21730 (DATA's
FLEG share at BAS, v_cropNutNeedAddFact, p_infl), the two tables above.

Output: capri_data/2017/abatement/mitigation/legsh_option.csv
    region, ms, fleg_share, nfix_rate_gras, biofix_ofar, othimpact_biofix, data_nitf_ofar, mult_fact_nitf,
    add_fact_nitf, need_share, cost_lin_eur_ha, pmp_lin, pmp_sqr, subs0, subs1, max_share

    python tools/build/build_legsh_option.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools" / "lib")); sys.path.insert(0, str(ROOT / "tools" / "build"))
from paths import SOURCES, REFERENCE  # noqa: E402  (CAPRI's material outside the repository)
from _money import deflator                                             # noqa: E402
from build_capri_crop_n_coefs import capri_tables, simini               # noqa: E402  (fertpar.gms's tables, DATA)
from capri_mod.supply.equations.fertpar import p_nitrFact_BioFix        # noqa: E402
from capri_mod.supply.equations.leg_share import (                     # noqa: E402
    othImpact_BioFix_LegSh_full, LegSh_costPar, othImpact_BioFix_LegSh, NUTNED_LegSh_needShare)

MITI = ROOT / "capri_data" / "sources" / "raw" / "capri" / "dat" / "scen" / "ghgtech" / "miti_data_jul15_p_ghgMiti.parquet"
MAP = REFERENCE / "sets" / "simini_21730" / "mitiTech_map.csv"
SIMINI = REFERENCE / "simini" / "simini_21730"
CROPN = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment" / "capri_crop_n_coefs_2030.csv"
MULT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment" / "crop_nut_need_mult_fact_2030.csv"
UNITS = ROOT / "capri_data" / "codes" / "regional_units.csv"
OUT = ROOT / "capri_data" / "2017" / "abatement" / "mitigation" / "legsh_option.csv"
SIM, BAS = 2030, 2017


def _addfact() -> dict:
    """v_cropNutNeedAddFact(r, NITF) of sim_ini_21730 (its level)."""
    with gzip.open(SIMINI / "v_cropNutNeedAddFact.csv.gz", "rt", newline="") as fh:
        return {r["d0"].upper(): float(r["level"]) for r in csv.DictReader(fh) if r["d1"].upper() == "NITF"}


def main(check: bool = False):
    T = capri_tables(SOURCES / "gams")
    _, fleg = simini(SIMINI / "DATA.csv.gz")
    m = pd.read_csv(MAP)
    ms_on = {str(r).upper() for r, t in zip(m.iloc[:, 0], m.iloc[:, 2]) if str(t).upper() == "LEGSH"}
    miti = pd.read_parquet(MITI)
    miti = miti[miti["technology"].str.upper() == "LEGSH"]
    par = {(str(r).upper(), str(i)): float(v) for r, i, v in zip(miti["region"], miti["info"], miti["value"])}
    p_infl = float(pd.read_csv(SIMINI / "p_infl.csv.gz", float_precision="round_trip")["value"].iloc[0])
    infl = p_infl ** (SIM - BAS) / deflator(SIM)
    cn = pd.read_csv(CROPN, float_precision="round_trip")
    cn = cn[cn["crop"] == "OFAR"].set_index("capri_region")
    kap = pd.read_csv(MULT, float_precision="round_trip").set_index("capri_region")["x"]
    add = _addfact()
    units = pd.read_csv(UNITS).set_index("region")["capri_ms"]
    bf_fleg, bf_grae = T["rall"].get("FLEG", 0.0), T["rall"].get("GRAE", 0.0)
    rows = []
    for reg, ms in units.items():
        ms = str(ms).upper()
        if ms not in ms_on or (ms, "costParLin") not in par or reg not in cn.index:
            continue
        g = T["nfix"].get(ms)
        g_ = float(g) if g else float(bf_grae)                       # fertpar.gms l. 295: the GRAE rate where none
        s_ms, s_r = fleg.get(ms, 0.0), fleg.get(reg, fleg.get(ms, 0.0))
        o = othImpact_BioFix_LegSh(othImpact_BioFix_LegSh_full(g_, s_ms, bf_fleg),
                                   p_nitrFact_BioFix("OFAR", 0.0, g, s_ms, bf_fleg, bf_grae))
        if not o > 0:
            continue
        D, b = float(cn.at[reg, "data_nitf"]), float(cn.at[reg, "biofix_rate"])
        k, a = float(kap.get(reg, float("nan"))), float(add.get(reg, 0.0))
        if not (D > 0 and k == k):
            continue
        cost = {i: LegSh_costPar(par.get((ms, i), 0.0), s_r) * infl for i in ("costParLin", "pmpParLin", "pmpParSqr",
                                                                               "subs0", "subs1")}
        rows.append({"region": reg, "ms": ms, "fleg_share": s_r, "nfix_rate_gras": g_, "biofix_ofar": b,
                     "othimpact_biofix": o, "data_nitf_ofar": D, "mult_fact_nitf": k, "add_fact_nitf": a,
                     "need_share": NUTNED_LegSh_needShare(D, b, o, k, a),
                     "cost_lin_eur_ha": cost["costParLin"], "pmp_lin": cost["pmpParLin"], "pmp_sqr": cost["pmpParSqr"],
                     "subs0": cost["subs0"], "subs1": cost["subs1"], "max_share": par.get((ms, "MaxShare"), 1.0)})
    out = pd.DataFrame(rows)
    print(f"legume share: {len(out)} regions in {out['ms'].nunique()} member states; othImpact median "
          f"{out['othimpact_biofix'].median():.3f}, need share median {out['need_share'].median():.4f}; "
          f"inflation x deflator {infl:.12f}")
    if check:
        old = pd.read_csv(OUT, float_precision="round_trip")
        pd.testing.assert_frame_equal(old, out.astype(old.dtypes.to_dict()), check_exact=False, rtol=1e-12)
        print("unchanged:", OUT.relative_to(ROOT))
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print("wrote", OUT.relative_to(ROOT), len(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    main(ap.parse_args().check)
