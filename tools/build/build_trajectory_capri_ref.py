"""CAPRI's own 2030 reference as the projection's trajectory (Sprint 9p).

CAPRI simulates every scenario from its calibrated baseline: CAPMOD's reference run for the simulation year (star 3.0:
`res_2_1730greendeal_refpol_endotech_all_ini`, the 2030 Green Deal reference with endogenous technologies at their
calibrated shares). The model projected its 2030 baseline with CAPRI's trend projection (CAPTRD `series`,
captrd_2030.json), which is the INPUT to that calibration, not its result: against the reference the projected data
had cereals 3-4% high, other fruit +21%, pulses +9% (tools/check/compare_baseline_capri.py), before the model solved anything.

This writes the same trajectory structure from the reference itself: per CAPRI region and activity the factor
    LEVL or YILD in the 2030 reference / LEVL or YILD in CAPRI's 2017 results (res_17<MS>.txt)
for the `herds` block (activity levels, crops included, as in captrd_2030.json) and the `yields` block; regions keyed
by the first four characters of CAPRI's code (national entries XX00), as CAPTRD's; EU growth per activity = median of
the regional factors (fallback); factors kept in [0.2, 5]; regional factors only where the 2017 value is >= 1.0 (the
rules of captrd_2030.json). Model activity and region keys are added by tools/build/build_trajectory_model_keys.py.

    python tools/build/build_trajectory_capri_ref.py [--ref CSV] [--dump-dir DIR]
"""
from __future__ import annotations
import argparse, json, re, statistics, subprocess, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "trajectories" / "capri_ref_2030.json"
REF = Path("/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv")
KEEP = ROOT / "capri_data" / "sources" / "capri_baseline" / "capri_ref_levl_yild_2030_2017.csv.xz"
EU27 = {"AT", "BL", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IR", "IT", "LT", "LV",
        "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK", "NO"}
BAND = (0.2, 5.0)


def extract(ref: Path, dump_dir: Path) -> list:
    rows = []
    p30 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'([A-Z0-9]+)'\.'(LEVL|YILD)'\.'2030'\s+([-\d.Ee+]+)")
    txt = subprocess.run(["grep", "-E", r"^'[A-Z]{2}[0-9A-Z]{6}'\.''\.'[A-Z0-9]+'\.'(LEVL|YILD)'\.'2030'", str(ref)],
                         capture_output=True, text=True).stdout
    for line in txt.splitlines():
        m = p30.match(line)
        if m and m.group(1)[:2] in EU27:
            rows.append((m.group(1), m.group(2), m.group(3), "2030", float(m.group(4))))
    p17 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Z0-9]+)'\.'(LEVL|YILD)'\.'Y'\s+([-\d.Ee+]+)")
    for f in sorted(dump_dir.glob("res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = p17.match(line)
            if m and m.group(1)[:2] in EU27:
                rows.append((m.group(1), m.group(2), m.group(3), "2017", float(m.group(4))))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, default=REF)
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    a = ap.parse_args()
    import pandas as pd
    if a.ref.exists() and a.dump_dir.exists():
        rows = extract(a.ref, a.dump_dir)
        # the model's activities, CAPRI's names for them and their parts, the land aggregates
        sys.path.insert(0, str(ROOT))
        from capri_mod.data.definitions import ALL_ACTIVITIES
        # CACR: CAPRI's own calves aggregate, whose YILD the calves' factor takes where it exists (K28: it was missing
        # from this list, so a fresh extract fell back to the components and changed 77 regional factors)
        keep = set(ALL_ACTIVITIES) | {"MAIZ", "TWIN", "SCOW", "HEIF", "HEIR", "SOWS", "HENS", "POUF", "OFAR", "BULF",
                                      "TEXT", "SHGM", "SHGF", "CAMF", "CAFF", "CAMR", "CAFR", "CACR", "ARAC", "FRUN", "GRAS",
                                      "FALL", "DCOL", "DCOH", "BULH", "HEIL", "HEIH", "PIGF"}
        rows = [r_ for r_ in rows if r_[1] in keep]
        KEEP.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows, columns=["capri_region", "activity", "item", "year", "value"]).to_csv(KEEP, index=False)
        print(f"extracted {len(rows)} rows -> {KEEP.relative_to(ROOT)}")
    t = pd.read_csv(KEEP)
    v = {(r.capri_region, r.activity, r.item, str(r.year)): float(r.value) for r in t.itertuples()}
    # CAPRI's calves are several activities; the model has one (CALV): their
    # levels as sums (CAPTRD carries the same totals as SHGT and CACR)
    for comp, parts in (("SHGT", ("SHGM", "SHGF")), ("CACR", ("CAMF", "CAFF", "CAMR", "CAFR"))):
        for reg in {k[0] for k in v}:
            for yr in ("2017", "2030"):
                xs = [v.get((reg, p_, "LEVL", yr)) for p_ in parts]
                if any(x is not None for x in xs):
                    v[(reg, comp, "LEVL", yr)] = sum(x for x in xs if x is not None)
    # Yields of the model's livestock activities that CAPRI's 2030 reference splits (Sprint 9p regression, found against
    # the EU outlook 2020-2030): the reference reports DCOL/DCOH, HEIL/HEIH, BULL/BULH, CAMF/CAFF and SHGM/SHGF per region
    # but not the model's aggregates, so DCOW, HFRS, BULL, CALV and SHGP had no regional yield factor and no EU one -
    # 2030 output per head stayed at 2017 (EU cow milk 139.6 Mt against CAPRI's 154.3). Their factor is the ratio of the
    # components' level-weighted yields, 2030 over 2017, the same components in both years. DCOW always so: CAPRI's own
    # DCOW YILD is not the milk yield (beef per cow) while the model's DCOW yield is milk per cow. The others take
    # CAPRI's aggregate where it exists in both years (national entries), else the components.
    for comp, parts, always in (("DCOW", ("DCOL", "DCOH"), True), ("HEIF", ("HEIL", "HEIH"), False),
                                ("BULF", ("BULL", "BULH"), False), ("CACR", ("CAMF", "CAFF"), False)):
        for reg in {k[0] for k in v}:
            if not always and all((reg, comp, "YILD", yr) in v for yr in ("2017", "2030")):
                continue
            comp_y = {}
            for yr in ("2017", "2030"):
                num = den = 0.0
                for p_ in parts:
                    L_, Y_ = v.get((reg, p_, "LEVL", yr)), v.get((reg, p_, "YILD", yr))
                    if L_ is not None and Y_ is not None and L_ > 0 and Y_ > 0:
                        num += L_ * Y_; den += L_
                comp_y[yr] = num / den if den > 0 else None
            if comp_y["2017"] and comp_y["2030"]:
                v[(reg, comp, "YILD", "2017")] = comp_y["2017"]
                v[(reg, comp, "YILD", "2030")] = comp_y["2030"]
    # sheep and goats: the model's activities are CAPRI's SHGM (milk; YILD = milk per head) and SHGF (fattening; YILD =
    # meat per head) since October 2026 (tools/build/build_shg_split.py); their factors are CAPRI's own, no alias needed
    blocks = {"herds": "LEVL", "yields": "YILD"}
    regional = {b: defaultdict(dict) for b in blocks}
    cells = {b: defaultdict(list) for b in blocks}
    for (reg, act, item, yr), x30 in v.items():
        if yr != "2030":
            continue
        b = next((k for k, i in blocks.items() if i == item), None)
        x17 = v.get((reg, act, item, "2017"))
        if b is None or x17 is None or not (x17 >= 1.0 if item == "LEVL" else x17 > 0) or x30 < 0:
            continue
        f = min(max(x30 / x17, BAND[0]), BAND[1])
        key = reg[:2] + "00" if reg.endswith("000000") else reg[:4]
        regional[b][key][act] = {"2030": round(f, 4)}
        if not reg.endswith("000000"):
            cells[b][act].append(f)
    # land types (the model's land table) from CAPRI's land aggregates: arable crops ARAC, fruit and nurseries FRUN,
    # grassland GRAS, fallow FALL (CAPRI's 2030 reference has 2.1% less UAA than 2017; without it the projection kept
    # 2017 land and the reconciliation put every crop ~2% above CAPRI's 2030 level)
    for key, acts in regional["herds"].items():          # the model's names for the two totals
        for m_, c_ in (("CALV", "CACR"),):
            if c_ in acts:
                acts[m_] = dict(acts[c_])
    for m_, c_ in (("CALV", "CACR"),):
        cells["herds"][m_] = list(cells["herds"].get(c_, []))
    land_map = {"ARABLE": "ARAC", "PERMANENT": "FRUN", "GRASSLAND": "GRAS", "FALLOW": "FALL"}
    regional["land"] = defaultdict(dict)
    cells["land"] = defaultdict(list)
    for key, acts in list(regional["herds"].items()):
        for col, ca in land_map.items():
            if ca in acts:
                regional["land"][key][col] = dict(acts[ca])
    for col, ca in land_map.items():
        cells["land"][col] = list(cells["herds"].get(ca, []))
    growth = {b: {act: {"2030": round(statistics.median(fs), 4)} for act, fs in c.items() if len(fs) >= 3}
              for b, c in cells.items()}
    out = {"name": "capri_ref_2030", "source": "CAPRI star 3.0 2030 Green Deal reference with endogenous technologies "
           "(res_2_1730greendeal_refpol_endotech_all_ini, LEVL and YILD) over CAPRI's 2017 results (res_17<MS>)",
           "vintage": "from user CAPRI installation", "base_year": 2017, "target_years": [2030], "growth": growth,
           "regional": {b: dict(r) for b, r in regional.items()},
           "_provenance": {"extracted_from": str(KEEP.relative_to(ROOT)),
                           "datatype_read": "CAPMOD reference results 2030 against CAPRI 2017 results",
                           "aggregation": "per-activity median of per-region ratios (EU fallback)",
                           "factor_band": list(BAND), "min_cells_per_activity": 3,
                           "regional_detail": "per-region factors where the 2017 level is >= 1.0 (yields > 0)"}}
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {OUT.relative_to(ROOT)}: {sum(len(r) for r in regional['herds'].values())} level and "
          f"{sum(len(r) for r in regional['yields'].values())} yield factors")
    subprocess.run([sys.executable, str(ROOT / "tools" / "build" / "build_trajectory_model_keys.py"), str(OUT)], check=True)


if __name__ == "__main__":
    main()
