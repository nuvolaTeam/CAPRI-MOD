"""CAPRI's two valuations of each crop's plant protection at its 2030 reference, for the comparison switch
supply.greendeal_plap_crop_level_capri_step (docs/CAPRI_DEPARTURES_REGISTER.md DEP-51, its crop-level part; the
project lead's decision of 19 November 2026).

CAPRI's 2030 reference and the PMP calibration of its supply models ran with the pesticide module's aggregates
(META "Stage of pesticide disaggregation: 5_aggregates"): each crop's plant-protection cost is dataOut's Plantp_cost.
Its Green Deal step ran with "none [default]": PLAP is in the crops' linear objective (sets.gms l. 5365-5368 take it
out only with PEST_DISAGG on), valued at the member state's UVAP of the simulation year (p_linObjeCont,
capmod/define_objc.gms l. 40-44; UVAP(Y) = UVAP(BAS) x p_infl^(Y - BAS), capmod/inflation_and_trend_interpolation.gms
l. 23, 69-73). The two differ by crop (DE80 barley 117.8 against 70.2 EUR/ha in CAPRI's 2030 money), so CAPRI's
step changes each crop's margin before any policy. The model has one representation in base
and scenario (DEP-51). With supply.greendeal_plap_crop_level_capri_step its Green Deal step moves each crop's mean
plant-protection cost to CAPRI's step (capri_mod/supply/policy.py, _apply_greendeal_input_changes); with
supply.greendeal_plap_mix_capri_step the technology mix columns carry the T1 - T2 cost CAPRI's step adds
(p_technFact PLAP +-0.4; policy._plap_mix_capri_step).

Until 21 November 2026 the unit value was dataOut's regional UVAG(PLAP) at 2030, which is not the price p_linObjeCont
uses: the member state's UVAP(Y) over it runs from 0.72 to 1.37 over the table's rows (DE21 1.011, AT11 0.900, PT20
1.372), 4.7% apart on average weighted by CAPRI's crop area.

Sources:
  CAPRI's 2030 Green Deal baseline, dataOut of res_2_1730greendeal_refdefaulta (tools/lib/paths.BASELINE_REF, the run
  the model's 2030 base reproduces):
    dataOut(R, '', crop, 'PLAP', '2030')         the plant-protection coefficient (EUR per ha at constant prices x 1000)
    dataOut(R, '', crop, 'Plantp_cost', '2030')  the pesticide module's cost per ha (EUR)
    dataOut(R, '', crop, 'LEVL', '2030')         the weights where a model crop sums CAPRI activities (CROP_MAP_CAPMOD)
  sim_ini_21730 (CAPRI's 2030 restart file, written at the simulation start; capri_sources/reference/simini/
  simini_21730, tools/build/build_simini_reference.py):
    DATA(MS, 'UVAP', 'PLAP', 'BAS')              the member state's unit value of plant protection, base year
    p_infl                                       the inflation index
Values in CAPRI's 2030 money (the model deflates them at run time, capri_mod/data/inputs.money_deflator: 1.019^13 to
rounding, CAPRI's p_inflationFactor). sim_ini_21730 has no UVAP(PLAP) for Turkey's regions: no rows there.

Output
  capri_data/baselines/capri_greendeal_ref/1730/supply/plant_protection_capri_step_2030.csv
      region, activity, plap_uvap_eur_ha (DATA(PLAP) x UVAP(PLAP, 2030) / 1000), plantp_cost_eur_ha,
      levl_capri (1000 ha)
  Rows for the supply models' regional units (capri_data/codes/regional_units.csv) where CAPRI has both values, the
  member state's UVAP and a positive level.

    python tools/build/build_plant_protection_capri_step_2030.py [--src ZIP]
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
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib")]
from paths import BASELINE_REF, BASE_YEAR, REFERENCE  # noqa: E402  (CAPRI's material outside the repository)
from capri_mod.csvio import read_csv  # noqa: E402  (exact float reads, test_exact_io)
from _grep import lines  # noqa: E402  (a listing's lines, plain or zipped)
import _model_codes as _MC  # noqa: E402  (the model's activities and their CAPRI activities)

OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply" / "plant_protection_capri_step_2030.csv"
UNITS = ROOT / "capri_data" / "codes" / "regional_units.csv"
SIMINI = REFERENCE / "simini" / "simini_21730"          # tools/build/build_simini_reference.py
SIM_YEAR = 2030


def num(s: str) -> float:
    s = s.strip().rstrip(",").strip()
    return 0.0 if s.upper() == "EPS" else float(s)


def read(src: Path) -> dict:
    """{(region, CAPRI activity, item): value} at 2030, items PLAP, Plantp_cost and LEVL."""
    rx = re.compile(r"^'([A-Z0-9_]{8})'\.''\.'([A-Za-z0-9_]+)'\.'(PLAP|Plantp_cost|LEVL)'\.'2030'\s+(\S+)")
    acts = {c for cs in _MC.CROP_MAP_CAPMOD.values() for c in cs}
    val = {}
    for line in lines(src):
        if "'2030'" not in line or not ("'PLAP'" in line or "'Plantp_cost'" in line or "'LEVL'" in line):
            continue
        m = rx.match(line)
        if not m:
            continue
        r, a, it, v = m.group(1), m.group(2), m.group(3), num(m.group(4))
        if a in acts:
            val[(r, a, it)] = v
    return val


def _simini_csv(symbol: str) -> Path:
    path = SIMINI / f"{symbol}.csv.gz"
    assert path.is_file(), (f"{path} missing: python tools/build/build_simini_reference.py --src sim_ini_21730.gdx "
                            "--tag simini_21730")
    return path


def read_uvap_bas() -> dict:
    """{member state: DATA(MS, 'UVAP', 'PLAP', 'BAS')} of sim_ini_21730 (Eps as 0; streamed: DATA is 1.65 million
    records)."""
    out = {}
    with gzip.open(_simini_csv("DATA"), "rt", newline="", encoding="utf-8") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        assert head[:5] == ["d0", "d1", "d2", "d3", "value"], head
        for d0, d1, d2, d3, v, *_ in rd:
            if d1 == "UVAP" and d2 == "PLAP" and d3 == "BAS" and d0.endswith("000000"):
                out[d0] = float(v)
    return out


def read_p_infl() -> float:
    """sim_ini_21730's p_infl (a scalar)."""
    t = read_csv(_simini_csv("p_infl"))
    assert len(t) == 1, t
    return float(t["value"].iloc[0])


def p_inflationFactor(p_infl: float, simy: int = SIM_YEAR, basy: int = BASE_YEAR) -> float:
    """capmod/inflation_and_trend_interpolation.gms l. 23:

        p_inflationFactor(MS)            = p_infl**(CALYEA("20%SIM%")-CALYEA("BAS"));
    """
    return p_infl ** (int(simy) - int(basy))


def UVAP_Y(UVAP_BAS: float, inflationFactor: float) -> float:
    """capmod/inflation_and_trend_interpolation.gms l. 69, 73 (PLAP is not in IOE, the items with price expectations,
    arm/arm_sets.gms l. 942-953):

       DATA(MS,"UVAP",IO,"20%SIM%") $ (NOT IOE(IO)) = DATA(MS,"UVAP",IO,"BAS") * p_inflationFactor(MS);
       DATA(MS,"UVAP",IO,"Y")  = DATA(MS,"UVAP",IO,"20%SIM%");
    """
    return UVAP_BAS * inflationFactor


def linObjeCont_PLAP(DATA_PLAP: float, UVAP: float) -> float:
    """The plant-protection term of p_linObjeCont per ha at technology factor 0 (the crop's mean), as a cost (CAPRI's
    sign is negative), capmod/define_objc.gms l. 40-44:

      p_dataCopy(%regions%,"UVAP",IobjCont,"Y")  = sum(RU_MS(%regions%,MS),DATA(MS,"UVAP",IobjCont,"Y"));

      p_linObjeCont(%regions%,%pacts%,A) $ p_technFact(%regions%,%pacts%,"LEVL",A)
            = (-0.001)*SUM(PACT_TO_I(%pacts%,IobjCont), DATA(%regions%,%pacts%,IobjCont,"Y") * (p_technFact(%regions%,%pacts%,IobjCont,A)+1.)
                                   * p_dataCopy(%regions%,"UVAP",IobjCont,"Y"));
    """
    return 0.001 * DATA_PLAP * UVAP


def member_state(region: str) -> str:
    """The unit's member state (CAPRI's RU_MS): its first two letters (DE210000 -> DE000000; a country unit is its own)."""
    return region[:2] + "000000"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=BASELINE_REF)
    a = ap.parse_args()
    val = read(a.src)
    infl = p_inflationFactor(read_p_infl())
    uvap = {ms: UVAP_Y(v, infl) for ms, v in read_uvap_bas().items()}
    units = set(read_csv(UNITS)["region"])
    regions = sorted(r for r in {r for (r, _, _) in val} & units if member_state(r) in uvap)
    rows = []
    for r in regions:
        uv = uvap[member_state(r)]
        for act, codes in _MC.CROP_MAP_CAPMOD.items():
            w = defaultdict(float)
            for c in codes:
                lv, q, pc = val.get((r, c, "LEVL"), 0.0), val.get((r, c, "PLAP")), val.get((r, c, "Plantp_cost"))
                if lv > 0 and q is not None and pc is not None:
                    w["levl"] += lv
                    w["plap_uvap"] += lv * linObjeCont_PLAP(q, uv)
                    w["plantp"] += lv * pc
            if w["levl"] > 0:
                rows.append(dict(region=r, activity=act, plap_uvap_eur_ha=w["plap_uvap"] / w["levl"],
                                 plantp_cost_eur_ha=w["plantp"] / w["levl"], levl_capri=w["levl"]))
    o = pd.DataFrame(rows).sort_values(["region", "activity"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    o.to_csv(OUT, index=False)
    print(f"plant_protection_capri_step_2030.csv: {len(o)} region x crop rows ({o.region.nunique()} regions); "
          f"ratio plap_uvap / plantp_cost median {float((o.plap_uvap_eur_ha / o.plantp_cost_eur_ha).median()):.3f}")


if __name__ == "__main__":
    main()
