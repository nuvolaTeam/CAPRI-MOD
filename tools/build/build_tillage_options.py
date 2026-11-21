"""CAPRI's conservation and no tillage options (ConsTill, NoTill; envind/tillage.gms) per model region, for the regional
model's tillage columns (capri_mod/supply/abatement.py _till_spec).

CAPRI's Green Deal settings (pol_input/greendeal/refpol_endotech_all_sup.gms: ghgAbatement on, the active list with
ConsTill and NoTill l. 213-222, NoYieldEffect 1 l. 202, premCapMitTech off l. 80; endoLeach on, capmod/
set_global_variables.gms l. 55) select in tillage.gms:
  - the initial shares from the SAPM 2016 survey (dat/envind/tillageCover.gdx, l. 314-329; no agri-environment data);
  - the cost per ha of tillage area, costParLin, NoTill 64 - 93 - 15, ConsTill 46 - 60 - 7 EUR (l. 401-402), and the
    calibration of l. 605-849 with costsaving0 from CAPRI's ini calibration run (v_Miti.m per ha of tillage area,
    l. 651-660; capri_data/sources/intermediate/ghgtech/capri_costsavings_2030.parquet);
  - no yield effect (NoYieldEffect 1 resets cropyld to 1, l. 504-526; e_t1Mit_ is not in CAPRI's equation list);
  - the effects: NoTill's N2O of mineral N (othImpact N2OSYN, l. 579-582, by tillage region), NoTill's leaching of
    soil and manure N (othImpact NO3SLEA, NO3MLEA x the tillage share of the crop area, l. 563-564), erosion (CO2ERO,
    l. 547-549).
The statements are read from CAPRI's tillage.gms itself (its active branch for these settings, tools/lib/
gams_preproc.py); the tillage regions (map_TillReg) and the tillage crops (CFACTOR_ARAB, the set tillage.gms l. 324
uses) as CAPRI's run instantiated them (sim_ini_21730's sets, capri_sources/reference/sets/simini_21730; the crops and
MCACT through capri_data/codes/capri, tools/build/build_code_lists.py).

The tillage area (sum of the levels of the tillage crops) and the tillage share of the crop area (DATA(ru, UAAR,
TILLSET, Y), l. 325-327) at CAPRI's 2030 levels (capri_data/validation/greendeal_2030/capri_marginal_terms_ref_2030.csv,
LEVL, as build_winter_cover_option.py). Money: CAPRI inflates costParLin to the simulation year (l. 438-441) and its ini
run's marginal values are in 2030 money; both are divided by the model's deflator(2030) (tools/lib/_money.py), so the
table is in the model's (2017) money.

Sources: capri_data/sources/raw/capri/dat/envind/tillageCover.parquet (the project lead's gdxdump of tillageCover.gdx,
p_tillageCover, converted one to one), capri_sources/gams/envind/tillage.gms, capri_sources/reference/sets/
simini_21730/map_TillReg.csv, capri_data/codes/capri/CFACTOR_ARAB.csv and MCACT.csv, the two tables above.

Output: capri_data/2017/abatement/mitigation/tillage_options.csv
    region, technology, till_region, tillage_kha, tillset_share, ini_share, max_share, cost_lin_eur_ha,
    costsaving0_eur_ha, max_increase, relsubs0, relsubs1, subs0, subs1, pmp_sqr, pmp_lin, case, n2osyn, no3slea,
    no3mlea, co2ero

    python tools/build/build_tillage_options.py [--check]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools" / "lib"))
from gams_preproc import preprocess                                     # noqa: E402
from _money import deflator                                             # noqa: E402
from _sources_io import read_source                                     # noqa: E402
from paths import SOURCES, REFERENCE  # noqa: E402  (CAPRI's material outside the repository)
from capri_mod.supply.equations.tillage import (                       # noqa: E402
    p_tillageCover_shares, IniShare_till, MaxIncrease_till, relSubs_till, Subs_till, pmpParsqr_till, pmpParlin_till)

GAMS = SOURCES / "gams"
SETS = REFERENCE / "sets" / "simini_21730"
CODES = ROOT / "capri_data" / "codes" / "capri"
TILLAGE = GAMS / "envind" / "tillage.gms"
COVER = ROOT / "capri_data" / "sources" / "raw" / "capri" / "dat" / "envind" / "tillageCover.parquet"
SAVINGS = ROOT / "capri_data" / "sources" / "intermediate" / "ghgtech" / "capri_costsavings_2030.parquet"
LEVELS = ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_marginal_terms_ref_2030.csv"
OUT = ROOT / "capri_data" / "2017" / "abatement" / "mitigation" / "tillage_options.csv"
TECHS = ("ConsTill", "NoTill")
#: the Green Deal settings that select tillage.gms's branches (refpol_endotech_all_sup.gms, set_global_variables.gms)
GLOBALS = {"premcapmittech": "off", "ghgtechcali": "off", "noyieldeffect": "1", "endoleach": "on",
           "tillinallrmssup": "off", "nondefaultcap": "off", "chk_": "off"}


def active_statements() -> list[tuple[int, str]]:
    """tillage.gms's active statements under the Green Deal settings, (first line, text joined up to ';')."""
    res = preprocess(TILLAGE.read_text(encoding="latin-1"), GLOBALS)
    out, cur, start = [], [], None
    for no, ln in res.lines:
        s = ln.split("*", 1)[0] if ln.startswith("*") else ln
        if not s.strip() or ln.startswith("*") or ln.lstrip().startswith("$"):
            continue
        if start is None:
            start = no
        cur.append(s.strip())
        if s.rstrip().endswith(";"):
            out.append((start, " ".join(cur))); cur, start = [], None
    return out


def _num(expr: str) -> float:
    """The value of a numeric GAMS expression of literals (64 - 93 - 15, (-0.24))."""
    if not re.fullmatch(r"[0-9.\s+\-()eE]+", expr):
        raise ValueError(f"not a literal expression: {expr!r}")
    return float(eval(expr, {"__builtins__": {}}, {}))                  # literals and + - ( ) only


def read_parameters() -> dict:
    """costParLin per option, othImpact N2OSYN per option and tillage region, NO3SLEA / NO3MLEA per option (the factor
    of DATA(ru, UAAR, TILLSET, Y)), CO2ERO per option, from tillage.gms's active statements."""
    P = {"costParLin": {}, "N2OSYN": {}, "NO3SLEA": {}, "NO3MLEA": {}, "CO2ERO": {}}
    pat = re.compile(r'p_ghgMiti\(ru,"cropMiti","(\w+)","(co2seq|othImpact)","(\w+)"\)\s*'
                     r'(?:\$\s*map_tillReg\(ru,"(\w+)"\))?\s*=\s*(.+?);$', re.I)
    for no, s in active_statements():
        m = pat.match(s)
        if not m:
            continue
        tech, kind, item, reg, rhs = m.groups()
        item_u = item.upper()
        if kind.lower() == "co2seq" and item_u == "COSTPARLIN":
            P["costParLin"][tech] = _num(rhs)
        elif kind.lower() == "othimpact" and item_u == "N2OSYN":
            P["N2OSYN"][(tech, reg)] = _num(rhs)
        elif kind.lower() == "othimpact" and item_u in ("NO3SLEA", "NO3MLEA"):
            mm = re.fullmatch(r'(.+?)\s*\*\s*data\(ru,"uaar","tillset","y"\)', rhs, re.I)
            if not mm:
                raise ValueError(f"tillage.gms l. {no}: {s}")
            P[item_u][tech] = _num(mm.group(1))
        elif kind.lower() == "othimpact" and item_u == "CO2ERO":
            P["CO2ERO"][tech] = _num(rhs)
    for k in ("costParLin", "CO2ERO"):
        if not all(t in P[k] for t in TECHS):
            raise ValueError(f"tillage.gms: {k} not found for {TECHS}: {P[k]}")
    return P


def main(check: bool = False):
    P = read_parameters()
    mt = pd.read_csv(SETS / "map_TillReg.csv", dtype=str)
    till_reg = {r: t.capitalize() for r, t in zip(mt["d0"], mt["d1"])}        # NORTH -> North, as tillage.gms writes
    arab = sorted(pd.read_csv(CODES / "CFACTOR_ARAB.csv", dtype=str)["code"].str.upper())
    mcact = set(pd.read_csv(CODES / "MCACT.csv", dtype=str)["code"].str.upper())
    terms = pd.read_csv(LEVELS, header=None, names=["region", "act", "item", "value"], dtype=str)
    terms["value"] = pd.to_numeric(terms["value"], errors="coerce")
    lev = terms[terms["item"] == "LEVL"].pivot_table(index="region", columns="act", values="value", aggfunc="sum")
    area = lev[[c for c in arab if c in lev.columns]].sum(axis=1)
    crops = lev[[c for c in lev.columns if c.upper() in mcact]].sum(axis=1)
    cov = read_source(COVER)
    cov.columns = ["region", "item", "value"]
    sav = read_source(SAVINGS)
    sav = sav[(sav["run"] == "ini") & sav["technology"].isin(TECHS)].set_index(["region", "technology"])["marginal"]
    defl = deflator(2030)
    rows = []
    for reg, g in cov.groupby("region"):
        if reg not in till_reg:
            continue                                     # outside CAPRI's tillage regions (the EU and its neighbours)
        sh = IniShare_till(p_tillageCover_shares(dict(zip(g["item"], g["value"]))))
        a_ = float(area.get(reg, 0.0) or 0.0)
        ts = a_ / float(crops[reg]) if reg in crops.index and float(crops[reg]) else 0.0
        for t in TECHS:
            k1 = P["costParLin"][t]                      # the base year's money: CAPRI's inflation and the deflator cancel
            sav0 = float(sav.get((reg, t), 0.0)) / a_ / defl if a_ > 0 else 0.0
            m0, m1 = sh[t], 1.0
            mi = MaxIncrease_till(m1, m0)
            r0, r1, case = relSubs_till(k1, sav0, m0, mi)
            s0, s1 = Subs_till(r0, k1, sav0), Subs_till(r1, k1, sav0)
            g2 = pmpParsqr_till(s0, s1, m1, m0)
            rows.append({"region": reg, "technology": t, "till_region": till_reg[reg], "tillage_kha": a_,
                         "tillset_share": ts, "ini_share": m0, "max_share": m1, "cost_lin_eur_ha": k1,
                         "costsaving0_eur_ha": sav0, "max_increase": mi, "relsubs0": r0, "relsubs1": r1,
                         "subs0": s0, "subs1": s1, "pmp_sqr": g2, "pmp_lin": pmpParlin_till(s0, k1, sav0, g2, m0),
                         "case": case, "n2osyn": P["N2OSYN"].get((t, till_reg[reg]), 0.0),
                         "no3slea": P["NO3SLEA"].get(t, 0.0) * ts, "no3mlea": P["NO3MLEA"].get(t, 0.0) * ts,
                         "co2ero": P["CO2ERO"][t]})
    out = pd.DataFrame(rows).sort_values(["region", "technology"]).reset_index(drop=True)
    # check: the survey shares, normalised as tillage.gms does, are the levels of CAPRI's ini calibration run
    ini_lv = read_source(SAVINGS)
    ini_lv = ini_lv[(ini_lv["run"] == "ini") & ini_lv["technology"].isin(TECHS)].set_index(["region", "technology"])["level"]
    d = (out.set_index(["region", "technology"])["ini_share"] - ini_lv).dropna().abs()
    print(f"tillage options: {out['region'].nunique()} regions; initial shares against CAPRI's ini run: "
          f"{len(d)} cells, largest difference {d.max():.2e}")
    if d.max() > 1e-5:
        raise SystemExit("initial shares differ from CAPRI's ini calibration run")
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
