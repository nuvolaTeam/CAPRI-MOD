"""CAPRI's 2030 N in livestock products per model head (register DEP-13; KNOWN_ISSUES K202): the coefficient of the
report item n_animal_products at the 2030 market year.

In a simulation CAPRI recomputes each animal activity's N in products at the simulation year before it solves:
capmod.gms l. 1090 includes feed/req_or_man_fnc.gms in its manure mode ('man', "Y"; not in baseline mode), which runs
fert/calc_nexport.gms for "Y" (req_or_man_fnc.gms l. 1814-1817) and then takes DATA(r, act, "CRPR_EXPT", "Y") off the
crude protein intake for the manure N (l. 1824-1825). sim_ini_21730 still carries the 2017 values at "Y" (equal to its
"BAS" in all 4,836 cells); the simulation overwrites them. The 2030 reference does not report CRPR_EXPT, so it is
computed here as CAPRI computes it: calc_nexport_CRPR_EXPT on each activity's 2030 items of the reference's dataOut
(COMI, COMF, BEEF, the young animals produced and bought, SGMT, SGMI, EGGS, POUM, PORK). Check: the same function on
sim_ini_21730's 2017 items ("BAS") gives sim_ini's 2017 CRPR_EXPT in every regional cell (relative 1e-9).

As the 2017 coefficient (tools/build/build_livestock_n_export_coef.py, build_livestock_output_coef.build): CAPRI's
regional total (LEVL x CRPR_EXPT, summed over CAPRI's activities of the model animal) over the model's heads, per
territory group (build_livestock_output_coef.per_head); here CAPRI's 2030 levels and N in products (its activities as
tools/build/build_livestock_manure_2030.MAP) over the model's 2030 base heads
(tools/build/build_young_animals_2030.herds_2030). Until 24 November 2026 the model's 2030 value was the 2017 one per
head x the projected yield factor (the dairy cows' + 0.0054 kg N per kg of extra milk; ProjectionModule.
_project_livestock).

Output (as the 2017 file: model region x model animal, kg N per head; empty where the model has no such animal)
  capri_data/baselines/capri_greendeal_ref/1730/environment/livestock_n_export_coef_2030.csv

    python tools/build/build_livestock_n_export_2030.py [--ref ZIP] [--no-check]
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT))
from _grep import grep  # noqa: E402  (grep -E in Python: any system)
from paths import BASELINE_REF, REFERENCE  # noqa: E402  (CAPRI's material outside the repository)

OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment" / "livestock_n_export_coef_2030.csv"
SIMINI = REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz"
#: CAPRI's ruminant activities in the model (sets.gms l. 3100-3101) and the subsets calc_nexport.gms uses
#: (capmod.gms l. 182 DCOW, l. 188 BULF; sets.gms l. 3098 CALF); the others of MAACT are MNRUMI (sets.gms l. 3110)
MRUMI = {"DCOL", "DCOH", "SCOW", "BULH", "BULL", "HEIL", "HEIH", "HEIR", "CAMF", "CAFF", "CAMR", "CAFR", "SHGM", "SHGF"}
CALF, BULF, DCOW = {"CAMF", "CAFF"}, {"BULL", "BULH"}, {"DCOL", "DCOH"}
#: PACT_TO_O and PACT_TO_I of the items calc_nexport.gms conditions on (sets.gms l. 5187-5262 and 5292-5362)
PACT_TO_O = {"DCOL": {"COMI", "COMF", "BEEF", "YCAM", "YCAF"}, "DCOH": {"COMI", "COMF", "BEEF", "YCAM", "YCAF"},
             "SCOW": {"COMF", "BEEF", "YCAM", "YCAF"}, "BULL": {"BEEF"}, "BULH": {"BEEF"}, "CAMF": {"BEEF"},
             "CAFF": {"BEEF"}, "PIGF": {"PORK"}, "SHGM": {"SGMI", "SGMF", "SGMT", "YLAM"}, "SHGF": {"SGMT"},
             "HENS": {"EGGS", "YCHI", "POUM"}, "POUF": {"POUM"}, "CAMR": {"YBUL"}, "CAFR": {"YHEI"},
             "HEIL": {"BEEF"}, "HEIH": {"BEEF"}, "HEIR": {"YCOW"}, "SOWS": {"YPIG", "PORK"}}
PACT_TO_I = {"DCOL": {"ICOW"}, "DCOH": {"ICOW"}, "SCOW": {"ICOW"}, "BULL": {"IBUL"}, "BULH": {"IBUL"},
             "CAMF": {"ICAM", "ICAL"}, "CAFF": {"ICAF", "ICAL"}, "PIGF": {"IPIG"}, "SHGM": {"ILAM"}, "SHGF": {"ILAM"},
             "HENS": {"ICHI"}, "POUF": {"ICHI"}, "CAMR": {"ICAM", "ICAL"}, "CAFR": {"ICAF", "ICAL"},
             "HEIL": {"IHEI"}, "HEIH": {"IHEI"}, "HEIR": {"IHEI"}, "SOWS": {"IPIG"}}
ITEMS = ("COMI", "COMF", "BEEF", "YCAF", "YCAM", "ICAF", "ICAM", "YBUL", "IBUL", "YHEI", "IHEI", "YCOW", "ICOW",
         "ILAM", "YLAM", "SGMT", "SGMI", "EGGS", "POUM", "IPIG", "YPIG", "PORK")
_ROW = re.compile(r"^'([A-Z]{2}[A-Z0-9]{6})'\.''\.'([A-Z0-9]+)'\.'([A-Z]+)'\.'2030'\s+([^,\s]+)")


def calc_nexport_CRPR_EXPT(act: str, d: dict) -> float:
    """CAPRI's N exported in products per unit of an animal activity, kg N (t N per 1000 head; the poultry per 1000
    animals): fert/calc_nexport.gms, DATA(RS, act, "CRPR_EXPT", %yr%) from the activity's items d = DATA(RS, act, ., %yr%)
    (only where the activity has a level, as the statement's $ DATA(RS, act, "LEVL", %yr%)).

    CAPRI's GAMS, fert/calc_nexport.gms (l. 21-98 and 100-133; the comment lines dropped):

          DATA(RS,MRUMI,"CRPR_EXPT",%yr%) $ DATA(RS,MRUMI,"LEVL",%yr%)  =
                                      DATA(RS,MRUMI,"BEEF",%yr%) * (  (0.027/0.60)    $ CALF(MRUMI)
                                                                    + (0.0285/0.54)   $ BULF(MRUMI)
                                                                    + (0.0285/0.54)   $ SAMEAS(MRUMI,"HEIL")
                                                                    + (0.0285/0.57)   $ (SAMEAS(MRUMI,"HEIH") or SAMEAS(MRUMI,"SCOW"))
                                                                    + (0.022/0.54)    $ DCOW(MRUMI)) $ PACT_TO_O(MRUMI,"BEEF")
                                    + (DATA(RS,MRUMI,"COMI",%yr%) * 0.0054) $ PACT_TO_O(MRUMI,"COMI")
                                    + (DATA(RS,MRUMI,"COMF",%yr%) * 0.0054) $ PACT_TO_O(MRUMI,"COMF")
                                    + (DATA(RS,MRUMI,"YCAF",%yr%) + DATA(RS,MRUMI,"YCAM",%yr%))/1000 * 50 * 0.030
                                    - (DATA(RS,MRUMI,"ICAF",%yr%) + DATA(RS,MRUMI,"ICAM",%yr%))/1000 * 50 * 0.030
                                    + (DATA(RS,MRUMI,"YBUL",%yr%)/1000 * 335 * 0.0285) $ PACT_TO_O(MRUMI,"YBUL")
                                    - (DATA(RS,MRUMI,"IBUL",%yr%)/1000 * 335 * 0.0285) $ PACT_TO_I(MRUMI,"IBUL")
                                    + (DATA(RS,MRUMI,"YHEI",%yr%)/1000  * 300 * 0.0245) $ PACT_TO_O(MRUMI,"YHEI")
                                    - (DATA(RS,MRUMI,"IHEI",%yr%)/1000  * 300 * 0.0245) $ PACT_TO_I(MRUMI,"IHEI")
                                    + (DATA(RS,MRUMI,"YCOW",%yr%)/1000  * 575 * 0.0220) $ PACT_TO_O(MRUMI,"YCOW")
                                    - (DATA(RS,MRUMI,"ICOW",%yr%)/1000  * 575 * 0.0220) $ PACT_TO_I(MRUMI,"ICOW")
                                    - (DATA(RS,MRUMI,"ILAM",%yr%)/1000 * 6 * 0.0245) $ PACT_TO_I(MRUMI,"ILAM")
                                    + (DATA(RS,MRUMI,"YLAM",%yr%)/1000 * 6 * 0.0245) $ PACT_TO_O(MRUMI,"YLAM")
                                    + (DATA(RS,MRUMI,"SGMT",%yr%) * 0.0245/0.60) $ PACT_TO_O(MRUMI,"SGMT")
                                    + (DATA(RS,MRUMI,"SGMI",%yr%) * 0.0053     ) $ PACT_TO_O(MRUMI,"SGMI")
                                    + 3.5 * 0.11 $ SAMEAS(MRUMI,"SHGM");
          DATA(RS,MNRUMI,"CRPR_EXPT",%yr%) $ DATA(RS,MNRUMI,"LEVL",%yr%)  =
                                      (DATA(RS,MNRUMI,"EGGS",%yr%) * 0.019) $ PACT_TO_O(MNRUMI,"EGGS")
                                    + (DATA(RS,MNRUMI,"POUM",%yr%) / 0.8 * 0.033) $ PACT_TO_O(MNRUMI,"POUM")
                                    - (DATA(RS,MNRUMI,"IPIG",%yr%)/1000 * 20 * 0.0251) $ PACT_TO_I(MNRUMI,"IPIG")
                                    + (DATA(RS,MNRUMI,"YPIG",%yr%)/1000 * 20 * 0.0251) $ PACT_TO_O(MNRUMI,"YPIG")
                                    + (DATA(RS,MNRUMI,"PORK",%yr%) * 0.0251/0.78) $ PACT_TO_O(MNRUMI,"PORK");
    """
    D = lambda k: float(d.get(k, 0.0) or 0.0)
    o, i = PACT_TO_O.get(act, set()), PACT_TO_I.get(act, set())
    if act in MRUMI:
        f = ((0.027 / 0.60) * (act in CALF) + (0.0285 / 0.54) * (act in BULF) + (0.0285 / 0.54) * (act == "HEIL")
             + (0.0285 / 0.57) * (act in ("HEIH", "SCOW")) + (0.022 / 0.54) * (act in DCOW))
        x = D("BEEF") * f * ("BEEF" in o)
        x += D("COMI") * 0.0054 * ("COMI" in o) + D("COMF") * 0.0054 * ("COMF" in o)
        x += (D("YCAF") + D("YCAM")) / 1000 * 50 * 0.030 - (D("ICAF") + D("ICAM")) / 1000 * 50 * 0.030
        x += D("YBUL") / 1000 * 335 * 0.0285 * ("YBUL" in o) - D("IBUL") / 1000 * 335 * 0.0285 * ("IBUL" in i)
        x += D("YHEI") / 1000 * 300 * 0.0245 * ("YHEI" in o) - D("IHEI") / 1000 * 300 * 0.0245 * ("IHEI" in i)
        x += D("YCOW") / 1000 * 575 * 0.0220 * ("YCOW" in o) - D("ICOW") / 1000 * 575 * 0.0220 * ("ICOW" in i)
        x += -D("ILAM") / 1000 * 6 * 0.0245 * ("ILAM" in i) + D("YLAM") / 1000 * 6 * 0.0245 * ("YLAM" in o)
        x += D("SGMT") * 0.0245 / 0.60 * ("SGMT" in o) + D("SGMI") * 0.0053 * ("SGMI" in o)
        return x + 3.5 * 0.11 * (act == "SHGM")
    x = D("EGGS") * 0.019 * ("EGGS" in o) + D("POUM") / 0.8 * 0.033 * ("POUM" in o)
    x += -D("IPIG") / 1000 * 20 * 0.0251 * ("IPIG" in i) + D("YPIG") / 1000 * 20 * 0.0251 * ("YPIG" in o)
    return x + D("PORK") * 0.0251 / 0.78 * ("PORK" in o)


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / "build" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _num(tok: str) -> float:
    t = tok.strip().upper()
    return 0.0 if t in ("EPS", "NA", "UNDF", "+INF", "-INF", "INF") else float(tok)


def capri_2030(ref: Path, acts: dict) -> dict:
    """{(CAPRI region, model animal): sum over the animal's CAPRI activities of LEVL x CRPR_EXPT, t N} at 2030, the
    N in products from the reference's dataOut items (calc_nexport_CRPR_EXPT)."""
    txt = grep(rf"^'[A-Z]{{2}}[A-Z0-9]{{6}}'\.''\.'({'|'.join(acts)})'\.'(LEVL|{'|'.join(ITEMS)})'\.'2030'", str(ref))
    v = defaultdict(dict)
    for line in txt.splitlines():
        m = _ROW.match(line)
        if m:
            v[(m.group(1), m.group(2))][m.group(3)] = _num(m.group(4))
    totals = defaultdict(float)
    for (r, a), d in v.items():
        lv = d.get("LEVL", 0.0)
        if lv:
            totals[(r, acts[a])] += lv * calc_nexport_CRPR_EXPT(a, d)
    return totals


def check_on_simini_2017(acts) -> tuple[int, float]:
    """calc_nexport_CRPR_EXPT on sim_ini_21730's 2017 items ("BAS") against its CRPR_EXPT ("BAS"), the regional cells
    with a level: (cells, the largest relative difference)."""
    t = pd.read_csv(SIMINI, usecols=["d0", "d1", "d2", "d3", "value"], keep_default_na=False, na_values=[""])
    t = t[(t.d3 == "BAS") & t.d1.isin(list(acts)) & t.d2.isin(("LEVL", "CRPR_EXPT") + ITEMS)
          & ~t.d0.str.endswith("000000")]
    worst, n = 0.0, 0
    for (r, a), g in t.groupby(["d0", "d1"]):
        d = dict(zip(g.d2, g.value.astype(float)))
        if d.get("LEVL", 0.0) > 0 and "CRPR_EXPT" in d:
            x = calc_nexport_CRPR_EXPT(a, d)
            worst, n = max(worst, abs(x - d["CRPR_EXPT"]) / max(abs(d["CRPR_EXPT"]), 1e-9)), n + 1
    return n, worst


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ref", type=Path, default=BASELINE_REF, help="CAPRI's 2030 baseline (dataOut listing, zip)")
    ap.add_argument("--no-check", action="store_true", help="skip the check on sim_ini_21730's 2017 values")
    args = ap.parse_args()
    B = _tool("build_livestock_output_coef")
    Y = _tool("build_young_animals_2030")
    acts = _tool("build_livestock_manure_2030").MAP
    if not args.no_check:
        n, worst = check_on_simini_2017(acts)
        assert n > 4000 and worst < 1e-9, (n, worst)
        print(f"calc_nexport on sim_ini_21730's 2017 items: CAPRI's CRPR_EXPT in {n} regional cells, worst {worst:.1e}")
    herds = Y.herds_2030()
    coef = B.per_head(capri_2030(args.ref, acts), herds)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    coef.to_csv(OUT)
    print(f"wrote {OUT.relative_to(ROOT)}: {coef.notna().sum().sum()} coefficients; EU median kg N per head "
          f"{coef.median().round(2).to_dict()}")


if __name__ == "__main__":
    main()
