"""CAPRI's simulation-year input coefficients of 2030 that the Green Deal's input changes and the crops' yield updates
act on, valued as its supply models value them (register DEP-21).

CAPRI's simulation rebuilds the directly yield-dependent input coefficients from the base year's
(capmod/define_inputs.gms, run by capmod.gms l. 772 for every main activity): DATA(Y) = DATA(BAS) x (1 - f + f G) x
TF_I (capri_mod/supply/equations/define_inputs.py), and the Green Deal's plant-protection and other-input changes
enter through TF_I (l. 70-73; pol_input/greendeal/organic_io.gms, conventional_io.gms), on these coefficients. Its
objective values them at the member state's UVAP of the simulation year (capmod/define_objc.gms l. 40-44; UVAP(Y) =
UVAP(BAS) x p_infl^(Y - BAS) for the inputs without price expectations, capmod/inflation_and_trend_interpolation.gms
l. 69, 73). The model took CAPRI's 2017 coefficients at the regions' 2017 UVAG (build_plant_protection_cost.py): the
Green Deal's change on them left out the yield growth's part (1 - f + f G) and the member state's price.

Written per regional unit and model activity, LEVL(Y)-weighted over the model activity's CAPRI activities, before
TF_I (the model applies TF_I with the scenario's changes, policy.py), in CAPRI's 2030 money (the model deflates it):
  crops (EUR per ha)
    plap_eur_ha, inpo_eur_ha   DATA(BAS) x (1 - f + f G) x UVAP(MS, I, Y) / 1000: the coefficient the Green Deal's
                               PLAP and INPO changes scale
    eful_inpo_eur_ha           (EFUL + SERI)(BAS) x (1 - f_INPO + f_INPO G) x UVAP(MS, INPO, Y) / 1000: the organic
                               top-up's base as organic_io.gms l. 111-115 codes it (added to INPO's base coefficient)
    eful_eur_ha                the same quantity at EFUL's and SERI's own UVAP (the fix of FIX-6, the default)
    yd_rest_eur_ha, yd_plap_eur_ha, yd_inpo_eur_ha
                               sum over IY of f x DATA(BAS) x G x UVAP(MS, I, Y) / 1000: the coefficients' derivative in
                               the yield ratio at CAPRI's 2030 reference (before TF_I), 0 for an activity at G's bound
    yield_growth               G of the model crop (base-yield weighted)
  animals
    inpo_yield_factor          sum LEVL(Y) DATA(BAS, INPO) (1 - f + f G) / sum LEVL(Y) DATA(BAS, INPO): the yield
                               growth's part of the animal's INPO coefficient (G its main output's, e.g. milk per cow),
                               applied to the model's INPO cost per head (build_plant_protection_cost.py's share of the
                               cost per head; the per-head basis is DEP-13's: CAPRI's head and the model's differ for
                               poultry and the fattening activities, capri_level_ratio.csv). INPO's UVAP(MS) equals the
                               regions' 2017 UVAG (the yd_inpo columns of the two tables agree within 1e-4)
  levl_capri                   CAPRI's 2030 level of the activity (1000 ha or head), the weight

Check printed: the rebuilt coefficients x TF_I equal CAPRI's 2030 reference coefficients (dataOut PLAP and INPO at
2030, the run the model's 2030 base reproduces) in every EU row with a base level, within the listing's printed
precision (relative 1e-5; 15,449 rows, at most 8.4e-6 on 23 November 2026).

Sources: sim_ini_21730 (capri_sources/reference/simini/simini_21730; tools/build/build_simini_reference.py): DATA at
BAS and Y (the activities' inputs, levels and main-output yields; the member states' UVAP at BAS), p_infl; CAPRI's
p_inputDemandFactor (inputs/yieldIY.gms, capri_data/sources/raw/capri/gams/inputs/yieldIY_p_inputDemandFactor.parquet);
sets.gms (PACT_TO_Y; IOE's members, to check none of the inputs has a price expectation); dataOut of
res_2_1730greendeal_refdefaulta (tools/lib/paths.BASELINE_REF) for the check.

Output: capri_data/baselines/capri_greendeal_ref/1730/supply/input_coefs_2030.csv

    python tools/build/build_input_coefs_2030.py [--src ZIP] [--no-check]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "build")]
from paths import BASELINE_REF, BASE_YEAR, REFERENCE, SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from capri_mod.supply.equations.define_inputs import DATA_IY_Y, TF_I, p_yieldGrowth  # noqa: E402
from _grep import lines  # noqa: E402  (a listing's lines, plain or zipped)
from _sources_io import source_records  # noqa: E402  (capri_data/sources: Parquet)
import _model_codes as _MC  # noqa: E402  (the model's activities and their CAPRI activities)
import _model_regions as _MR  # noqa: E402  (the regional units and their member states)
import gams_sets as G_  # noqa: E402  (CAPRI's sets from its GAMS files)
from build_plant_protection_capri_step_2030 import UVAP_Y, p_inflationFactor, read_p_infl  # noqa: E402

OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply" / "input_coefs_2030.csv"
SIMINI = REFERENCE / "simini" / "simini_21730"
YIELD_IY = ROOT / "capri_data" / "sources" / "raw" / "capri" / "gams" / "inputs" / "yieldIY_p_inputDemandFactor.parquet"
SIM_YEAR = 2030
#: CAPRI's directly yield-dependent inputs of the crops (sets.gms IY without the water and mitigation inputs; as
#: build_plant_protection_cost.py)
IY_CROP = ("CAOF", "SEED", "PLAP", "REPM", "REPB", "ELEC", "EGAS", "EFUL", "ELUB", "IRRO", "INPO", "SERI")
COLS = ["region", "activity", "plap_eur_ha", "inpo_eur_ha", "eful_eur_ha", "eful_inpo_eur_ha", "yd_rest_eur_ha",
        "yd_plap_eur_ha", "yd_inpo_eur_ha", "yield_growth", "inpo_yield_factor", "levl_capri"]


def read_simini(acts: set) -> tuple:
    """sim_ini_21730's DATA: {(region, activity, row, year): value} for the activities (BAS and Y), and
    {(member state, input): UVAP at BAS}."""
    d, uvap = {}, {}
    with gzip.open(SIMINI / "DATA.csv.gz", "rt", newline="", encoding="utf-8") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        assert head[:5] == ["d0", "d1", "d2", "d3", "value"], head
        for d0, d1, d2, d3, v, *_ in rd:
            if d3 not in ("BAS", "Y"):
                continue
            if d1 in acts:
                d[(d0, d1, d2, d3)] = float(v)
            elif d1 == "UVAP" and d3 == "BAS" and d2 in IY_CROP:
                uvap[(d0, d2)] = float(v)
    return d, uvap


def read_reference_2030(src: Path, acts: set) -> dict:
    """CAPRI's 2030 reference coefficients {(region, activity, PLAP | INPO): value} (dataOut at 2030)."""
    rx = re.compile(r"^'([A-Z0-9_]{8})'\.''\.'([A-Za-z0-9_]+)'\.'(PLAP|INPO)'\.'2030'\s+(\S+)")
    out = {}
    for line in lines(src):
        if "'2030'" not in line or not ("'PLAP'" in line or "'INPO'" in line):
            continue
        m = rx.match(line)
        if m and m.group(2) in acts:
            s = m.group(4).strip().rstrip(",")
            out[(m.group(1), m.group(2), m.group(3))] = 0.0 if s.upper() == "EPS" else float(s)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=BASELINE_REF)
    ap.add_argument("--no-check", action="store_true")
    a = ap.parse_args()
    gs = G_.read(SOURCES / "gams" / "sets.gms", SOURCES / "gams", {"BaseYear": BASE_YEAR, "BAS": BASE_YEAR[2:]})
    p2y = defaultdict(list)
    for act, o in gs.get("PACT_TO_Y"):
        p2y[act.upper()].append(o.upper())
    ioe = {x[0].upper() for s in ("FEED", "IYANI") for x in (gs.get(s) or [])}
    assert not ioe & set(IY_CROP), f"inputs with a price expectation (IOE): {sorted(ioe & set(IY_CROP))}"
    fac = {(r["activity"], r["input"]): float(r["value"]) for r in source_records(YIELD_IY)}
    crops, animals = dict(_MC.CROP_MAP_CAPMOD), dict(_MC.ANIMALS_CAPMOD)
    acts = {c for cs in list(crops.values()) + list(animals.values()) for c in cs}
    D, uvap_bas = read_simini(acts)
    infl = p_inflationFactor(read_p_infl(), SIM_YEAR, int(BASE_YEAR))
    TF = TF_I(1.0 - 0.005 * (SIM_YEAR - int(BASE_YEAR)))

    def G_of(r, c, bounded=True):
        ys = [(D.get((r, c, o, "Y"), 0.0), D.get((r, c, o, "BAS"), 0.0)) for o in p2y.get(c, [])]
        return p_yieldGrowth([y for y, _ in ys], [b for _, b in ys], D.get((r, c, "LEVL", "BAS"), 0.0), bounded)

    def f(c, i):
        return fac.get((c, i), 1.0)

    rows, check, missing_uv = [], [], set()
    for r in _MR.model_regions():
        ms = _MR.national_code(r)
        uv = {i: UVAP_Y(uvap_bas[(ms, i)], infl) for i in IY_CROP if (ms, i) in uvap_bas}
        for kind, mp in (("crop", crops), ("animal", animals)):
            for model_act, members in mp.items():
                s, w = defaultdict(float), 0.0
                for c in members:
                    L = D.get((r, c, "LEVL", "Y"), 0.0)
                    if not (L > 0 and D.get((r, c, "LEVL", "BAS"))):
                        continue
                    G, g_raw = G_of(r, c), G_of(r, c, bounded=False)
                    bas = {i: D.get((r, c, i, "BAS"), 0.0) for i in IY_CROP}
                    if not any(bas[i] for i in ("PLAP", "INPO")):
                        continue
                    for i in ("PLAP", "INPO"):
                        if bas[i] and i not in uv:
                            missing_uv.add((ms, i))
                    w += L
                    q = {i: DATA_IY_Y(bas[i], f(c, i), G, 1.0) or 0.0 for i in ("PLAP", "INPO")}
                    if kind == "animal":
                        s["inpo_yf"] += L * q["INPO"]
                        s["inpo_bas"] += L * bas["INPO"]
                    else:
                        s["plap"] += L * q["PLAP"] * uv.get("PLAP", 0.0) / 1000.0
                        s["inpo"] += L * q["INPO"] * uv.get("INPO", 0.0) / 1000.0
                        # the organic top-up's quantity: EFUL and SERI added to INPO's base coefficient (organic_io.gms
                        # l. 111-115), so it follows INPO's update
                        for i in ("EFUL", "SERI"):
                            t = DATA_IY_Y(bas[i], f(c, "INPO"), G, 1.0) or 0.0
                            s["eful_inpo"] += L * t * uv.get("INPO", 0.0) / 1000.0
                            s["eful"] += L * t * uv.get(i, 0.0) / 1000.0
                        if 0.5 < g_raw < 1.5:          # at a bound (or without a yield) the cost does not move
                            for i in IY_CROP:
                                if bas[i]:
                                    k = "yd_plap" if i == "PLAP" else "yd_inpo" if i == "INPO" else "yd_rest"
                                    s[k] += L * f(c, i) * bas[i] * G * uv.get(i, 0.0) / 1000.0
                        yb = sum(D.get((r, c, o, "BAS"), 0.0) for o in p2y.get(c, []))
                        s["yld"] += L * yb
                        s["yld_g"] += L * yb * G
                    if ms[:2] not in ("UK", "TU", "AL", "BA", "CS", "KO", "MK", "MO", "NO"):
                        for i in ("PLAP", "INPO"):
                            if bas[i]:
                                check.append((r, c, i, DATA_IY_Y(bas[i], f(c, i), G, TF)))
                if w <= 0:
                    continue
                if kind == "animal":
                    if s["inpo_bas"] > 0:
                        rows.append([r, model_act] + [float("nan")] * 8 + [s["inpo_yf"] / s["inpo_bas"], w])
                else:
                    g = s["yld_g"] / s["yld"] if s["yld"] > 0 else float("nan")
                    rows.append([r, model_act] + [s[k] / w for k in ("plap", "inpo", "eful", "eful_inpo", "yd_rest",
                                                                      "yd_plap", "yd_inpo")] + [g, float("nan"), w])
    out = pd.DataFrame(rows, columns=COLS).sort_values(["region", "activity"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"{OUT.name}: {len(out)} rows ({out.inpo_yield_factor.isna().sum()} crop, {out.inpo_yield_factor.notna().sum()} animal), "
          f"{out.region.nunique()} regions; member-state inputs without UVAP: {sorted(missing_uv)}")
    if not a.no_check:
        ref = read_reference_2030(a.src, acts)
        dev = [abs(v / ref[(r, c, i)] - 1.0) for r, c, i, v in check if ref.get((r, c, i))]
        n_miss = sum(1 for r, c, i, _ in check if not ref.get((r, c, i)))
        # the listing prints six to seven significant digits
        print(f"check against CAPRI's 2030 reference: {len(dev)} EU rows, max relative difference {max(dev):.2e}, "
              f"{sum(x > 1e-5 for x in dev)} above 1e-5; {n_miss} without a reference value")
        assert max(dev) < 1e-5


if __name__ == "__main__":
    main()
