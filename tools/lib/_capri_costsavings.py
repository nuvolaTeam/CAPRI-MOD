"""CAPRI's cost-saving drop of an animal option between its two calibration runs, per model head adopting.

CAPRI calibrates each option's quadratic cost term on two supply-only runs of its own model at the 2030 baseline
(ghgTechCali = ini: the shares held at IniShare; = max: every breeding, supplement and low-N feed option held at its
MaxShare at once, supply/set_miti_bounds.gms), with the options' unit costs at 1e-10, so v_Miti.m is the option's
marginal value in the model ("costsaving"):

    pmpParsqr = max[floor x |c|, c (relSubs1 - relSubs0) - (costsaving0 - costsaving1)] / (MaxShare - IniShare)

(envind/breeding.gms l. 447-458, low_n_feed.gms l. 265-272, line_nitr.gms the same). The planned slope
c (relSubs1 - relSubs0) is the total curvature of the option's net marginal cost between IniShare and MaxShare; the
model's own drop of the marginal value over that range (costsaving0 - costsaving1) is part of it, so CAPRI takes it
out of the option's own term.

costsaving_i = v_Miti.m / (LEVL x DAYS / 365) per place (breeding, low-N feed) or v_Miti.m / (LEVL x DRMA x DAYS /
1000 x ShrOfDM) per unit of supplement (line_nitr.gms); in each case the option's cost c is in the same unit, so per
CAPRI head both become (M0 - M1) / LEVL and the formula holds per head with c per head. Per model head adopting:
the CAPRI members of the model animal weighted by their heads at the maximum share (MaxShare x LEVL, as the effect
tables aggregate them), divided by capri_level_ratio (model heads per CAPRI level unit):

    dsav = sum_m MaxShare_m (M0_m - M1_m) / (capri_level_ratio x sum_m MaxShare_m LEVL_m)

M0, M1: v_Miti.m of CAPRI's ini and max runs (capri_data/sources/ghgtech/capri_costsavings_2030.csv, from the project
lead's costsavings_ini/max_21730_jul15.gdx); MaxShare_m: the max run's level (+2e-6, as CAPRI's adjustment);
LEVL_m: CAPRI's 2030 levels (abatement/ammonia/capri_mann_days_2030.csv). The member records are the region's row,
else its member state's.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]


def _model_regions():
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mr)
    return mr


def costsaving_drop(members: dict, technology: str) -> dict:
    """{(model region, model animal): dsav, EUR per model head adopting} for CAPRI's option `technology`
    (GENET_EFF, lowNFeed, LINE_Tot, Nitr_Tot as in the source file) over the model animals' CAPRI members
    {model animal: (CAPRI activity, ...)}. Missing where no member has both runs' records or no level ratio."""
    cs = _read_csv(ROOT / "capri_data" / "sources" / "ghgtech" / "capri_costsavings_2030.csv")
    cs = cs[cs.technology == technology]
    p = cs.pivot_table(index=["region", "activity"], columns="run", values=["level", "marginal"])
    rec = {k: (float(r[("level", "max")]), float(r[("marginal", "ini")]), float(r[("marginal", "max")]))
           for k, r in p.iterrows()
           if pd.notna(r.get(("level", "max"))) and pd.notna(r.get(("marginal", "ini"))) and pd.notna(r.get(("marginal", "max")))}
    md = _read_csv(ROOT / "capri_data" / "2017" / "abatement" / "ammonia" / "capri_mann_days_2030.csv")
    lev = {(r.region, r.activity): float(r.value) for r in md[md["item"] == "LEVL"].itertuples()}
    ratio = _read_csv(ROOT / "capri_data" / "2017" / "supply" / "capri_level_ratio.csv", index_col=0)
    mr = _model_regions()
    to_c8 = mr.region_to_capri()
    out = {}
    for reg in mr.model_regions():
        c8, ms = to_c8.get(reg), mr.national_code(reg)
        for an, mem in members.items():
            if reg not in ratio.index or an not in ratio.columns or not (float(ratio.at[reg, an]) > 0):
                continue
            num = den = 0.0
            for x in mem:
                for c in (c8, ms):
                    r = rec.get((c, x)) if c else None
                    if r is None:
                        continue
                    lv = lev.get((c, x))
                    if lv and lv > 0:
                        mx = min(1.0, r[0] + 2e-6)
                        num += mx * (r[1] - r[2])
                        den += mx * lv
                    break
            if den > 0:
                out[(reg, an)] = num / den / float(ratio.at[reg, an])
    return out
