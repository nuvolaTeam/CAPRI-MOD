"""CAPRI's 2030 manure N, P2O5 and K2O per head, per model region and model head (KNOWN_ISSUES K179): the excretion
coefficients the model's manure terms use at the 2030 market year.

In a simulation CAPRI computes each animal activity's manure output per head from its herd data at the simulation year
(capmod.gms l. 1090: $BATINCLUDE 'feed\\req_or_man_fnc.gms' man '"Y"', when not in baseline mode; MANN from the
literature crude-protein requirement less the N in products, MANP and MANK from the milk yield, days and live weights
with CAPRI's fixed manure contents; capri_mod/feed/equations/req_or_man_fnc.py) before it solves; its supply model then multiplies
that DATA(r, act, MANN/MANP/MANK, "Y") by the activity level (e_EXCRET, ManureNPK_ with manExportOrAppl_ and InclEmiAppl_,
supply_model.gms l. 927-1036 and 1305-1338, with the mitigation options' factors). The 2030 Green Deal baseline the model's 2030 base is taken from
(res_2_1730greendeal_refdefaulta, tools/lib/paths.BASELINE_REF) reports those coefficients in dataOut (MANN, MANP, MANK
of every animal activity at 2030); over a region's activities LEVL x MANN adds up to the region's EXCRET. They differ
from the 2017 values (sim_ini_21730 carries the 2017 ones at "Y" too; e.g. FR52's suckler cows 65.16 kg N per head in
the 2030 baseline, 68.57 in 2017). Until 18 November 2026 the model's 2030 runs took the 2017 coefficients
(livestock_manure_{n,p,k}_coef.csv, tools/build/build_livestock_output_coef.py and build_npk_balance_2030.py), its
dairy cows' manure N moved by its own rule on the milk yield (capri_mod/projection/projection_module.py).

As the 2017 coefficients: CAPRI's regional total of each nutrient (LEVL x coefficient, summed over CAPRI's activities of
the model animal) over the model's head count of the animal, per territory group (tools/lib/_model_regions.capri_groups;
build_livestock_output_coef.per_head, the member state's row where a model region has no regional row); here CAPRI's
2030 levels and coefficients (its activities MAACT: DCOL, DCOH, SCOW, BULL, BULH, HEIL, HEIH, HEIR, CAMF, CAFF, CAMR,
CAFR, SOWS, PIGF, HENS, POUF, SHGM, SHGF) over the model's 2030 base heads (the 2017 heads x the 2030 reference
trajectory's herd factor, as the projection projects them: tools/build/build_young_animals_2030.herds_2030). So the
model's 2030 base excretion is CAPRI's 2030 EXCRET.

The baseline's dataOut gives the coefficients at the baseline's solution, mitigation factors included; it does not
report the options' adoption, so a reference adoption of low-nitrogen feeding or breeding, if any, cannot be told
apart here. The model's options start from no adoption at its 2030 base (capri_mod/supply/livestock.py).

Outputs (as the 2017 files: model region x model animal, kg per head; empty where the model has no such animal)
  capri_data/baselines/capri_greendeal_ref/1730/environment/livestock_manure_n_coef_2030.csv   N
  capri_data/baselines/capri_greendeal_ref/1730/environment/livestock_manure_p_coef_2030.csv   P2O5
  capri_data/baselines/capri_greendeal_ref/1730/environment/livestock_manure_k_coef_2030.csv   K2O

    python tools/build/build_livestock_manure_2030.py [--ref ZIP]
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT))
from _grep import grep  # noqa: E402  (grep -E in Python: any system)
from paths import BASELINE_REF  # noqa: E402  (CAPRI's material outside the repository)

OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment"
#: CAPRI's 2030 animal activities (MAACT) -> the model's animals (DCOW, BULF and HEIF are the sums of their intensity
#: variants in dataOut: not read, as tools/build/build_young_animals_2030.MAP)
MAP = {"DCOL": "DCOW", "DCOH": "DCOW", "SCOW": "BCOW", "BULL": "BULL", "BULH": "BULL",
       "HEIL": "HFRS", "HEIH": "HFRS", "HEIR": "HFRS", "CAMF": "CALV", "CAFF": "CALV", "CAMR": "CALV", "CAFR": "CALV",
       "SOWS": "PIGS", "PIGF": "PIGF", "HENS": "LAYS", "POUF": "BROI", "SHGM": "SHGM", "SHGF": "SHGF"}
#: CAPRI's manure item, CAPRI's nutrient (EXCRET's column), output file
NUTRIENTS = (("MANN", "NITF", "livestock_manure_n_coef_2030.csv"),
             ("MANP", "PHOF", "livestock_manure_p_coef_2030.csv"),
             ("MANK", "POTF", "livestock_manure_k_coef_2030.csv"))
_ROW = re.compile(r"^'([A-Z]{2}[A-Z0-9]{6})'\.''\.'([A-Z0-9]+)'\.'([A-Z]+)'\.'2030'\s+([^,\s]+)")


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / "build" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _num(tok: str) -> float:
    t = tok.strip().upper()
    return 0.0 if t in ("EPS", "NA", "UNDF", "+INF", "-INF", "INF") else float(tok)


def capri_2030(ref: Path):
    """({(CAPRI region, model animal, manure item): LEVL x coefficient, t}, {(CAPRI region, nutrient): EXCRET, kt}) of
    the baseline's dataOut at 2030."""
    acts = "|".join(MAP)
    txt = grep(rf"^'[A-Z]{{2}}[A-Z0-9]{{6}}'\.''\.'({acts})'\.'(LEVL|MANN|MANP|MANK)'\.'2030'"
               rf"|^'[A-Z]{{2}}[A-Z0-9]{{6}}'\.''\.'EXCRET'\.'(NITF|PHOF|POTF)'\.'2030'", str(ref))
    v, excret = defaultdict(dict), {}
    for line in txt.splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        r, row, col, x = m.group(1), m.group(2), m.group(3), _num(m.group(4))
        if row == "EXCRET":
            excret[(r, col)] = x
        else:
            v[(r, row)][col] = x
    totals = defaultdict(float)
    for (r, a), d in v.items():
        lv = d.get("LEVL", 0.0)
        for item in ("MANN", "MANP", "MANK"):
            if lv and d.get(item):
                totals[(r, MAP[a], item)] += lv * d[item]
    return totals, excret


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ref", type=Path, default=BASELINE_REF, help="CAPRI's 2030 baseline (dataOut listing, zip)")
    args = ap.parse_args()
    B = _tool("build_livestock_output_coef")
    Y = _tool("build_young_animals_2030")
    totals, excret = capri_2030(args.ref)
    herds = Y.herds_2030()
    OUT.mkdir(parents=True, exist_ok=True)
    for item, nut, name in NUTRIENTS:
        t = {(r, a): x for (r, a, it), x in totals.items() if it == item}
        coef = B.per_head(t, herds)
        lost = [(r, a) for r in coef.index for a in coef.columns
                if a in herds.columns and float(herds.at[r, a]) > 0 and not coef.at[r, a] > 0
                and any(k[1] == a and k[0][:2] == r[:2] for k in t)]
        coef.to_csv(OUT / name)
        # the model's 2030 base excretion against CAPRI's EXCRET, per member state (kt)
        worst, n = 0.0, 0
        for ms in sorted({r[:2] for r in coef.index}):
            e = excret.get((f"{ms}000000", nut))
            if not e:
                continue
            regs = [r for r in coef.index if r[:2] == ms]
            mod = sum(float(herds.at[r, a]) * float(coef.at[r, a]) for r in regs for a in coef.columns
                      if a in herds.columns and coef.at[r, a] == coef.at[r, a]) / 1000.0
            worst, n = max(worst, abs(mod / e - 1.0)), n + 1
        print(f"wrote {OUT / name}: {coef.notna().sum().sum()} coefficients; model 2030 heads x coefficient against "
              f"CAPRI's EXCRET {nut} of {n} member states: worst {worst:.2e}; animals with CAPRI manure but no "
              f"coefficient: {lost[:8]}")


if __name__ == "__main__":
    main()
