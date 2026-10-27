"""CAPRI's two grassland activities, extensive GRAE and intensive GRAI, per model region.

CAPRI models permanent grassland as two activities with their own yields, nutrient needs, costs and
PMP terms; the model has one GRAS (their sum). The model represents CAPRI's split by the area moved
from intensive to extensive grassland, z (1000 ha; z = 0 at base, GRAE = s0 x GRAS + z):

  share_ext      s0, GRAE's share of GRAS area (CAPRI 2017, LEVL)
  yield_ext_rel  GRAE yield / average GRAS yield, yield_int_rel likewise (CAPRI 2017, YILD)
  q_ext, q_int   CAPRI's own PMP diagonal terms of GRAE and GRAI (p_pmpQuadTechn, EUR/ha per 1000 ha;
                 capri_data/sources/capreg/pmp_quad_techn.csv). Regions without them: the country's
                 median of q x area (= margin / elasticity for a constant-elasticity PMP term) over
                 the region's area of the activity (REGISTERED fallback, column q_source)

Moving z ha from GRAI to GRAE changes the PMP cost by (q_ext + q_int) z^2 / 2 (the group terms of
p_pmpQuadPact act on the grassland total, which z does not change).

Source: CAPRI 2017 results res_17<MS>.txt (GRAE, GRAI: LEVL, YILD). Output:
capri_data/2017/supply/grass_intensity.csv

    python tools/build/build_grass_intensity.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, json, re, statistics
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
#: (column suffix, terms per model region): the base year's (CAPREG), CAPRI's 2030 calibration and capri-mod's
#: recipe at 2030 (tools/build/build_intensity_q_2030.py); the model takes the suffix of its PMP source at the 2030 market
#: year (KNOWN_ISSUES K61)
Q_SOURCES = (("", ROOT / "capri_data" / "sources" / "capreg" / "pmp_quad_techn.csv"),
             ("_capri2030", ROOT / "capri_data" / "sources" / "baseline_pmp" / "intensity_q_capri2030.csv"),
             ("_recipe2030", ROOT / "capri_data" / "sources" / "baseline_pmp" / "intensity_q_recipe2030.csv"))
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'(GRAE|GRAI)'\.'(LEVL|YILD)'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    a = ap.parse_args()
    v = defaultdict(dict)
    for f in glob.glob(str(a.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = ROW.match(line)
            if m:
                v[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    import importlib.util as _ilu_
    _sp_ = _ilu_.spec_from_file_location("_mr_", ROOT / "tools" / "lib" / "_model_regions.py")
    _mr_ = _ilu_.module_from_spec(_sp_); _sp_.loader.exec_module(_mr_)
    to_c8 = _mr_.region_to_capri()          # correspondence + NUTS splits and merges (tools/lib/_model_regions.py)
    import sys
    sys.path.insert(0, str(ROOT))
    from capri_mod.data.loaders import load_all_data
    areas = load_all_data(str(ROOT / "capri_data"))["areas"]
    Q = {sfx: _read_csv(f)[lambda d: d["activity"].isin(["GRAE", "GRAI"])].pivot_table(
             index="model_region", columns="activity", values="value") for sfx, f in Q_SOURCES if f.exists()}

    rows = []
    for reg in areas.index:
        G = float(areas.at[reg, "GRAS"]) if "GRAS" in areas.columns else 0.0
        if not G > 0:
            continue
        src = to_c8.get(reg) if to_c8.get(reg) in v else mr.national_code(reg)
        d = v.get(src, {})
        LE, LI = d.get(("GRAE", "LEVL"), 0.0), d.get(("GRAI", "LEVL"), 0.0)
        YE, YI = d.get(("GRAE", "YILD"), 0.0), d.get(("GRAI", "YILD"), 0.0)
        if LE + LI <= 0 or YE <= 0 or YI <= 0:
            continue
        s0 = LE / (LE + LI)
        Ybar = s0 * YE + (1 - s0) * YI
        rows.append({"region": reg, "capri_region": src, "share_ext": s0, "yield_ext_rel": YE / Ybar,
                     "yield_int_rel": YI / Ybar, "area_ext": s0 * G, "area_int": (1 - s0) * G})
    out = pd.DataFrame(rows).set_index("region")
    # fallback: country median of q x area, over the region's area
    out["ms"] = [mr.national_code(r)[:2] for r in out.index]
    for sfx, q in Q.items():
        out["q_ext" + sfx] = q["GRAE"].reindex(out.index)
        out["q_int" + sfx] = q["GRAI"].reindex(out.index)
        out["q_source" + sfx] = "CAPRI p_pmpQuadTechn" if sfx != "_recipe2030" else "capri-mod recipe p_pmpQuadTechn"
        for col, ar in (("q_ext" + sfx, "area_ext"), ("q_int" + sfx, "area_int")):
            k = (out[col] * out[ar]).where(out[col].notna())
            med_ms = k.groupby(out["ms"]).median()
            med_eu = float(k.median())
            miss = out[col].isna() & (out[ar] > 0)
            for r in out.index[miss]:
                km = med_ms.get(out.at[r, "ms"])
                km = med_eu if km is None or km != km else km
                out.at[r, col] = km / out.at[r, ar]
                out.at[r, "q_source" + sfx] = "country median of q x area (REGISTERED fallback)"
    out = out.drop(columns=["ms"])
    dest = ROOT / "capri_data" / "2017" / "supply" / "grass_intensity.csv"
    out.to_csv(dest)
    print(f"wrote {dest.name}: {len(out)} regions, {int((out.q_source == 'CAPRI p_pmpQuadTechn').sum())} with CAPRI's own PMP terms; "
          f"extensive share median {out.share_ext.median():.2f}, yield ext/int median "
          f"{(out.yield_ext_rel / out.yield_int_rel).median():.2f}")


if __name__ == "__main__":
    main()
