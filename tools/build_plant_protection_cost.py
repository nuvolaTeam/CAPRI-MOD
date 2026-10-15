"""CAPRI's plant-protection and other-input costs per hectare, per model region and crop (2017).

CAPRI's pesticide target (pol_input/greendeal/conventional_io.gms) shocks two input rows of every
crop in every EU region: plant protection PLAP by -target and other inputs INPO by +50% at the 50%
target, on the conventional area. The model applies the same shocks in EUR per ha, so it needs
both costs per region and crop:

  plap_eur_ha  = PLAP (g of active ingredient per ha, CAPRI's quantity) x UVAG.PLAP (EUR per kg,
                 regional) / 1000. Check: TOIN minus CAPRI's other cost components leaves
                 plant protection (FRH0 soft wheat: 887 - 686 = 201 EUR/ha; PLAP x UVAG: 181)
  inpo_eur_ha  = INPO (EUR/ha)
  fert_eur_ha  = FERT (EUR/ha), the fertiliser cost organic conversion saves (organic_minfert_redu)

They replace the EU-wide shares of input cost (PPP_COST_SHARE, OTHER_COST_SHARE, FERT_COST_SHARE in
the supply module, used by the pesticide and organic instruments) applied to the model's cost per ha, which is CAPRI's TOIN: same concept, now per region.

Mapping: model regions take their CAPRI region (NUTS correspondence), else the national row;
model crops sum CAPRI activities as in tools/build_capri_base.py (CROP_MAP), weighted by CAPRI's
2017 levels; cotton is CAPRI's TEXT in EL, ES and BG.

Source: CAPRI 2017 results res_17<MS>.txt (PLAP, INPO, LEVL per activity; UVAG.PLAP).
Output: capri_data/2017/supply/plant_protection_cost.csv (region, activity, plap_eur_ha, inpo_eur_ha,
fert_eur_ha, capri_region)

    python tools/build_plant_protection_cost.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, json, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Za-z0-9_]+)'\.'(PLAP|INPO|FERT|LEVL)'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    a = ap.parse_args()
    v = defaultdict(dict)            # region -> {(act, item): value}
    for f in glob.glob(str(a.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = ROW.match(line)
            if m:
                v[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    mr = _load(ROOT / "tools" / "_model_regions.py")
    base = _load(ROOT / "tools" / "build_capri_base.py")
    crop_map = dict(base.CROP_MAP)
    corr = json.loads((ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    import importlib.util as _ilu_
    _sp_ = _ilu_.spec_from_file_location("_mr_", ROOT / "tools" / "_model_regions.py")
    _mr_ = _ilu_.module_from_spec(_sp_); _sp_.loader.exec_module(_mr_)
    to_c8 = _mr_.region_to_capri()          # correspondence + NUTS splits and merges (tools/_model_regions.py)

    def cost(src, acts):
        d = v.get(src, {})
        uv = d.get(("UVAG", "PLAP"))
        num_p = num_i = num_f = den = 0.0
        for act in acts:
            L = d.get((act, "LEVL"), 0.0)
            if L <= 0:
                continue
            p, i = d.get((act, "PLAP")), d.get((act, "INPO"))
            if p is None and i is None:
                continue
            den += L
            num_p += L * (p or 0.0) * (uv or 0.0) / 1000.0
            num_i += L * (i or 0.0)
            num_f += L * (d.get((act, "FERT")) or 0.0)
        return (num_p / den, num_i / den, num_f / den) if den > 0 and uv else None

    rows, n_reg, n_nat = [], 0, 0
    for reg in mr.model_regions():
        if reg[:2] == "NO":
            continue                               # EU instrument (EU27yr19)
        for col, acts in list(crop_map.items()) + [("COTT", ("TEXT",))]:
            if col == "COTT" and reg[:2] not in ("EL", "ES", "BG"):
                continue
            for src, kind in ((to_c8.get(reg), "regional"), (mr.national_code(reg), "national")):
                if src and src in v:
                    c = cost(src, acts)
                    if c is not None:
                        rows.append((reg, col, c[0], c[1], c[2], src))
                        n_reg += kind == "regional"; n_nat += kind == "national"
                        break
    out = pd.DataFrame(rows, columns=["region", "activity", "plap_eur_ha", "inpo_eur_ha", "fert_eur_ha", "capri_region"])
    dest = ROOT / "capri_data" / "2017" / "supply" / "plant_protection_cost.csv"
    out.to_csv(dest, index=False, float_format="%.6g")
    med = out.groupby("activity")[["plap_eur_ha", "inpo_eur_ha", "fert_eur_ha"]].median().round(0)
    print(f"wrote {dest.name}: {len(out)} rows, {out.region.nunique()} regions ({n_reg} regional, {n_nat} national cells)")
    print(med.loc[[c for c in ("SWHE", "CORN", "RAPE", "SUGB", "POTA", "APPL", "WINE", "OLIV", "GRAS") if c in med.index]].to_string())


if __name__ == "__main__":
    main()
