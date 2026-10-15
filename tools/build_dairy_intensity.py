"""CAPRI's two dairy-cow activities, low-yield DCOL and high-yield DCOH, per model region.

CAPRI models dairy cows as two activities with their own milk yield, feed requirements, manure N,
costs and PMP terms; at base each holds half the herd (res_17: DCOL LEVL = DCOH LEVL). The model has
one DCOW (their sum) and represents CAPRI's split by the heads moved from DCOH to DCOL, z (1000 heads;
DCOL = s0 x DCOW + z), with per-head changes relative to the average cow (DCOW):

  share_low          s0, DCOL's share of DCOW (LEVL)
  d<item>_rel        (item of DCOL - item of DCOH) / item of DCOW, for COMI (milk), MANN (manure N),
                     ENNE (net energy need), CRPR (crude protein need), DRMN, DRMX (dry matter
                     intake limits; DRMX is stored negative by CAPRI, magnitudes used)
  q_low, q_high      CAPRI's own PMP diagonal terms of DCOL and DCOH (p_pmpQuadTechn,
                     capri_data/sources/capreg/pmp_quad_techn.csv); regions without them: the
                     country's median of q x heads over the region's heads (REGISTERED fallback,
                     column q_source), as for the grassland split (tools/build_grass_intensity.py)

Calves, cull-cow beef and replacement (YCAM, YCAF, BEEF, ICOW) are the same for both activities.

Source: CAPRI 2017 results res_17<MS>.txt (DCOL, DCOH, DCOW). Output:
capri_data/2017/supply/dairy_intensity.csv

    python tools/build_dairy_intensity.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, json, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ("LEVL", "COMI", "MANN", "ENNE", "CRPR", "DRMN", "DRMX")
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'(DCOL|DCOH|DCOW)'\.'(" + "|".join(ITEMS)
                 + r")'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")


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
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    corr = json.loads((ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    import importlib.util as _ilu_
    _sp_ = _ilu_.spec_from_file_location("_mr_", ROOT / "tools" / "_model_regions.py")
    _mr_ = _ilu_.module_from_spec(_sp_); _sp_.loader.exec_module(_mr_)
    to_c8 = _mr_.region_to_capri()          # correspondence + NUTS splits and merges (tools/_model_regions.py)
    import sys
    sys.path.insert(0, str(ROOT))
    from capri_mod.data.loaders import load_all_data
    herds = load_all_data(str(ROOT / "capri_data"))["animal_numbers"]
    q = pd.read_csv(ROOT / "capri_data" / "sources" / "capreg" / "pmp_quad_techn.csv")
    q = q[q["activity"].isin(["DCOL", "DCOH"])].pivot_table(index="model_region", columns="activity", values="value")

    rows = []
    for reg in herds.index:
        H = float(herds.at[reg, "DCOW"]) if "DCOW" in herds.columns else 0.0
        if not H > 0:
            continue
        c8 = to_c8.get(reg)
        src = c8 if c8 in v and ("DCOL", "COMI") in v[c8] else mr.national_code(reg)
        d = v.get(src, {})
        L, Hh = d.get(("DCOL", "LEVL"), 0.0), d.get(("DCOH", "LEVL"), 0.0)
        if L + Hh <= 0 or d.get(("DCOW", "COMI"), 0.0) <= 0:
            continue
        rec = {"region": reg, "capri_region": src, "share_low": L / (L + Hh)}
        ok = True
        for it in ("COMI", "MANN", "ENNE", "CRPR", "DRMN", "DRMX"):
            lo, hi, av = (abs(d.get((x, it), 0.0)) for x in ("DCOL", "DCOH", "DCOW"))
            if av <= 0:
                ok = False
                break
            rec[f"d{it.lower()}_rel"] = (lo - hi) / av
        if not ok:
            continue
        rec["heads_low"] = rec["share_low"] * H
        rec["heads_high"] = (1.0 - rec["share_low"]) * H
        rows.append(rec)
    out = pd.DataFrame(rows).set_index("region")
    out["q_low"] = q["DCOL"].reindex(out.index)
    out["q_high"] = q["DCOH"].reindex(out.index)
    out["q_source"] = "CAPRI p_pmpQuadTechn"
    out["ms"] = [mr.national_code(r)[:2] for r in out.index]
    for col, hd in (("q_low", "heads_low"), ("q_high", "heads_high")):
        k = (out[col] * out[hd]).where(out[col].notna())
        med_ms = k.groupby(out["ms"]).median()
        med_eu = float(k.median())
        miss = out[col].isna() & (out[hd] > 0)
        for r in out.index[miss]:
            km = med_ms.get(out.at[r, "ms"])
            km = med_eu if km is None or km != km else km
            out.at[r, col] = km / out.at[r, hd]
            out.at[r, "q_source"] = "country median of q x heads (REGISTERED fallback)"
    out = out.drop(columns=["ms"])
    dest = ROOT / "capri_data" / "2017" / "supply" / "dairy_intensity.csv"
    out.to_csv(dest, float_format="%.6g")
    print(f"wrote {dest.name}: {len(out)} regions, {int((out.q_source == 'CAPRI p_pmpQuadTechn').sum())} with CAPRI's own "
          f"PMP terms; low-yield share median {out.share_low.median():.2f}; milk low-high / mean median "
          f"{out.dcomi_rel.median():.2f}, manure N {out.dmann_rel.median():.2f}, energy {out.denne_rel.median():.2f}")


if __name__ == "__main__":
    main()
