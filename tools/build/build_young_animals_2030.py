"""CAPRI's young-animal coefficients at its 2030 calibration point, per model region and model head (KNOWN_ISSUES
K178): the coefficients the young-animal balances use at the 2030 market year.

CAPRI's young-animal balance (supply_model.gms INPANI_, l. 839-856) multiplies each activity's level by the coefficient
of the simulation year, DATA(r, act, young animal, "Y"); its 2030 calibration file (sim_ini_21730) holds it next to
the base year's ("BAS", 2017): ES41's suckler cows 422.8 male calves per 1000 cows in 2017, 457.0 in 2030; FR52's
397.7 and 372.8. Until 18 November 2026 the model's 2030 runs used the 2017 coefficients
(tools/build/build_young_animals.py).

As the 2017 builder, CAPRI's regional flow of each young animal (LEVL x coefficient / 1000, summed over CAPRI's
activities of the model animal) over the model's head count of the animal, per territory group
(tools/lib/_model_regions.capri_groups), the member state's row where a model region has no regional row; here CAPRI's
2030 levels and coefficients (DATA at "Y" of sim_ini_21730: its activities MAACT, DCOL, DCOH, SCOW, BULL, BULH, HEIL,
HEIH, HEIR, CAMF, CAFF, CAMR, CAFR, SOWS, PIGF, SHGM, SHGF; INPANI_ sums over them) over the model's 2030 base heads (the
2017 heads x the 2030 reference trajectory's herd factor, capri_data/scenarios/capri_ref_2030, as
capri_mod/projection/projection_module.py projects them). So the model's 2030 base flows are CAPRI's 2030 flows. The
value per head stays the 2017 one (the projection layer applies CAPRI's 2030 / 2017 unit value ratio,
capri_mod/projection/prices.py).

Outputs (capri_mod/data/nested_tables.py format, as the 2017 files)
  capri_data/baselines/capri_greendeal_ref/1730/supply/young_animals_2030.csv (+ _coef.csv): calves and young cattle
      pooled across the sexes (the cattle member splits off)
  capri_data/baselines/capri_greendeal_ref/1730/supply/young_animals_by_sex_2030.csv (+ _coef.csv): per sex (the
      default)

    python tools/build/build_young_animals_2030.py [--simini-data DATA.csv.gz]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT))
from paths import REFERENCE  # noqa: E402  (CAPRI's material outside the repository)
from capri_mod.data.nested_tables import read_young_animals, write_young_animals  # noqa: E402

SUPPLY17 = ROOT / "capri_data" / "2017" / "supply"
OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply"
TRAJ = ROOT / "capri_data" / "scenarios" / "capri_ref_2030"
#: CAPRI's 2030 animal activities (MAACT) -> the model's animals
MAP = {"DCOL": "DCOW", "DCOH": "DCOW", "SCOW": "BCOW", "BULL": "BULL", "BULH": "BULL",
       "HEIL": "HFRS", "HEIH": "HFRS", "HEIR": "HFRS", "CAMF": "CALV", "CAFF": "CALV", "CAMR": "CALV", "CAFR": "CALV",
       "SOWS": "PIGS", "PIGF": "PIGF", "SHGM": "SHGM", "SHGF": "SHGF"}
#: the model's animals -> their column in the model's herd table (capri_mod/data/loaders.load_regional_animal_numbers:
#: the model's codes, the column capri_mod/projection/projection_module.py projects)
HCOL = {"DCOW": "DCOW", "BCOW": "BCOW", "BULL": "BULL", "HFRS": "HFRS", "CALV": "CALV", "PIGS": "PIGS", "PIGF": "PIGF",
        "SHGM": "SHGM", "SHGF": "SHGF"}
#: the balances (produced items, used items), as tools/build/build_young_animals.py
BAL_BY_SEX = {"calves_m": ({"YCAM"}, {"ICAM"}), "calves_f": ({"YCAF"}, {"ICAF"}),
              "young_m": ({"YBUL"}, {"IBUL"}), "young_f": ({"YHEI"}, {"IHEI"}),
              "cows": ({"YCOW"}, {"ICOW"}), "piglets": ({"YPIG"}, {"IPIG"}), "lambs": ({"YLAM"}, {"ILAM"})}
BAL_POOLED = {"calves": ({"YCAM", "YCAF"}, {"ICAM", "ICAF"}), "young": ({"YBUL", "YHEI"}, {"IBUL", "IHEI"}),
              **{k: v for k, v in BAL_BY_SEX.items() if k not in ("calves_m", "calves_f", "young_m", "young_f")}}
VARIANTS = (("young_animals_2030.csv", "young_animals_2017.csv", BAL_POOLED),
            ("young_animals_by_sex_2030.csv", "young_animals_by_sex_2017.csv", BAL_BY_SEX))


def _model_regions_lib():
    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mr)
    return mr


def _read_csv(*a, **k):
    """pandas.read_csv with floats parsed to the last digit (KNOWN_ISSUES K82)."""
    import pandas as pd
    k.setdefault("float_precision", "round_trip")
    return pd.read_csv(*a, **k)


def capri_2030(path: Path) -> dict:
    """{CAPRI region: {(activity, item): DATA(region, activity, item, "Y")}} for the young-animal items and LEVL of
    CAPRI's 2030 animal activities (sim_ini_21730's DATA, tools/build/build_simini_reference.py)."""
    items = {i for b in BAL_BY_SEX.values() for s in b for i in s} | {"LEVL"}
    v = defaultdict(dict)
    with gzip.open(path, "rt", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["d3"] == "Y" and row["d1"] in MAP and row["d2"] in items:
                v[row["d0"]][(row["d1"], row["d2"])] = float(row["value"])
    return v


def herds_2030():
    """The model's 2030 base heads: the model's 2017 herd table (load_regional_animal_numbers: the model's codes,
    poultry in 1000 head) x the 2030 reference trajectory's herd factor per region and column, as
    capri_mod/projection/projection_module.py (project_data) projects data["animal_numbers"]. Until 18 November 2026
    the raw table's columns were projected: heifers (HEIF) took CAPRI's factor of its fattening heifers HEIF, not the
    factor of the model's heifers HFRS (HEIF and HEIR) the projection applies (all regions' heads 5% too high, a region's
    0.1 to 3.2 times the projected heads)."""
    from capri_mod.projection.trajectory import BaselineTrajectory
    from capri_mod.data.loaders import load_regional_animal_numbers
    h = load_regional_animal_numbers(ROOT / "capri_data")
    t = BaselineTrajectory.from_file(TRAJ)
    out = h.copy()
    for c in out.columns:
        for r in out.index:
            out.at[r, c] = float(h.at[r, c]) * t.factor("herds", c, 2030, region=r)
    return out


def build(v, herds, bal, base17: dict) -> tuple:
    mr = _model_regions_lib()
    _c2g, groups = mr.capri_groups(list(herds.index))
    grp_of = {r: (sorted(c for c in cs if c in v), sorted(rs)) for cs, rs in groups.values() for r in rs}

    def coefs(codes, regs):
        num, lev = defaultdict(float), defaultdict(float)
        for code in codes:
            d = v.get(code, {})
            for (a, it), val in d.items():
                if it == "LEVL":
                    lev[MAP[a]] += val
            for (a, it), val in d.items():
                if it != "LEVL":
                    num[(MAP[a], it)] += d.get((a, "LEVL"), 0.0) * val / 1000.0
        hd = {m: float(herds.loc[regs, HCOL[m]].sum()) if HCOL[m] in herds.columns else 0.0 for m in lev}
        out = {}
        for b, (prod, use) in bal.items():
            pc = {m: sum(num[(m, i)] for i in prod) / hd[m] for m in lev if hd[m] > 0 and sum(num[(m, i)] for i in prod) > 0}
            uc = {m: sum(num[(m, i)] for i in use) / hd[m] for m in lev if hd[m] > 0 and sum(num[(m, i)] for i in use) > 0}
            if pc and uc:
                out[b] = {"produce": pc, "use": uc}
        return out

    res, nat, missing = {}, 0, []
    for reg in herds.index:
        if reg not in base17:
            continue                                      # the 2017 table has no balance there: none in 2030 either
        codes, regs = grp_of.get(reg, ([], [reg]))
        cf = coefs(codes, regs) if codes else {}
        if not cf:
            nc = mr.national_code(reg)
            if nc in v:
                cf = coefs([nc], [r for r in herds.index if mr.national_code(r) == nc])
                nat += bool(cf)
        if not cf:
            missing.append(reg)
            continue
        rec = {}
        x = herds.loc[reg]
        for b, d in cf.items():
            if b not in base17[reg]:
                continue                                  # a balance the 2017 table does not hold
            p0 = sum(c * float(x.get(HCOL[m], 0.0)) for m, c in d["produce"].items())
            u0 = sum(c * float(x.get(HCOL[m], 0.0)) for m, c in d["use"].items())
            rec[b] = {**d, "base_net_export": p0 - u0, "value_eur_head": float(base17[reg][b]["value_eur_head"])}
        lost = sorted(set(base17[reg]) - set(rec))
        if lost:
            missing.append(f"{reg}:{','.join(lost)}")
        if rec:
            res[reg] = rec
    return res, nat, missing


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--simini-data", type=Path, default=REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz",
                    help="CAPRI's 2030 calibration data, DATA of sim_ini_21730 (tools/build/build_simini_reference.py)")
    args = ap.parse_args()
    v = capri_2030(args.simini_data)
    herds = herds_2030()
    for dest, src17, bal in VARIANTS:
        base17 = read_young_animals(SUPPLY17 / src17)
        res, nat, missing = build(v, herds, bal, base17)
        if missing:
            raise SystemExit(f"{dest}: no CAPRI 2030 balance for {len(missing)} region(s) of the 2017 table: "
                             f"{missing[:12]}")
        OUT.mkdir(parents=True, exist_ok=True)
        write_young_animals(OUT / dest, res)
        print(f"wrote {OUT / dest}: {len(res)} regions ({nat} from the member state's row)")


if __name__ == "__main__":
    main()
