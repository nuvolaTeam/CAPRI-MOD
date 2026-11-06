"""CAPRI's own 2030 reference as the projection's trajectory (Sprint 9p): the scenario folder
capri_data/scenarios/capri_ref_2030 (settings.toml, growth.csv, regional.csv; capri_mod/projection/scenario_io.py;
capri_data/trajectories/capri_ref_2030.json until 31 October 2026).

CAPRI simulates every scenario from its calibrated baseline: CAPMOD's reference run for the simulation year (star 3.0:
`res_2_1730greendeal_refpol_endotech_all_ini`, the 2030 Green Deal reference with endogenous technologies at their
calibrated shares). The model projected its 2030 baseline with CAPRI's trend projection (CAPTRD `series`,
capri_data/scenarios/captrd_2030), which is the INPUT to that calibration, not its result: against the reference the projected data
had cereals 3-4% high, other fruit +21%, pulses +9% (tools/check/compare_baseline_capri.py), before the model solved anything.

This writes the same trajectory structure from the reference itself: per CAPRI region and activity the factor
    LEVL or YILD in the 2030 reference / LEVL or YILD in CAPRI's 2017 results (res_17<MS>.txt)
for the `herds` block (activity levels, crops included, as in captrd_2030) and the `yields` block; regions keyed
by the first four characters of CAPRI's code (national entries XX00), as CAPTRD's; EU growth per activity = median of
the regional factors (fallback); factors as they are, regional ones where the 2017 value is > 0; a 2030 level the
reference does not list is 0 (since 4 November 2026; until then the rules of captrd_2030: every factor in [0.2, 5],
regional level factors only where the 2017 level is >= 1.0; KNOWN_ISSUES K116). Model activity and region keys are
added by tools/build/build_trajectory_model_keys.py.

    python tools/build/build_trajectory_capri_ref.py [--ref CSV] [--dump-dir DIR]
"""
from __future__ import annotations
import argparse, re, statistics, subprocess, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from _grep import grep  # noqa: E402  (grep -E in Python: any system)
from paths import EXPORTS, SOURCES  # noqa: E402  (CAPRI's material outside the repository)


def _read_csv(*a, **k):
    """pandas.read_csv with floats parsed to the last digit (KNOWN_ISSUES K82)."""
    import pandas as pd
    k.setdefault("float_precision", "round_trip")
    return pd.read_csv(*a, **k)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "scenarios" / "capri_ref_2030"
REF = EXPORTS / "res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv"
KEEP = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "res_2_1730greendeal_refpol_endotech_all_inidefaulta" / "capri_ref_levl_yild_2030_2017.csv.xz"
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from _model_regions import FALLBACK_UNITS, UNITS  # noqa: E402  (capri_data/shared/regional_units.csv)
#: the first two letters of the model's regional units (CAPRI's codes: BL, IR, EL, NO ...): the countries whose 2030
#: reference rows are kept. A set named EU27 until 30 October 2026, which held Norway (HARDCODED_TABLES.md)
SUPPLY_PREFIXES = frozenset(u[:2] for u in UNITS)


def extract(ref: Path, dump_dir: Path) -> list:
    rows = []
    p30 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'([A-Z0-9]+)'\.'(LEVL|YILD)'\.'2030'\s+([-\d.Ee+]+)")
    txt = grep(r"^'[A-Z]{2}[0-9A-Z]{6}'\.''\.'[A-Z0-9]+'\.'(LEVL|YILD)'\.'2030'", str(ref))
    for line in txt.splitlines():
        m = p30.match(line)
        if m and m.group(1)[:2] in SUPPLY_PREFIXES:
            rows.append((m.group(1), m.group(2), m.group(3), "2030", float(m.group(4))))
    p17 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Z0-9]+)'\.'(LEVL|YILD)'\.'Y'\s+([-\d.Ee+]+)")
    for f in sorted(dump_dir.glob("res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = p17.match(line)
            if m and m.group(1)[:2] in SUPPLY_PREFIXES:
                rows.append((m.group(1), m.group(2), m.group(3), "2017", float(m.group(4))))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, default=REF)
    ap.add_argument("--dump-dir", type=Path, default=SOURCES / "capreg")
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
                                      "FALL", "VSET", "DCOL", "DCOH", "BULH", "HEIL", "HEIH", "PIGF", "ROOF"}
        rows = [r_ for r_ in rows if r_[1] in keep]
        KEEP.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows, columns=["capri_region", "activity", "item", "year", "value"]).to_csv(KEEP, index=False)
        print(f"extracted {len(rows)} rows -> {KEEP.relative_to(ROOT)}")
    t = _read_csv(KEEP)
    v = {(r.capri_region, r.activity, r.item, str(r.year)): float(r.value) for r in t.itertuples()}
    # CAPRI's calves are several activities; the model has one (CALV): their
    # levels as sums (CAPTRD carries the same totals as SHGT and CACR). The model's set-aside SETA is CAPRI's fallow FALL
    # plus its voluntary set-aside VSET (CAPRI_TO_MODEL_ACTIVITY; the set-aside split, KNOWN_ISSUES K111), while CAPRI's
    # own SETA row is VSET alone (res_17IT: IT400000 SETA = VSET = 10.70, FALL 7.22): until 4 November 2026 the model's
    # SETA took that row's growth, or the EU median where a region has no VSET (KNOWN_ISSUES K115)
    # The model's other fodder OFOD is CAPRI's OFAR plus its fodder roots ROOF (CAPRI_TO_MODEL_ACTIVITY): until 4
    # November 2026 it took OFAR's growth alone (53 regions off CAPRI's 2030 level by more than 1%)
    for comp, parts in (("SHGT", ("SHGM", "SHGF")), ("CACR", ("CAMF", "CAFF", "CAMR", "CAFR")),
                        ("SETA", ("FALL", "VSET")), ("OFOD", ("OFAR", "ROOF"))):
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
                                ("BULF", ("BULL", "BULH"), False), ("CACR", ("CAMF", "CAFF"), False),
                                ("OFOD", ("OFAR", "ROOF"), True)):
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
    v = {k: x for k, x in v.items() if k[1] not in ("VSET", "ROOF")}   # parts of SETA and OFOD only
    # CAPRI's zeros: GAMS stores no zero, so an activity level the 2030 reference does not list is 0 where the
    # reference reports the region and the activity elsewhere (UK grain maize MAIZ 5.6 kha in 2017, none in 2030; ES
    # other oilseeds OOIL, PT durum wheat DWHE, DK pulses PULS: 20 cells of 2017 level >= 1). Until 4 November 2026
    # they had no regional factor and took the national or EU one (about 1)
    reg30 = {k[0] for k in v if k[2] == "LEVL" and k[3] == "2030"}
    act30 = {k[1] for k in v if k[2] == "LEVL" and k[3] == "2030"}
    for (reg, act, item, yr), x17 in list(v.items()):
        if item == "LEVL" and yr == "2017" and x17 > 0 and reg in reg30 and act in act30 \
                and (reg, act, "LEVL", "2030") not in v:
            v[(reg, act, "LEVL", "2030")] = 0.0
    blocks = {"herds": "LEVL", "yields": "YILD"}
    regional = {b: defaultdict(dict) for b in blocks}
    cells = {b: defaultdict(list) for b in blocks}
    for (reg, act, item, yr), x30 in v.items():
        if yr != "2030":
            continue
        b = next((k for k, i in blocks.items() if i == item), None)
        x17 = v.get((reg, act, item, "2017"))
        if b is None or x17 is None or not x17 > 0 or x30 < 0:
            continue
        # CAPRI's own 2030 over 2017, as it is (the model's 2017 levels and yields are CAPRI's 2017 results), so the
        # projection reproduces the reference. Until 4 November 2026 the factors were kept in [0.2, 5] and level factors
        # taken only where the 2017 level is >= 1.0, rules of the trend projection captrd_2030 (France's pulses: 328 kha
        # in 2017, 36.9 in 2030, factor 0.112, held at 0.2; Poland's other crops OCRO yield 11.6 in 2017, 206.5 in
        # 2030, held at 5; KNOWN_ISSUES K116)
        f = x30 / x17
        key = reg[:2] + "00" if reg.endswith("000000") else reg[:4]
        regional[b][key][act] = {"2030": f}
        # the EU fallback's medians over the units they were taken over before CAPRI's other 29 were listed
        # (FALLBACK_UNITS, 4 November 2026), levels of at least 1.0 in 2017 (a proxy for regions without CAPRI rows:
        # the small cells left out, as before)
        if not reg.endswith("000000") and reg in FALLBACK_UNITS and (item != "LEVL" or x17 >= 1.0):
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
    growth = {b: {act: {"2030": statistics.median(fs)} for act, fs in c.items() if len(fs) >= 3}
              for b, c in cells.items()}
    out = {"name": "capri_ref_2030", "source": "CAPRI star 3.0 2030 Green Deal reference with endogenous technologies "
           "(res_2_1730greendeal_refpol_endotech_all_ini, LEVL and YILD) over CAPRI's 2017 results (res_17<MS>)",
           "vintage": "from user CAPRI installation", "base_year": 2017, "target_years": [2030], "growth": growth,
           "regional": {b: dict(r) for b, r in regional.items()},
           "_provenance": {"extracted_from": str(KEEP.relative_to(ROOT)),
                           "datatype_read": "CAPMOD reference results 2030 against CAPRI 2017 results",
                           "aggregation": "per-activity median of per-region ratios (EU fallback)",
                           "factor_band": "none", "min_cells_per_activity": 3,
                           "regional_detail": "per-region factors where the 2017 value is > 0; a 2030 level the "
                                              "reference does not list is 0 (GAMS stores no zero)"}}
    sys.path.insert(0, str(ROOT))
    from capri_mod.projection import scenario_io
    scenario_io.write(OUT, out)
    print(f"wrote {OUT.relative_to(ROOT)}: {sum(len(r) for r in regional['herds'].values())} level and "
          f"{sum(len(r) for r in regional['yields'].values())} yield factors")
    subprocess.run([sys.executable, str(ROOT / "tools" / "build" / "build_trajectory_model_keys.py"), str(OUT)], check=True)


if __name__ == "__main__":
    main()
