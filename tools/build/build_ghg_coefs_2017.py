"""CAPRI's manure and enteric methane per head and its CO2 from liming and urea, per model region (Sprint 9s;
docs/SYNTHETIC_DATA_AUDIT.md B1-B3, B5).

The accounts used IPCC Tier 1 defaults: one manure-CH4 factor per animal for every region (dairy 16 kg, sows 4.2 kg;
CAPRI's 2017 results: dairy 42.8 kg in Germany, 10.9 in France, sows 8.9-11.5), and CO2 from 600 kg of limestone on
every arable hectare and from 30% of mineral N as urea at 0.2 kg CO2 per kg N.

CAPRI (envind/gases.gms, supply/supply_model.gms):
  CH4MAN, CH4ENT   per activity and region (kg CH4 per CAPRI unit); per model head: CAPRI total LEVL x item over the
                   region's CAPRI activities / the model's census herd (tools/build/build_livestock_output_coef.build, as
                   manure N, revenue and costs);
  CO2LIM           one coefficient per ha of every crop activity, the region's UAAR CO2LIM (kg CO2/ha; gases.gms
                   (16): "kg lime emissions per ha equally distributed to crop and grassland");
  CO2UREA          mineral N x the member state's urea share of mineral N (FracUseFert 'ureum') x 44/28 (gases.gms
                   l. 833): the share is CAPRI's FracUseFert as its simulation loads it (envind/ammo.gms l. 285-290, 535;
                   capri_data/2017/abatement/ammonia/FracUseFert.csv, build_ammonia_tech_inputs.py). Checked on CAPRI's
                   Green Deal 2030 result: its CO2UREA equals mineral N x this share x 44/28 in every country (KNOWN_ISSUES
                   K93). Before 29 October 2026 the share was recovered from CAPREG's 2017 results (CO2UREA / NMIN /
                   (44/28)), CAPREG's base-year share, which differs (CZ 0.116 against 0.016).
Outputs:
  capri_data/2017/environment/livestock_ch4man_coef.csv, livestock_ch4ent_coef.csv  (region x animal, kg CH4/head)
  capri_data/2017/environment/crop_co2_coef.csv  (region, co2lim_kg_ha, urea_share)

    python tools/build/build_ghg_coefs_2017.py [dump dir]
"""
from __future__ import annotations
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from _model_regions import CTRY as MS_CODE  # noqa: E402  CAPRI member-state codes (capri_member_state_codes.csv)
sys.path.insert(0, str(ROOT)); sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
ENV = ROOT / "capri_data" / "2017" / "environment"
FRAC_USE_FERT = ROOT / "capri_data" / "2017" / "abatement" / "ammonia" / "FracUseFert.csv"


def main(dump: Path):
    import build_livestock_output_coef as L
    import build_capri_base as B
    for item, name in (("CH4MAN", "livestock_ch4man_coef.csv"), ("CH4ENT", "livestock_ch4ent_coef.csv")):
        t = L.build(dump, item)
        t.to_csv(ENV / name)
        print(name, t.shape, "median kg/head:", t.median().round(2).to_dict())
    # CO2LIM per region (UAAR); the urea share per member state is CAPRI's FracUseFert
    import re
    row = re.compile(r"'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z]+)'\.'([A-Z0-9]+)'\.'Y'\s+([^,\s]+)")
    cap: dict = defaultdict(lambda: defaultdict(dict))
    for path in sorted(dump.glob("res_17*.txt")):
        for line in open(path, errors="ignore"):
            m = row.match(line)
            if m and m.group(3) in ("LEVL", "CO2LIM"):
                cap[m.group(1)][m.group(3)][m.group(2)] = B._num(m.group(4))
    fuf = _read_csv(FRAC_USE_FERT)
    share = {r[:2]: float(v) for r, f, v in zip(fuf["region"], fuf["fertiliser"], fuf["value"])
             if str(f).lower() == "ureum" and str(r).endswith("000000")}
    areas = _read_csv(B.AREAS, index_col=0)
    spec = B.build_spec(cap, list(areas.index))
    rows = []
    for reg in areas.index:
        ms = MS_CODE.get(reg[:2], reg[:2])
        src = spec.get(reg) or ((ms + "000000", 1.0),)
        w = sum(wt * cap.get(c, {}).get("LEVL", {}).get("UAAR", 0.0) for c, wt in src)
        lim = (sum(wt * cap.get(c, {}).get("LEVL", {}).get("UAAR", 0.0) * cap.get(c, {}).get("CO2LIM", {}).get("UAAR", 0.0)
                   for c, wt in src) / w) if w > 0 else cap.get(ms + "000000", {}).get("CO2LIM", {}).get("UAAR", 0.0)
        rows.append((reg, lim, share.get(ms, 0.0)))
    out = pd.DataFrame(rows, columns=["region", "co2lim_kg_ha", "urea_share"]).set_index("region")
    out.to_csv(ENV / "crop_co2_coef.csv")
    print("crop_co2_coef.csv:", out.describe().round(3).loc[["min", "50%", "max"]].to_dict())


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/claude/work/capreg"))
