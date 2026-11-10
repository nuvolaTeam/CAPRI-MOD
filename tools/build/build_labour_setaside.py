"""CAPRI's labour accounts and its two set-aside activities, per model region (22 October 2026, the project lead's
request).

1. Labour (capri_data/2017/supply/labour_coef.csv). CAPRI reports labour per activity unit (LABT total, LABF family,
   LABP paid; hours per ha or per head - per 1000 animals for poultry - of CAPRI's activity level) and the region's
   total GROF LABT = sum over its production activities of LABT x LEVL / 1000 (million hours; checked on DE11, FR52,
   IT12 at 2030: equal to CAPRI's GROF LABT). Per model activity and region: the CAPRI members' labour over their
   levels (hours per CAPRI unit), for animals divided by capri_level_ratio (model heads per CAPRI unit), so that
   model level x coefficient / 1000 is CAPRI's million hours. Two vintages: 2017 (res_17 dumps, item 'Y') and
   2030 (CAPRI's 2030 reference the model's trajectory is built from). Members: tools/build/build_capri_base.CROP_MAP for
   crops (GRAS = GRAE + GRAI as CAPRI's activities; VSET and FALL their own since S2), the cattle and other animals as
   tools/build/build_livestock_output_coef.py. Labour enters CAPRI's results as an indicator, not as a constraint of its
   supply model; here it is an account after the solve. REGISTERED: within an animal the members' mix is the base
   one (the cattle splits' labour differences are not carried).

2. Set-aside (capri_data/2017/supply/set_aside_split.csv): the premiums PRME (EUR/ha) of CAPRI's VSET (voluntary
   set-aside) and FALL (fallow), the model's own activities since S2 (7 November 2026), for the report of set-aside
   premiums (model._set_aside_table). Until then the model's SETA was VSET + FALL, and the file held the reported split
   of a SETA level (CAPRI's VSET share and the share of a change CAPRI's PMP terms give VSET) and their labour, now
   in labour_coef.csv under VSET and FALL.

Sources: CAPRI 2017 results capri_sources/capreg/res_17*.txt; CAPRI's 2030 Green Deal baseline
capri_sources/exports/res_2_1730greendeal_refdefaulta.zip (tools/lib/paths.BASELINE_REF; its calibration run
refpol_endotech_all_ini until 9 November 2026); PMP terms
(the PMP terms, capri_data/sources/intermediate/baseline_pmp/intensity_q_*.csv, were read for the split until S2).

    python tools/build/build_labour_setaside.py
"""
from __future__ import annotations

import glob
import importlib.util
import re
from collections import defaultdict
import sys
from pathlib import Path

import pandas as pd

import functools as _ft
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from _grep import grep  # noqa: E402  (grep -E in Python: any system)
from paths import SOURCES, BASELINE_REF  # noqa: E402  (CAPRI's material outside the repository)
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
DUMPS = SOURCES / "capreg"
REF = BASELINE_REF
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
    txt = grep(pat, str(REF))
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
        # the set-aside's source: the labour's where there is one; else (no labour items in CAPREG's results: Turkey, the
        # Western Balkans, as Norway's) the first of the same rows with set-aside levels (4 November 2026: before, those
        # units had no set-aside split although CAPRI has their VSET and FALL)
        src_sa = dict(src)
        for vt, d in data.items():
            if vt not in src_sa:
                for c in (to_c8.get(reg), mr.national_code(reg)):
                    if c and c in d and (d[c].get(("VSET", "LEVL"), 0.0) + d[c].get(("FALL", "LEVL"), 0.0)) > 0:
                        src_sa[vt] = c
                        break
        if not src and not src_sa:
            continue
        for act, mem in (MEMBERS.items() if src else ()):
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
            c = src_sa.get(vt)
            if c is None:
                continue
            dv, df = d[c].get(("VSET", "LEVL"), 0.0), d[c].get(("FALL", "LEVL"), 0.0)
            if dv + df <= 0:
                continue
            for a, k in (("VSET", "vset"), ("FALL", "fall")):
                rec[f"prem_{k}{vt}"] = d[c].get((a, "PRME"), 0.0) / money[vt]
        if len(rec) > 1:
            srows.append(rec)
    lab = pd.DataFrame(rows)
    lab.to_csv(ROOT / "capri_data" / "2017" / "supply" / "labour_coef.csv", index=False)
    sa = pd.DataFrame(srows).set_index("region")
    sa.to_csv(ROOT / "capri_data" / "2017" / "supply" / "set_aside_split.csv")
    print(f"labour_coef.csv: {len(lab)} region x activity rows, {lab.region.nunique()} regions; "
          f"set_aside_split.csv: {len(sa)} regions, VSET premium median {sa['prem_vset'].median():.0f} EUR/ha")


if __name__ == "__main__":
    main()
