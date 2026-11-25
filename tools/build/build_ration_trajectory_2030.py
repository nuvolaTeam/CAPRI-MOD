"""CAPRI's 2030 rations and requirements as factors on the model's 2017 rations (the port of CAPRI's 2030 rations and fodder).

The 2030 baseline took each animal's 2017 ration scaled by one factor (its projected requirements), so every feed moved
alike - grass, silage maize and other fodder as much as concentrates. CAPRI's 2030 reference has its own rations: in
Upper Bavaria a dairy cow (DCOL) eats 6% more grass, 12% less silage maize and 29% more other fodder per head than in
2017. With the 2017 mix the projected fodder use did not match the projected fodder output (other fodder 13-28% below
its projected area in some regions, silage maize 2-6%).

Per group of CAPRI and model regions (tools/lib/_model_regions.capri_groups) and model animal (the CAPRI activities of
tools/build/build_feed_ration.CAPRI_TO_MODEL, the bulls' and heifers' elementary ones in both years: ELEMENTARY,
KNOWN_ISSUES K201), per feed and per requirement:

    factor = (sum_a LEVL_a,2030 x item_a,2030 / sum_a LEVL_a,2030) / (same in 2017)

items: the feeds (kg per head), ENNE and CRPR per day x DAYS, DRMN and |DRMX| x DAYS, and (the removal of synthetic data) manure and
enteric methane per head, CH4MAN and CH4ENT (items ghg_CH4MAN, ghg_CH4ENT: the 2030 factors on the 2017 per-head
methane of tools/build/build_ghg_coefs_2017.py). Groups without regional rows take
their member state's factor (national rows). The 2017 side is CAPRI's 2017 results (res_17<MS>.txt). The 2030 side
(--source):

- capri_ref (the default): CAPRI's 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta, tools/lib/paths.
  BASELINE_REF; its calibration run refpol_endotech_all_ini until 9 November 2026), the solved reference. Output:
  capri_data/baselines/capri_greendeal_ref/1730/trajectories/capri_ref_ration_2030.csv and capri_ref_fodder_2030.csv;
- chain: CAPRI's feed chain of 2030 as ported (capri_mod/feed/chain.py, on CAPREG's base year and CAPRI's trends:
  tools/lib/feed_chain_inputs.py), the simulation's start that CAPRI writes to sim_ini, per regional unit and CAPRI
  activity (read_2030_chain). The national rows are the member state's regional units together, in both years. Its
  methane per head and the fodder are not in the chain yet: only the ration file, without the ghg_ items. Output:
  chain_ration_2030.csv beside CAPRI's.

(region, animal, item, factor, level); factors in [0, 5] (feeds) and [0.2, 5] (requirements).

    python tools/build/build_ration_trajectory_2030.py [--source capri_ref|chain] [--ref CSV] [--dump-dir DIR]
"""
from __future__ import annotations
import argparse, collections, importlib.util, re, sys
from pathlib import Path

import pandas as pd

import functools as _ft
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from _grep import grep  # noqa: E402  (grep -E in Python: any system)
from paths import SOURCES, BASELINE_REF  # noqa: E402  (CAPRI's material outside the repository)
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path[:0] = [str(ROOT)] + [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from _model_regions import CTRY as MS_CODE  # noqa: E402  CAPRI member-state codes (capri_member_state_codes.csv)
TRAJ = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "trajectories"
OUT = TRAJ / "capri_ref_ration_2030.csv"
OUT_FODDER = TRAJ / "capri_ref_fodder_2030.csv"
OUT_CHAIN = TRAJ / "chain_ration_2030.csv"
REF = BASELINE_REF
ITEMS = ("LEVL", "DAYS", "ENNE", "CRPR", "DRMN", "DRMX", "CH4MAN", "CH4ENT")
#: the bulls' and heifers' CAPRI activities of the factors (KNOWN_ISSUES K201): CAPRI's elementary activities in both
#: years, as its requirement rows take them (REQSN_ and REQSE_: p_animReq x p_animProdDays of each activity,
#: supply/supply_model.gms l. 521-590). The 2017 ration builder's aggregates BULF and HEIF have no DAYS in CAPRI's
#: 2030 reference, so until 24 November 2026 the bulls had no 2030 factor (their 2030 ration and requirements the
#: 2017 ones x the projected yield factor) and the heifers' 2030 total was HEIR's alone against HEIF + HEIR in 2017
ELEMENTARY = {"BULL": ("BULL", "BULH"), "HFRS": ("HEIL", "HEIH", "HEIR")}


def capri_activities(c2m: dict) -> dict:
    """The CAPRI activity -> model animal map of the factors: the 2017 ration builder's (build_feed_ration
    .CAPRI_TO_MODEL) with the bulls' and heifers' elementary activities (ELEMENTARY) in place of theirs."""
    out = {ca: ma for ca, ma in c2m.items() if ma not in ELEMENTARY}
    for ma, acts in ELEMENTARY.items():
        out.update({ca: ma for ca in acts})
    return out


def _load(name):
    from paths import tool_file as _tool_file      # tools/lib/paths.py: a tool by name, in whichever tools/ folder
    spec = importlib.util.spec_from_file_location(name, _tool_file(name))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def read_2030_capri(ref: Path, C2M: dict, want: set) -> dict:
    """CAPRI's 2030 results of the activities: {(region, CAPRI activity): {item: value}}."""
    out = collections.defaultdict(dict)
    acts_alt = "|".join(C2M)
    txt = grep(rf"^'[A-Z]{{2}}[0-9A-Z]{{6}}'\.''\.'({acts_alt})'\.'[A-Z0-9]+'\.'2030'", str(ref))
    p30 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'([A-Z0-9]+)'\.'([A-Z0-9]+)'\.'2030'\s+(-?[\d.Ee+\-]+|[Ee][Pp][Ss])")
    for line in txt.splitlines():
        m = p30.match(line)
        if m and m.group(3) in want:
            v = 0.0 if m.group(4).lower() == "eps" else float(m.group(4))
            out[(m.group(1), m.group(2))][m.group(3)] = v
    return out


def read_2017(dump_dir: Path, C2M: dict, want: set, fr) -> dict:
    """CAPRI's 2017 results of the activities (res_17<MS>.txt): {(region, CAPRI activity): {item: value}}."""
    out = collections.defaultdict(dict)
    for f in sorted(dump_dir.glob("res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = fr.ROW.match(line.strip())
            if m and m.group(2) in C2M and m.group(3) in want:
                v = 0.0 if m.group(4).lower() == "eps" else float(m.group(4))
                out[(m.group(1), m.group(2))][m.group(3)] = v
    return out


def read_2030_chain(C2M: dict, FEEDS, raw: Path | None = None) -> tuple:
    """The chain's simulation start (capri_mod/feed/chain.py) of every member state with CAPREG's base year, per
    regional unit and CAPRI activity: LEVL and DAYS at "Y", the feeds per head (the start's v_feedInpCoeff) and ENNE,
    CRPR, DRMN, DRMX per day (p_animReq), each over the activity's technologies weighted by their shares p_technFact,
    as CAPRI's DATA(RU, activity, FEED, "Y") sums them (fedtrm_cal_pw.gms's DATA_feeding). Returns ({(region,
    activity): {item: value}}, {member state: its regional units})."""
    from capri_mod.data.definitions import capri_set
    from capri_mod.feed import chain
    import feed_chain_inputs as fci
    out, units = collections.defaultdict(dict), {}
    A = capri_set("A")
    for ms in capri_set("MS"):
        cc = ms[:2]
        if not (fci.CAPREG_BASE / f"{cc}.csv.gz").exists():
            print(f"  {ms}: no CAPREG base year, left out")
            continue
        res = chain.feed_chain(fci.chain_inputs(cc, raw))
        st, fic, days = res.st, res.a.v_feedInpCoeff_L, res.si.DATA_DAYS_Y
        units[ms] = list(res.d.RU)
        for r in res.d.RU:
            for ca in C2M:
                lv = res.D.get(r, ca, "LEVL", "Y")
                if not lv:
                    continue
                sh = {t: st.tf(r, ca, "LEVL", t) for t in A}
                d = {"LEVL": lv, "DAYS": days.get((r, ca), 0.0)}
                for fe in FEEDS:
                    d[fe] = sum(fic.get((r, ca, t, fe), 0.0) * s for t, s in sh.items() if s)
                for q in ("ENNE", "CRPR", "DRMN", "DRMX"):
                    d[q] = sum(st.p_animReq.get((r, ca, t, q), 0.0) * s for t, s in sh.items() if s)
                out[(r, ca)] = d
        print(f"  {ms}: {len(res.d.RU)} units, {sum(1 for k in out if k[0] in set(res.d.RU))} activities")
    return out, units


def totals(data: dict, yr: str, codes, animal: str, C2M: dict, FEEDS) -> dict | None:
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
            for q in ("CH4MAN", "CH4ENT"):                   # methane per head (the removal of synthetic data)
                acc["ghg_" + q] += lv * d.get(q, 0.0)
    return ({k: v / lv_sum for k, v in acc.items()} if lv_sum > 0 else None)


def ration_rows(data: dict, groups: dict, herds, C2M: dict, FEEDS, national) -> list:
    """The factors per group of regions and model animal, then per member state where a model region has no regional
    rows (national(ms): the CAPRI regions of the member state's row)."""
    animals = sorted(set(C2M.values()))
    rows, covered = [], set()
    for g, (codes, regs) in groups.items():
        for an in animals:
            t17, t30 = totals(data, "2017", codes, an, C2M, FEEDS), totals(data, "2030", codes, an, C2M, FEEDS)
            if not t17 or not t30:
                continue
            for k, v17 in t17.items():
                if v17 > 0 and k in t30:
                    f = min(max(t30[k] / v17, 0.0 if not k.startswith("req_") else 0.2), 5.0)
                    for r in regs:
                        rows.append((r, an, k, f, "region"))
                        covered.add((r, an))
    # national factors where a model region has no regional CAPRI rows
    for r in herds.index:
        ms = MS_CODE.get(r[:2], r[:2]) + "000000"
        for an in animals:
            if (r, an) in covered:
                continue
            codes = national(ms)
            t17, t30 = totals(data, "2017", codes, an, C2M, FEEDS), totals(data, "2030", codes, an, C2M, FEEDS)
            if not t17 or not t30:
                continue
            for k, v17 in t17.items():
                if v17 > 0 and k in t30:
                    rows.append((r, an, k, min(max(t30[k] / v17, 0.0 if not k.startswith("req_") else 0.2), 5.0), "member state"))
    return rows


def fodder_rows(ref: Path, dump_dir: Path, groups: dict, herds) -> list:
    """FODDER per ha (the fodder balance's usable fodder, u = fed quantity / area): CAPRI's FEDM over LEVL of the fodder
    crop, 2030 over 2017 (yield, losses and the non-feed use, e.g. silage maize for biogas in Germany: INDM 3.6 of 6.9
    Mt in Upper Bavaria's 2030 reference); per group, else member state. The model's fodder crop -> CAPRI's: GRAE and
    GRAI take the use per ha of CAPRI's whole grassland GRAS (CAPRI's FEDM of grass is not split by activity); (OFOD:
    OFAR alone until 7 November 2026)."""
    fcrop = {"GRAE": "GRAS", "GRAI": "GRAS", "MAIF": "MAIF", "OFAR": "OFAR", "ROOF": "ROOF"}
    fdat = {"2017": {}, "2030": {}}
    pf30 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'(FEDM|LEVL)'\.'(GRAS|MAIF|OFAR|ROOF)'\.'2030'\s+(-?[\d.Ee+\-]+)")
    txt = grep(r"^'[A-Z]{2}[0-9A-Z]{6}'\.''\.'(FEDM|LEVL)'\.'(GRAS|MAIF|OFAR|ROOF)'\.'2030'", str(ref))
    for line in txt.splitlines():
        m = pf30.match(line)
        if m:
            fdat["2030"][(m.group(1), m.group(3), m.group(2))] = float(m.group(4))
    pl30 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'(GRAS|MAIF|OFAR|ROOF)'\.'LEVL'\.'2030'\s+(-?[\d.Ee+\-]+)")
    txt = grep(r"^'[A-Z]{2}[0-9A-Z]{6}'\.''\.'(GRAS|MAIF|OFAR|ROOF)'\.'LEVL'\.'2030'", str(ref))
    for line in txt.splitlines():
        m = pl30.match(line)
        if m:
            fdat["2030"][(m.group(1), m.group(2), "LEVL")] = float(m.group(3))
    p17 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'(FEDM|GRAS|MAIF|OFAR|ROOF)'\.'(GRAS|MAIF|OFAR|ROOF|LEVL)'\.'Y'\s+(-?[\d.Ee+\-]+)")
    for f in sorted(dump_dir.glob("res_17*.txt")):
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
                    frows.append((r, mc, f_, "region")); fcov.add((r, mc))
    for r in herds.index:
        ms = MS_CODE.get(r[:2], r[:2]) + "000000"
        for mc, cc in fcrop.items():
            if (r, mc) not in fcov:
                f_ = u_ratio([ms], cc)
                if f_ is not None:
                    frows.append((r, mc, f_, "member state"))
    return frows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=("capri_ref", "chain"), default="capri_ref")
    ap.add_argument("--ref", type=Path, default=REF)
    ap.add_argument("--dump-dir", type=Path, default=SOURCES / "capreg")
    ap.add_argument("--raw", type=Path, default=None, help="chain: a local copy of the raw dataset's capri/ folder")
    a = ap.parse_args()
    fr = _load("build_feed_ration")
    mr = _load("_model_regions")
    FEEDS, C2M = fr.FEEDS, capri_activities(fr.CAPRI_TO_MODEL)
    want = set(FEEDS) | set(ITEMS)
    data = {"2017": read_2017(a.dump_dir, C2M, want, fr)}
    if a.source == "chain":
        data["2030"], units = read_2030_chain(C2M, FEEDS, a.raw)
        national = lambda ms: units.get(ms, [ms])                    # noqa: E731
        out_path = OUT_CHAIN
    else:
        data["2030"] = read_2030_capri(a.ref, C2M, want)
        national = lambda ms: [ms]                                   # noqa: E731
        out_path = OUT
    herds = _read_csv(ROOT / "capri_data" / "2017" / "supply" / "animal_numbers.csv", index_col=0)
    c2g, groups = mr.capri_groups(list(herds.index))
    rows = ration_rows(data, groups, herds, C2M, FEEDS, national)
    if a.source == "chain":                              # the chain has no methane per head yet (module docstring)
        rows = [row for row in rows if not row[2].startswith("ghg_")]
    if a.source == "capri_ref":
        fo = pd.DataFrame(fodder_rows(a.ref, a.dump_dir, groups, herds), columns=["region", "crop", "factor", "level"])
        fo.to_csv(OUT_FODDER, index=False)
        print(f"wrote {OUT_FODDER.relative_to(ROOT)}: {len(fo)} rows; median {fo.groupby('crop')['factor'].median().round(3).to_dict()}")
    out = pd.DataFrame(rows, columns=["region", "animal", "item", "factor", "level"])
    out.to_csv(out_path, index=False)
    med = out.groupby("item")["factor"].median().to_dict()
    print(f"wrote {out_path.relative_to(ROOT)}: {len(out)} rows, {out[['region', 'animal']].drop_duplicates().shape[0]} "
          f"region x animal; median factors { {k: round(v, 3) for k, v in med.items()} }")


if __name__ == "__main__":
    main()
