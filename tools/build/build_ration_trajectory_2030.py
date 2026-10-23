"""CAPRI's 2030 rations and requirements as factors on the model's 2017 rations (Sprint 9q).

The 2030 baseline took each animal's 2017 ration scaled by one factor (its projected requirements), so every feed moved
alike - grass, silage maize and other fodder as much as concentrates. CAPRI's 2030 reference has its own rations: in
Upper Bavaria a dairy cow (DCOL) eats 6% more grass, 12% less silage maize and 29% more other fodder per head than in
2017. With the 2017 mix the projected fodder use did not match the projected fodder output (other fodder 13-28% below
its projected area in some regions, silage maize 2-6%).

Per group of CAPRI and model regions (tools/lib/_model_regions.capri_groups) and model animal (the CAPRI activities of
tools/build/build_feed_ration.CAPRI_TO_MODEL), per feed and per requirement:

    factor = (sum_a LEVL_a,2030 x item_a,2030 / sum_a LEVL_a,2030) / (same in 2017)

items: the feeds (kg per head), ENNE and CRPR per day x DAYS, DRMN and |DRMX| x DAYS, and (Sprint 9s) manure and
enteric methane per head, CH4MAN and CH4ENT (items ghg_CH4MAN, ghg_CH4ENT: the 2030 factors on the 2017 per-head
methane of tools/build/build_ghg_coefs_2017.py). Groups without regional rows take
their member state's factor (national rows). Inputs: CAPRI's 2030 reference (res_2_1730greendeal_refpol_endotech_all_ini)
and CAPRI's 2017 results (res_17<MS>.txt). Output: capri_data/trajectories/capri_ref_ration_2030.csv
(region, animal, item, factor); factors in [0, 5] (feeds) and [0.2, 5] (requirements).

    python tools/build/build_ration_trajectory_2030.py [--ref CSV] [--dump-dir DIR]
"""
from __future__ import annotations
import argparse, collections, importlib.util, re, subprocess, sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]
from _model_regions import CTRY as MS_CODE  # noqa: E402  CAPRI member-state codes (capri_member_state_codes.csv)
OUT = ROOT / "capri_data" / "trajectories" / "capri_ref_ration_2030.csv"
OUT_FODDER = ROOT / "capri_data" / "trajectories" / "capri_ref_fodder_2030.csv"
REF = Path("/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv")
ITEMS = ("LEVL", "DAYS", "ENNE", "CRPR", "DRMN", "DRMX", "CH4MAN", "CH4ENT")


def _load(name):
    from paths import tool_file as _tool_file      # tools/lib/paths.py: a tool by name, in whichever tools/ folder
    spec = importlib.util.spec_from_file_location(name, _tool_file(name))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, default=REF)
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    a = ap.parse_args()
    fr = _load("build_feed_ration")
    mr = _load("_model_regions")
    FEEDS, C2M = fr.FEEDS, fr.CAPRI_TO_MODEL
    want = set(FEEDS) | set(ITEMS)
    data = {"2017": collections.defaultdict(dict), "2030": collections.defaultdict(dict)}
    acts_alt = "|".join(C2M)
    txt = subprocess.run(["grep", "-E", rf"^'[A-Z]{{2}}[0-9A-Z]{{6}}'\.''\.'({acts_alt})'\.'[A-Z0-9]+'\.'2030'", str(a.ref)],
                         capture_output=True, text=True).stdout
    p30 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'([A-Z0-9]+)'\.'([A-Z0-9]+)'\.'2030'\s+(-?[\d.Ee+\-]+|[Ee][Pp][Ss])")
    for line in txt.splitlines():
        m = p30.match(line)
        if m and m.group(3) in want:
            v = 0.0 if m.group(4).lower() == "eps" else float(m.group(4))
            data["2030"][(m.group(1), m.group(2))][m.group(3)] = v
    for f in sorted(a.dump_dir.glob("res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = fr.ROW.match(line.strip())
            if m and m.group(2) in C2M and m.group(3) in want:
                v = 0.0 if m.group(4).lower() == "eps" else float(m.group(4))
                data["2017"][(m.group(1), m.group(2))][m.group(3)] = v

    def totals(yr, codes, animal):
        """LEVL-weighted per-head items over the CAPRI activities of a model animal in a set of CAPRI regions."""
        lv_sum, acc = 0.0, collections.defaultdict(float)
        for c in codes:
            for ca, ma in C2M.items():
                if ma != animal:
                    continue
                d = data[yr].get((c, ca))
                if not d:
                    continue
                lv, days = d.get("LEVL", 0.0), d.get("DAYS", 0.0)
                if lv <= 0 or days <= 0:
                    continue
                lv_sum += lv
                for fe in FEEDS:
                    acc[fe] += lv * d.get(fe, 0.0)
                for q in ("ENNE", "CRPR"):
                    acc["req_" + q] += lv * d.get(q, 0.0) * days
                acc["req_DMIN"] += lv * d.get("DRMN", 0.0) * days
                acc["req_DMAX"] += lv * abs(d.get("DRMX", 0.0)) * days
                for q in ("CH4MAN", "CH4ENT"):                   # methane per head (Sprint 9s)
                    acc["ghg_" + q] += lv * d.get(q, 0.0)
        return ({k: v / lv_sum for k, v in acc.items()} if lv_sum > 0 else None)

    herds = pd.read_csv(ROOT / "capri_data" / "2017" / "supply" / "animal_numbers.csv", index_col=0)
    c2g, groups = mr.capri_groups(list(herds.index))
    animals = sorted(set(C2M.values()))
    rows = []
    covered = set()
    for g, (codes, regs) in groups.items():
        for an in animals:
            t17, t30 = totals("2017", codes, an), totals("2030", codes, an)
            if not t17 or not t30:
                continue
            for k, v17 in t17.items():
                if v17 > 0 and k in t30:
                    f = min(max(t30[k] / v17, 0.0 if not k.startswith("req_") else 0.2), 5.0)
                    for r in regs:
                        rows.append((r, an, k, round(f, 5), "region"))
                        covered.add((r, an))
    # national factors where a model region has no regional CAPRI rows
    for r in herds.index:
        ms = MS_CODE.get(r[:2], r[:2]) + "000000"
        for an in animals:
            if (r, an) in covered:
                continue
            t17, t30 = totals("2017", [ms], an), totals("2030", [ms], an)
            if not t17 or not t30:
                continue
            for k, v17 in t17.items():
                if v17 > 0 and k in t30:
                    rows.append((r, an, k, round(min(max(t30[k] / v17, 0.0 if not k.startswith("req_") else 0.2), 5.0), 5), "member state"))
    # FODDER per ha (the fodder balance's usable fodder, u = fed quantity / area): CAPRI's FEDM over LEVL of the
    # fodder crop, 2030 over 2017 (yield, losses and the non-feed use, e.g. silage maize for biogas in Germany: INDM
    # 3.6 of 6.9 Mt in Upper Bavaria's 2030 reference); per group, else member state
    fcrop = {"GRAS": "GRAS", "MAIF": "MAIF", "OFOD": "OFAR"}
    fdat = {"2017": {}, "2030": {}}
    pf30 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'(FEDM|LEVL)'\.'(GRAS|MAIF|OFAR)'\.'2030'\s+(-?[\d.Ee+\-]+)")
    txt = subprocess.run(["grep", "-E", r"^'[A-Z]{2}[0-9A-Z]{6}'\.''\.'(FEDM|LEVL)'\.'(GRAS|MAIF|OFAR)'\.'2030'", str(a.ref)],
                         capture_output=True, text=True).stdout
    for line in txt.splitlines():
        m = pf30.match(line)
        if m:
            fdat["2030"][(m.group(1), m.group(3), m.group(2))] = float(m.group(4))
    pl30 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'(GRAS|MAIF|OFAR)'\.'LEVL'\.'2030'\s+(-?[\d.Ee+\-]+)")
    txt = subprocess.run(["grep", "-E", r"^'[A-Z]{2}[0-9A-Z]{6}'\.''\.'(GRAS|MAIF|OFAR)'\.'LEVL'\.'2030'", str(a.ref)],
                         capture_output=True, text=True).stdout
    for line in txt.splitlines():
        m = pl30.match(line)
        if m:
            fdat["2030"][(m.group(1), m.group(2), "LEVL")] = float(m.group(3))
    p17 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'(FEDM|GRAS|MAIF|OFAR)'\.'(GRAS|MAIF|OFAR|LEVL)'\.'Y'\s+(-?[\d.Ee+\-]+)")
    for f in sorted(a.dump_dir.glob("res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = p17.match(line)
            if not m:
                continue
            if m.group(2) == "FEDM" and m.group(3) in fcrop.values():
                fdat["2017"][(m.group(1), m.group(3), "FEDM")] = float(m.group(4))
            elif m.group(3) == "LEVL" and m.group(2) in fcrop.values():
                fdat["2017"][(m.group(1), m.group(2), "LEVL")] = float(m.group(4))

    def u_ratio(codes, cc):
        num = {}
        for yr in ("2017", "2030"):
            fe = sum(fdat[yr].get((c, cc, "FEDM"), 0.0) for c in codes)
            lv = sum(fdat[yr].get((c, cc, "LEVL"), 0.0) for c in codes)
            if fe <= 0 or lv <= 0:
                return None
            num[yr] = fe / lv
        return min(max(num["2030"] / num["2017"], 0.2), 5.0)

    frows, fcov = [], set()
    for g, (codes, regs) in groups.items():
        for mc, cc in fcrop.items():
            f_ = u_ratio(codes, cc)
            if f_ is not None:
                for r in regs:
                    frows.append((r, mc, round(f_, 5), "region")); fcov.add((r, mc))
    for r in herds.index:
        ms = MS_CODE.get(r[:2], r[:2]) + "000000"
        for mc, cc in fcrop.items():
            if (r, mc) not in fcov:
                f_ = u_ratio([ms], cc)
                if f_ is not None:
                    frows.append((r, mc, round(f_, 5), "member state"))
    fo = pd.DataFrame(frows, columns=["region", "crop", "factor", "level"])
    fo.to_csv(OUT_FODDER, index=False)
    print(f"wrote {OUT_FODDER.relative_to(ROOT)}: {len(fo)} rows; median {fo.groupby('crop')['factor'].median().round(3).to_dict()}")
    out = pd.DataFrame(rows, columns=["region", "animal", "item", "factor", "level"])
    out.to_csv(OUT, index=False)
    med = out.groupby("item")["factor"].median().round(3).to_dict()
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} rows, {out[['region', 'animal']].drop_duplicates().shape[0]} "
          f"region x animal; median factors {med}")


if __name__ == "__main__":
    main()
