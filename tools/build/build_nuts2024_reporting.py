"""CAPRI's regional units -> current NUTS-2 regions (NUTS 2024), with area weights, for reporting results on current
NUTS (task 237, decided 27 October 2026: the model stays on CAPRI's units; results are mapped, which is not regional
detail of its own).

Mapping, in three steps, each from a published correspondence:
  1. CAPRI unit -> NUTS 2016: tools/lib/_model_regions.capri_groups over the NUTS-2016 level-2 regions (CAPRI's own
     NUTS version correspondence, gams/compile_rdp_data/build_general_set_structure.gms, with the verified fixes and the
     NUTS splits and merges: DED0 = DED2 + DED4 + DED5, IT31 = ITH1 + ITH2, PL12 = PL91 + PL92, HU10 = HU11 + HU12,
     FI18 = FI1B + FI1C, FI1D = FI13 + FI1A, Ireland's 2016 redrawing). Units under a NUTS-2021 code that NUTS 2016 did
     not have (Norway's NO08, NO09, NO0A) are taken at 2021 directly. A member state without regional detail (DK, EE,
     LT, LV, SI, CY, MT, HR) maps to all of its regions.
  2. NUTS 2016 -> NUTS 2021: Eurostat's NUTS 2021 classification, 'Changes detailed NUTS 2016-2021'
     (sources/nuts/nuts2016_2021.csv): codes kept or recoded; HR04 -> HR02, HR05, HR06; Norway's NO01, NO03, NO04,
     NO05 -> NO08, NO09, NO0A.
  3. NUTS 2021 -> NUTS 2024: Eurostat's 'NUTS2021- NUTS2024' (sources/nuts/nuts2021_2024.csv) and its NUTS-2 change
     notes: NL31, NL33 -> NL35, NL36 (boundary shift); PT16, PT18 -> PT19, PT1C, PT1D; PT17 -> PT1A, PT1B.
The units and NUTS-2024 regions linked by these steps form groups (connected sets). A group's results are spread over
its NUTS-2024 regions by their utilised agricultural area (Eurostat ef_lus_main, UAA, ha, farm structure survey 2023,
NUTS 2024; the 2020 census, NUTS 2021, for the member states without NUTS-2 data for 2023, whose NUTS-2 codes are the
same in 2024; sources/eurostat/ef_lus_main_uaa_nuts2024.csv): weight = the region's UAA / the group's UAA.
Norway is not in the EU's NUTS 2024 tables; Eurostat publishes its 2023 farm structure data under the 2021 statistical
regions (NO02, NO06, NO07, NO08, NO09, NO0A), which are taken as its 2024 regions.
CAPRI has no unit for Brussels (BE10), Berlin (DE30), Bremen (DE50), Hamburg (DE60), Ceuta and Melilla (ES63, ES64) and
the French outermost regions (FRY1-5): build_general_set_structure.gms leaves them out; nor for Svalbard (NO0B). They receive no values.

Output: capri_data/shared/capri_units_nuts2024.csv (capri_unit, nuts2024, group, uaa_ha, weight)
    python tools/build/build_nuts2024_reporting.py [--download]
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
NUTS = ROOT / "capri_data" / "sources" / "nuts"
UAA = ROOT / "capri_data" / "sources" / "eurostat" / "ef_lus_main_uaa_nuts2024.csv"
DEST = ROOT / "capri_data" / "shared" / "capri_units_nuts2024.csv"
API = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ef_lus_main?format=JSON&lang=EN"
       "&crops=UAA&unit=HA&statinfo=TOTAL&farmtype=TOTAL&so_eur=TOTAL&uaarea=TOTAL&time=")
#: Eurostat's NUTS-2 change notes 2021 -> 2024 (sheet 'Changes NUTS-2'): the regions whose boundaries changed
CHANGES_2024 = {"NL31": ("NL35", "NL36"), "NL33": ("NL35", "NL36"),
                "PT16": ("PT19", "PT1C", "PT1D"), "PT18": ("PT19", "PT1C", "PT1D"), "PT17": ("PT1A", "PT1B")}


def _fetch(year):
    """{NUTS-2 code: UAA ha} for one survey year from Eurostat's API."""
    with urllib.request.urlopen(API + year, timeout=120) as r:
        d = json.load(r)
    geo = d["dimension"]["geo"]["category"]["index"]
    inv = {i: g for g, i in geo.items()}
    size = d["size"]
    gpos = d["id"].index("geo")
    stride = 1
    for k in size[gpos + 1:]:
        stride *= k
    out = {}
    for k, v in d["value"].items():
        g = inv[(int(k) // stride) % size[gpos]]
        if len(g) == 4 and not g.endswith("ZZ"):
            out[g] = float(v)
    return out


def download():
    """UAA (ha) per NUTS-2 region: the farm structure survey 2023 (NUTS 2024) for the countries Eurostat publishes at
    NUTS 2 for 2023; the agricultural census 2020 (NUTS 2021) for the others (as of October 2026: BG, EL, ES, IT, LT, PL,
    SI), whose NUTS-2 codes did not change from 2021 to 2024 (checked in main). One year per country, so the weights
    within a group (always within one country) come from one survey."""
    y23, y20 = _fetch("2023"), _fetch("2020")
    have23 = {g[:2] for g in y23}
    rows = [(g, v, "2023") for g, v in y23.items()]
    rows += [(g, v, "2020") for g, v in y20.items() if g[:2] not in have23]
    UAA.parent.mkdir(parents=True, exist_ok=True)
    with open(UAA, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["nuts", "uaa_ha", "year", "source"])
        for g, v, y in sorted(rows):
            w.writerow([g, repr(v), y, f"Eurostat ef_lus_main, UAA, ha, {y} (TOTAL farm type, economic size and area "
                                       f"classes)"])
    print(f"wrote {UAA.relative_to(ROOT)}: {len(rows)} NUTS-2 regions; 2020 census for "
          f"{sorted({g[:2] for g in y20} - have23)}")


def level2(codes):
    return {c for c in codes if isinstance(c, str) and len(c) == 4 and not c.endswith("ZZ")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="fetch the UAA weights from Eurostat first")
    a = ap.parse_args()
    if a.download or not UAA.exists():
        download()
    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    units = mr.UNITS
    ctry = {u: c for u, c in zip(units, pd.read_csv(ROOT / "capri_data" / "shared" / "regional_units.csv", dtype=str).country)}

    t13 = pd.read_csv(NUTS / "nuts2013_2016.csv", dtype=str).fillna("")
    n16 = sorted(level2(t13.code_2016) & {c for c in t13.code_2016 if c[:2] in set(ctry.values()) | {"EL"}})
    t21 = pd.read_csv(NUTS / "nuts2016_2021.csv", dtype=str).fillna("")
    t21 = t21[(t21.code_2016.str.len() == 4) | (t21.code_2021.str.len() == 4)]
    n21 = sorted(level2(t21.code_2021))
    t24 = pd.read_csv(NUTS / "nuts2021_2024.csv", dtype=str).fillna("")
    t24 = t24[(t24.code_2021.str.len() == 4) | (t24.code_2024.str.len() == 4)]
    n24 = level2(t24.code_2024)
    in24 = {c[:2] for c in n24}
    n24 = sorted(n24 | {c for c in n21 if c[:2] not in in24 and c[:2] in set(ctry.values())})   # Norway

    # 1. unit -> NUTS 2016 (or NUTS 2021 for codes new in 2021)
    c2g, groups = mr.capri_groups(n16)
    u16 = defaultdict(set)
    for cs, rs in groups.values():
        for c in cs:
            if c in units:
                u16[c] |= set(rs)
    u21_direct = {u: {u[:4]} for u in units if u[:4] in n21 and u[:4] not in n16}
    for u in units:
        if u.endswith("000000") and u not in u16 and u not in u21_direct:          # national units: the country
            u16[u] = {r for r in n16 if r[:2] == ctry[u] or (ctry[u] == "EL" and r[:2] == "EL")}
    # 2. NUTS 2016 -> NUTS 2021 (kept or recoded codes; HR04 split; Norway's 2016 regions to its 2021 ones)
    to21 = defaultdict(set)
    for r in t21.itertuples():
        if len(r.code_2016) == 4 and len(r.code_2021) == 4:
            to21[r.code_2016].add(r.code_2021)
    to21["HR04"] |= {"HR02", "HR05", "HR06"}
    for o in ("NO01", "NO03", "NO04", "NO05"):
        to21[o] |= {"NO08", "NO09", "NO0A"}
    # 3. NUTS 2021 -> NUTS 2024
    to24 = defaultdict(set)
    for r in t24.itertuples():
        if len(r.code_2021) == 4 and len(r.code_2024) == 4:
            to24[r.code_2021].add(r.code_2024)
    for o, ns in CHANGES_2024.items():
        to24[o] |= set(ns)
    for c in n21:
        if c[:2] not in in24:
            to24[c].add(c)
    links = []
    missing = []
    for u in units:
        s21 = set(u21_direct.get(u, set()))
        for r16 in u16.get(u, ()):
            s21 |= to21.get(r16, {r16} if r16 in n21 else set())
        s24 = set()
        for r21 in s21:
            s24 |= to24.get(r21, {r21} if r21 in n24 else set())
        if not s24:
            missing.append(u)
        links += [(u, n) for n in sorted(s24)]
    # groups: connected sets of units and NUTS-2024 regions
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for u, n in links:
        parent[find(("u", u))] = find(("n", n))
    gid = {}
    for u, n in links:
        gid.setdefault(find(("u", u)), len(gid))
    uaa_t = pd.read_csv(UAA, float_precision="round_trip")
    uaa = uaa_t.set_index("nuts")["uaa_ha"]
    old = uaa_t[uaa_t.year == 2020].nuts
    assert not [c for c in old if c in n21 and c not in n24 and c[:2] in set(ctry.values())], \
        "a 2020 census region whose NUTS-2 code changed in 2024: its weight needs a 2024 source"
    rows = []
    by_group = defaultdict(set)
    for u, n in links:
        by_group[gid[find(("u", u))]].add(n)
    for u, n in links:
        g = gid[find(("u", u))]
        v = float(uaa.get(n, float("nan")))
        if len(by_group[g]) == 1:                  # one NUTS-2024 region: weight 1 (its UAA may be unpublished: Eurostat
            w = 1.0                                # has no 2023 value for SK01, SK03, DEE0)
        else:
            miss = [x for x in by_group[g] if x not in uaa.index]
            assert not miss, f"group of {u}: no UAA for {miss}"
            w = v / float(sum(uaa[x] for x in by_group[g]))
        rows.append({"capri_unit": u, "nuts2024": n, "group": g, "uaa_ha": v, "weight": w})
    out = pd.DataFrame(rows)
    out.to_csv(DEST, index=False)
    eu_n24 = {n for n in n24 if n[:2] in set(ctry.values())}
    uncovered = sorted(eu_n24 - set(out.nuts2024))
    ng = out.groupby("group").agg(u=("capri_unit", "nunique"), n=("nuts2024", "nunique"))
    print(f"wrote {DEST.relative_to(ROOT)}: {out.capri_unit.nunique()} units -> {out.nuts2024.nunique()} NUTS-2024 "
          f"regions in {len(ng)} groups ({int(((ng.u == 1) & (ng.n == 1)).sum())} one-to-one); units without a NUTS "
          f"region: {missing}; NUTS-2024 regions of the EU27 and Norway without a unit: {uncovered}")


if __name__ == "__main__":
    main()
