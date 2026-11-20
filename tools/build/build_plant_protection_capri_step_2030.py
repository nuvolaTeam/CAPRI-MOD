"""CAPRI's two valuations of each crop's plant protection at its 2030 reference, for the comparison switch
supply.greendeal_plap_crop_level_capri_step (docs/CAPRI_DEPARTURES_REGISTER.md DEP-51, its crop-level part; the
project lead's decision of 19 November 2026).

CAPRI's 2030 reference and the PMP calibration of its supply models ran with the pesticide module's aggregates
(META "Stage of pesticide disaggregation: 5_aggregates"): each crop's plant-protection cost is dataOut's Plantp_cost.
Its Green Deal step ran with "none [default]": the crop pays its PLAP coefficient at PLAP's unit value
(p_linObjeCont: DATA(PLAP) x UVAG(PLAP)). The two differ by crop (DE80 barley 120.7 against 70.2 EUR/ha in CAPRI's
2030 money), so CAPRI's step changes each crop's margin before any policy. The model has one representation in base
and scenario (DEP-51). With the switch on, its Green Deal step moves each crop's mean plant-protection cost to CAPRI's
step (capri_mod/supply/policy.py, _apply_greendeal_input_changes).

Source: CAPRI's 2030 Green Deal baseline, dataOut of res_2_1730greendeal_refdefaulta (tools/lib/paths.BASELINE_REF,
the run the model's 2030 base reproduces):
  dataOut(R, '', crop, 'PLAP', '2030')         the plant-protection coefficient (EUR per ha at constant prices x 1000)
  dataOut(R, '', 'UVAG', 'PLAP', '2030')       PLAP's unit value (an index, per 1000)
  dataOut(R, '', crop, 'Plantp_cost', '2030')  the pesticide module's cost per ha (EUR)
  dataOut(R, '', crop, 'LEVL', '2030')         the weights where a model crop sums CAPRI activities (CROP_MAP_CAPMOD)
Values in CAPRI's 2030 money (the model deflates them at run time, capri_mod/data/inputs.money_deflator).

Output
  capri_data/baselines/capri_greendeal_ref/1730/supply/plant_protection_capri_step_2030.csv
      region, activity, plap_uvag_eur_ha (DATA(PLAP) x UVAG(PLAP) / 1000), plantp_cost_eur_ha, levl_capri (1000 ha)
  Rows for the supply models' regional units (capri_data/codes/regional_units.csv) where CAPRI has both values and a
  positive level.

    python tools/build/build_plant_protection_capri_step_2030.py [--src ZIP]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib")]
from paths import BASELINE_REF  # noqa: E402  (CAPRI's material outside the repository)
from capri_mod.csvio import read_csv  # noqa: E402  (exact float reads, test_exact_io)
from _grep import lines  # noqa: E402  (a listing's lines, plain or zipped)
import _model_codes as _MC  # noqa: E402  (the model's activities and their CAPRI activities)

OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply" / "plant_protection_capri_step_2030.csv"
UNITS = ROOT / "capri_data" / "codes" / "regional_units.csv"


def num(s: str) -> float:
    s = s.strip().rstrip(",").strip()
    return 0.0 if s.upper() == "EPS" else float(s)


def read(src: Path):
    """({(region, CAPRI activity, item): value}, {region: UVAG(PLAP)}) at 2030."""
    rx = re.compile(r"^'([A-Z0-9_]{8})'\.''\.'([A-Za-z0-9_]+)'\.'(PLAP|Plantp_cost|LEVL)'\.'2030'\s+(\S+)")
    acts = {c for cs in _MC.CROP_MAP_CAPMOD.values() for c in cs}
    val, uv = {}, {}
    for line in lines(src):
        if "'2030'" not in line or not ("'PLAP'" in line or "'Plantp_cost'" in line or "'LEVL'" in line):
            continue
        m = rx.match(line)
        if not m:
            continue
        r, a, it, v = m.group(1), m.group(2), m.group(3), num(m.group(4))
        if a == "UVAG" and it == "PLAP":
            uv[r] = v
        elif a in acts:
            val[(r, a, it)] = v
    return val, uv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=BASELINE_REF)
    a = ap.parse_args()
    val, uv = read(a.src)
    units = set(read_csv(UNITS)["region"])
    regions = sorted({r for (r, _, _) in val} & set(uv) & units)
    rows = []
    for r in regions:
        for act, codes in _MC.CROP_MAP_CAPMOD.items():
            w = defaultdict(float)
            for c in codes:
                lv, q, pc = val.get((r, c, "LEVL"), 0.0), val.get((r, c, "PLAP")), val.get((r, c, "Plantp_cost"))
                if lv > 0 and q is not None and pc is not None:
                    w["levl"] += lv
                    w["plap_uvag"] += lv * q * uv[r] / 1000.0
                    w["plantp"] += lv * pc
            if w["levl"] > 0:
                rows.append(dict(region=r, activity=act, plap_uvag_eur_ha=w["plap_uvag"] / w["levl"],
                                 plantp_cost_eur_ha=w["plantp"] / w["levl"], levl_capri=w["levl"]))
    o = pd.DataFrame(rows).sort_values(["region", "activity"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    o.to_csv(OUT, index=False)
    print(f"plant_protection_capri_step_2030.csv: {len(o)} region x crop rows ({o.region.nunique()} regions); "
          f"ratio plap_uvag / plantp_cost median {float((o.plap_uvag_eur_ha / o.plantp_cost_eur_ha).median()):.3f}")


if __name__ == "__main__":
    main()
