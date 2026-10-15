"""CAPRI's manure and enteric methane per head and its CO2 from liming and urea, per model region (Sprint 9s;
docs/SYNTHETIC_DATA_AUDIT.md B1-B3, B5).

The accounts used IPCC Tier 1 defaults: one manure-CH4 factor per animal for every region (dairy 16 kg, sows 4.2 kg;
CAPRI's 2017 results: dairy 42.8 kg in Germany, 10.9 in France, sows 8.9-11.5), and CO2 from 600 kg of limestone on
every arable hectare and from 30% of mineral N as urea at 0.2 kg CO2 per kg N.

CAPRI (envind/gases.gms, supply/supply_model.gms):
  CH4MAN, CH4ENT   per activity and region (kg CH4 per CAPRI unit); per model head: CAPRI total LEVL x item over the
                   region's CAPRI activities / the model's census herd (tools/build_livestock_output_coef.build, as
                   manure N, revenue and costs);
  CO2LIM           one coefficient per ha of every crop activity, the region's UAAR CO2LIM (kg CO2/ha; gases.gms
                   (16): "kg lime emissions per ha equally distributed to crop and grassland");
  CO2UREA          mineral N x the member state's urea share of mineral N (FracUseFert 'ureum') x 44/28; the share is
                   recovered from CAPRI's own results: sum LEVL CO2UREA / sum LEVL NMIN / (44/28).
Outputs:
  capri_data/2017/environment/livestock_ch4man_coef.csv, livestock_ch4ent_coef.csv  (region x animal, kg CH4/head)
  capri_data/2017/environment/crop_co2_coef.csv  (region, co2lim_kg_ha, urea_share)

    python tools/build_ghg_coefs_2017.py [dump dir]
"""
from __future__ import annotations
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
ENV = ROOT / "capri_data" / "2017" / "environment"


def main(dump: Path):
    import build_livestock_output_coef as L
    import build_capri_base as B
    for item, name in (("CH4MAN", "livestock_ch4man_coef.csv"), ("CH4ENT", "livestock_ch4ent_coef.csv")):
        t = L.build(dump, item)
        t.round(5).to_csv(ENV / name)
        print(name, t.shape, "median kg/head:", t.median().round(2).to_dict())
    # CO2LIM per region (UAAR) and urea share per member state
    import re
    row = re.compile(r"'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z]+)'\.'([A-Z0-9]+)'\.'Y'\s+([^,\s]+)")
    cap: dict = defaultdict(lambda: defaultdict(dict))
    for path in sorted(dump.glob("res_17*.txt")):
        for line in open(path, errors="ignore"):
            m = row.match(line)
            if m and m.group(3) in ("LEVL", "CO2LIM", "CO2UREA", "NMIN"):
                cap[m.group(1)][m.group(3)][m.group(2)] = B._num(m.group(4))
    areas = pd.read_csv(B.AREAS, index_col=0)
    spec = B.build_spec(cap, list(areas.index))
    share = {}
    for code, it in cap.items():
        if not code.endswith("000000"):
            continue
        num = sum(it["LEVL"].get(a, 0.0) * v for a, v in it.get("CO2UREA", {}).items())
        den = sum(it["LEVL"].get(a, 0.0) * it.get("NMIN", {}).get(a, 0.0) for a in it.get("CO2UREA", {}))
        if den > 0:
            share[code[:2]] = num / den / (44.0 / 28.0)
    rows = []
    for reg in areas.index:
        ms = {"BE": "BL", "LU": "BL", "IE": "IR", "GR": "EL"}.get(reg[:2], reg[:2])
        src = spec.get(reg) or ((ms + "000000", 1.0),)
        w = sum(wt * cap.get(c, {}).get("LEVL", {}).get("UAAR", 0.0) for c, wt in src)
        lim = (sum(wt * cap.get(c, {}).get("LEVL", {}).get("UAAR", 0.0) * cap.get(c, {}).get("CO2LIM", {}).get("UAAR", 0.0)
                   for c, wt in src) / w) if w > 0 else cap.get(ms + "000000", {}).get("CO2LIM", {}).get("UAAR", 0.0)
        rows.append((reg, round(lim, 4), round(share.get(ms, 0.0), 5)))
    out = pd.DataFrame(rows, columns=["region", "co2lim_kg_ha", "urea_share"]).set_index("region")
    out.to_csv(ENV / "crop_co2_coef.csv")
    print("crop_co2_coef.csv:", out.describe().round(3).loc[["min", "50%", "max"]].to_dict())


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/claude/work/capreg"))
