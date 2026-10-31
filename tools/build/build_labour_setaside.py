"""CAPRI's labour accounts and its two set-aside activities, per model region (22 October 2026, the project lead's
request).

1. Labour (capri_data/2017/supply/labour_coef.csv). CAPRI reports labour per activity unit (LABT total, LABF family,
   LABP paid; hours per ha or per head - per 1000 animals for poultry - of CAPRI's activity level) and the region's
   total GROF LABT = sum over its production activities of LABT x LEVL / 1000 (million hours; checked on DE11, FR52,
   IT12 at 2030: equal to CAPRI's GROF LABT). Per model activity and region: the CAPRI members' labour over their
   levels (hours per CAPRI unit), for animals divided by capri_level_ratio (model heads per CAPRI unit), so that
   model level x coefficient / 1000 is CAPRI's million hours. Two vintages: 2017 (res_17 dumps, item 'Y') and
   2030 (CAPRI's 2030 reference the model's trajectory is built from). Members: tools/build/build_capri_base.CROP_MAP for
   crops (GRAS = GRAE + GRAI, SETA = VSET + FALL as CAPRI's activities), the cattle and other animals as
   tools/build/build_livestock_output_coef.py. Labour enters CAPRI's results as an indicator, not as a constraint of its
   supply model; here it is an account after the solve. REGISTERED: within an animal the members' mix is the base
   one (the cattle splits' labour differences are not carried).

2. Set-aside (capri_data/2017/supply/set_aside_split.csv). The model's SETA is CAPRI's VSET (voluntary set-aside) and
   FALL (fallow), identical in every equation the model carries except the premium (and labour). Reported split of a
   SETA level X: VSET = s X0 + w (X - X0), FALL = X - VSET, with X0 the model's base level, s CAPRI's VSET share of
   VSET + FALL and w = q_FALL / (q_VSET + q_FALL) the share of a change CAPRI's own PMP terms give VSET when both see
   the same incentive (min 1/2 q_V V^2 + 1/2 q_F F^2 at V + F given; q on the activity's level, its two technologies
   collapsed). Columns: share_vset, w_vset (2017: the recipe's 2017 terms, as CAPREG's file has one technology's
   term; _capri2030 / _recipe2030: the 2030 terms), the premiums PRME (EUR/ha) and labour LABT (h/ha) of each.

Sources: CAPRI 2017 results /home/claude/work/capreg/res_17*.txt; CAPRI's 2030 reference
/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv; PMP terms
capri_data/sources/capreg/pmp_quad_techn.csv and sources/baseline_pmp/intensity_q_*.csv.

    python tools/build/build_labour_setaside.py
"""
from __future__ import annotations

import glob
import importlib.util
import re
import subprocess
from collections import defaultdict
import sys
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
DUMPS = Path("/home/claude/work/capreg")
REF = Path("/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv")
ITEMS = ("LEVL", "LABT", "LABF", "LABP", "PRME")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import _model_codes as _MC  # noqa: E402  the model's activities and their CAPRI activities (codes/model_activities.csv)
CROPS = dict(_MC.CROP_MAP_CAPMOD)
ANIMALS = dict(_MC.ANIMALS)
MEMBERS = {**CROPS, **ANIMALS}
CAPRI_ACTS = sorted({c for v in MEMBERS.values() for c in v})


def read_2017() -> dict:
    out = defaultdict(dict)
    rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Z0-9]+)'\.'(" + "|".join(ITEMS) + r")'\.'Y'\s+([-\d.Ee+]+)")
    for f in glob.glob(str(DUMPS / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = rx.match(line)
            if m and m.group(2) in CAPRI_ACTS:
                out[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    return out


def read_2030() -> dict:
    pat = r"^'[A-Z]{2}[0-9A-Z]{6}'\.''\.'[A-Z0-9]+'\.'(" + "|".join(ITEMS) + r")'\.'2030'"
    txt = subprocess.run(["grep", "-E", pat, str(REF)], capture_output=True, text=True).stdout
    rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'([A-Z0-9]+)'\.'([A-Z]+)'\.'2030'\s+([-\d.Ee+]+)")
    out = defaultdict(dict)
    for line in txt.splitlines():
        m = rx.match(line)
        if m and m.group(2) in CAPRI_ACTS:
            out[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    return out


def per_unit(d: dict, members, item: str):
    """Labour (or premium) per CAPRI unit over the members, weighted by their levels; None without levels."""
    L = sum(float(d.get((c, "LEVL"), 0.0) or 0.0) for c in members)
    if L <= 0:
        return None
    return sum(float(d.get((c, "LEVL"), 0.0) or 0.0) * float(d.get((c, item), 0.0) or 0.0) for c in members) / L


def main() -> None:
    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    regions = mr.model_regions()
    to_c8 = mr.region_to_capri()
    ratio = _read_csv(ROOT / "capri_data" / "2017" / "supply" / "capri_level_ratio.csv", index_col=0)
    data = {"": read_2017(), "_2030": read_2030()}
    # money terms of the 2030 reference in the model's 2017 money (CAPRI's 2030 PRME over its inflation to 2030;
    # tools/lib/_money, KNOWN_ISSUES K108, 31 October 2026)
    import _money
    money = {"": 1.0, "_2030": _money.deflator(2030)}
    rows, srows = [], []
    for reg in regions:
        src = {}
        for vt, d in data.items():
            for c in (to_c8.get(reg), mr.national_code(reg)):
                if c and c in d and any(k[1] == "LABT" for k in d[c]):
                    src[vt] = c
                    break
        if not src:
            continue
        for act, mem in MEMBERS.items():
            rec = {"region": reg, "activity": act}
            ok = False
            for vt, d in data.items():
                c = src.get(vt)
                if c is None:
                    continue
                r_ = 1.0
                if act in ANIMALS:
                    r_ = float(ratio.at[reg, act]) if reg in ratio.index and act in ratio.columns \
                        and pd.notna(ratio.at[reg, act]) and float(ratio.at[reg, act]) > 0 else None
                    if r_ is None:
                        continue
                for it in ("LABT", "LABF", "LABP"):
                    v = per_unit(d[c], mem, it)
                    if v is not None:
                        rec[it.lower() + vt] = v / r_
                        ok = True
                rec["capri_region" + vt] = c
            if ok:
                rows.append(rec)
        # set-aside: CAPRI's VSET and FALL
        rec = {"region": reg}
        for vt, d in data.items():
            c = src.get(vt)
            if c is None:
                continue
            dv, df = d[c].get(("VSET", "LEVL"), 0.0), d[c].get(("FALL", "LEVL"), 0.0)
            if dv + df <= 0:
                continue
            rec["share_vset" + vt] = dv / (dv + df)
            for a, k in (("VSET", "vset"), ("FALL", "fall")):
                rec[f"prem_{k}{vt}"] = d[c].get((a, "PRME"), 0.0) / money[vt]
                rec[f"labt_{k}{vt}"] = d[c].get((a, "LABT"), 0.0)
        if len(rec) > 1:
            srows.append(rec)
    lab = pd.DataFrame(rows)
    lab.to_csv(ROOT / "capri_data" / "2017" / "supply" / "labour_coef.csv", index=False)
    sa = pd.DataFrame(srows).set_index("region")
    # w = q_FALL / (q_VSET + q_FALL) of each PMP source (the model region's terms; else the country's median w)
    # base year: the recipe's 2017 terms (both technologies; CAPREG's file holds one diagonal term per activity, the
    # first technology's, which is not VSET's curvature on its level)
    for sfx, f in (("", ROOT / "capri_data" / "sources" / "baseline_pmp" / "intensity_q_recipe2017.csv"),
                   ("_capri2030", ROOT / "capri_data" / "sources" / "baseline_pmp" / "intensity_q_capri2030.csv"),
                   ("_recipe2030", ROOT / "capri_data" / "sources" / "baseline_pmp" / "intensity_q_recipe2030.csv")):
        q = _read_csv(f).pivot_table(index="model_region", columns="activity", values="value")
        w = (q["FALL"] / (q["VSET"] + q["FALL"])).where((q["VSET"] > 0) & (q["FALL"] > 0))
        col = "w_vset" + sfx
        sa[col] = w.reindex(sa.index)
        ms = pd.Series([mr.national_code(r)[:2] for r in sa.index], index=sa.index)
        med = sa[col].groupby(ms).median()
        fill = ms.map(med).fillna(float(sa[col].median()))
        sa[col] = sa[col].fillna(fill)
    sa.to_csv(ROOT / "capri_data" / "2017" / "supply" / "set_aside_split.csv")
    print(f"labour_coef.csv: {len(lab)} region x activity rows, {lab.region.nunique()} regions; "
          f"set_aside_split.csv: {len(sa)} regions, VSET share median {sa['share_vset'].median():.2f} (2030 "
          f"{sa['share_vset_2030'].median():.2f}), w median {sa['w_vset'].median():.2f}")


if __name__ == "__main__":
    main()
