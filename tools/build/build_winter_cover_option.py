"""CAPRI's winter cover (catch crops) as an endogenous mitigation option, per model region (envind/cover_crops.gms).

CAPRI makes the catch-crop share a choice of the regional model: v_Miti(CATC, WinterCov, CO2SEQ), the share of UAAR,
tied to the CATC activity by catcMiti_ (v_actLevl(CATC) = v_Miti x UAAR) and limited by winterCover_ (the land not
already under winter cover). Its cost is the CATC activity's input cost (p_linObjeCont, costParLin) plus CAPRI's
calibrated mitigation cost curve (cover_crops.gms l. 550-700):

  MaxShare   = min(1, sum_c p_coverMax(c) x LEVL_c / UAAR), p_coverMax(c) = 1 - p_winterCoverShare0(c) (NUTS2, else the
               member state's, else the EU's)                                                      (l. 336-345)
  IniShare   = the region's initial catch-crop share; here CAPRI's 2030 reference level CATC / UAAR, the share the model's
               base already uses (cover_crops.csv catc_share_2030); MaxShare >= IniShare             (l. 348, 382)
  MaxIncrease= max(1e-4, (MaxShare - IniShare) / MaxShare)
  relSubs1   = 0.8 x MaxIncrease            (costParLin > 0, IniShare > 0: case 1)
             = 1.2, relSubs0 = 0.2          (costParLin > 0, IniShare = 0: case 3)                  (sensFac 1)
  Subs0, Subs1 = relSubs0, relSubs1 x costParLin
  pmpParSqr  = (Subs1 - Subs0) / (MaxShare - IniShare)
  pmpParLin  = Subs0 - costParLin - pmpParSqr x IniShare
so the cost per ha of UAAR, costParLin m + pmpParLin m + 1/2 pmpParSqr m^2, has the marginal cost Subs0 at IniShare and
Subs1 at MaxShare (the subsidies that would make those shares optimal without other benefits). premCapMitTech is off in
CAPRI's Green Deal settings (refpol_endotech_all_sup.gms l. 76), so no RDP premiums enter.

Sources: capri_data/2017/supply/cover_crops.csv (catc_share_2030, catc_cost_eur_ha = CATC TOIN; tools/
build_cover_crops.py), capri_data/2017/supply/winter_cover_share.csv (filled shares by model crop), CAPRI's 2030 crop
levels (capri_data/validation/greendeal_2030/capri_marginal_terms_ini_2030.csv.xz, LEVL, as build_cover_crops.py).

Output: capri_data/2017/abatement/mitigation/winter_cover_option.csv
    region, capri_region, uaar_kha, ini_share, max_share, cost_lin_eur_ha, subs0, subs1, pmp_sqr, pmp_lin, case

    python tools/build/build_winter_cover_option.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "2017" / "abatement" / "mitigation" / "winter_cover_option.csv"


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def main():
    cc = _load(ROOT / "tools" / "build" / "build_cover_crops.py")
    terms = _read_csv(ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_marginal_terms_ini_2030.csv.xz",
                        header=None, names=["region", "act", "item", "value"], dtype=str)
    terms["value"] = pd.to_numeric(terms["value"], errors="coerce")
    lev = terms[terms["item"] == "LEVL"].pivot_table(index="region", columns="act", values="value")
    wcs0 = cc.read_wcs(ROOT / "capri_data" / "sources" / "capri_gams" / "wintercovershare.gms")
    base = _load(ROOT / "tools" / "build" / "build_capri_base.py")
    crop_map = dict(base.CROP_MAP)
    crop_map["GRAS"] = ("GRAE", "GRAI")
    capri_acts = sorted({x for v in crop_map.values() for x in v})
    cover = _read_csv(ROOT / "capri_data" / "2017" / "supply" / "cover_crops.csv")

    def share_filled(c8, act):
        if (c8, act) in wcs0:
            return wcs0[(c8, act)]
        ms = cc.CTRY_CAPRI.get(c8[:2], c8[:2]) + "000000"
        return wcs0.get((ms, act), wcs0.get(("EU027000", act), 0.0))

    rows = []
    for r in cover.itertuples(index=False):
        src = r.capri_region
        if src not in lev.index:
            continue
        uaar = float(lev.at[src, "UAAR"])
        if not uaar > 0:
            continue
        pot = 0.0
        for x in capri_acts:
            if x in lev.columns and pd.notna(lev.at[src, x]) and float(lev.at[src, x]) > 0:
                pot += (1.0 - share_filled(src, x)) * float(lev.at[src, x])
        mx = min(1.0, pot / uaar)
        ini = float(r.catc_share_2030) if pd.notna(r.catc_share_2030) else 0.0
        mx = max(mx, ini)
        k1 = float(r.catc_cost_eur_ha) if pd.notna(r.catc_cost_eur_ha) else float("nan")
        if not (k1 == k1) or k1 <= 0 or mx - ini <= 1e-9:
            # no cost curve (no cost data, or no room above the initial share): the option is not offered
            rows.append(dict(region=r.region, capri_region=src, uaar_kha=uaar, ini_share=ini, max_share=mx,
                             cost_lin_eur_ha=k1, subs0=0.0, subs1=0.0, pmp_sqr=0.0, pmp_lin=0.0, case="none"))
            continue
        incr = max(1e-4, (mx - ini) / mx)
        if ini > 0:
            rs0, rs1, case = 0.0, 0.8 * incr, "1"
        else:
            rs0, rs1, case = 0.2, 1.2, "3"
        s0, s1 = rs0 * k1, rs1 * k1
        sqr = (s1 - s0) / (mx - ini)
        lin = s0 - k1 - sqr * ini
        rows.append(dict(region=r.region, capri_region=src, uaar_kha=uaar, ini_share=ini, max_share=mx,
                         cost_lin_eur_ha=k1, subs0=s0, subs1=s1, pmp_sqr=sqr, pmp_lin=lin, case=case))
    out = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    on = out[out.case != "none"]
    print(f"{OUT.relative_to(ROOT)}: {len(out)} regions ({len(on)} with a cost curve); ini share median "
          f"{on.ini_share.median():.3f}, max share median {on.max_share.median():.3f}, cost median "
          f"{on.cost_lin_eur_ha.median():.0f} EUR/ha, slope median {on.pmp_sqr.median():.0f} EUR/ha")


if __name__ == "__main__":
    main()
