"""CAPRI's two-intensity cattle fattening activities, per model region: bulls BULL/BULH and fattening
heifers HEIL/HEIH (Sprint 7c; dairy cows DCOL/DCOH are in tools/build_dairy_intensity.py).

CAPRI fattens young bulls and heifers in a low- and a high-intensity activity (res_17: equal numbers at
base). They differ in fattening length (DAYS: DE94 bulls 173 vs 270 days, heifers 78 vs 223), slaughter
weight (BEEF per animal 281 vs 422 kg), daily feed needs and manure; each animal takes one young animal
(IBUL, IHEI). The model has one BULL (CAPRI's BULF aggregate) and one HFRS (HEIF + replacement heifers
HEIR) in census heads, i.e. stalls occupied over the year. The split is represented by the stalls moved
from the high to the low activity, z (1000 model heads), as for the dairy split:

  per stall-year, an activity with fattening length D turns over 365 / D animals, so
    flow items (MANN manure N, BEEF, the young animal IBUL/IHEI) per stall = per animal x 365 / D
    daily items (ENNE energy, CRPR protein, DRMN / DRMX dry-matter limits) per stall = per day
  d<item>_rel = (low - high) per stall / the model animal's average per stall (all its CAPRI
               activities: for HFRS including the replacement heifers HEIR)
  share_low, share_high   stall shares of the two activities in the model animal (HFRS: < 1 together)
  q_z        curvature in z from CAPRI's own PMP terms (p_pmpQuadTechn, per CAPRI animal):
             (q_low (365 / (rho D_low))^2 + q_high (365 / (rho D_high))^2), rho = model heads per
             CAPRI stall (the model's census heads over CAPRI's stalls, LEVL x DAYS / 365)

Sources: CAPRI 2017 results res_17<MS>.txt; capri_data/sources/capreg/pmp_quad_techn.csv. Regions take
their CAPRI region through tools/_model_regions.py (splits and merges), else the national row.
Output: capri_data/2017/supply/cattle_intensity.csv (region, animal, ...)

    python tools/build_cattle_intensity.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ("LEVL", "DAYS", "MANN", "BEEF", "IBUL", "IHEI", "ENNE", "CRPR", "DRMN", "DRMX")
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'(BULL|BULH|HEIL|HEIH|HEIR)'\.'(" + "|".join(ITEMS)
                 + r")'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")
SPLITS = {"BULL": ("BULL", "BULH", (), "IBUL"), "HFRS": ("HEIL", "HEIH", ("HEIR",), "IHEI")}
FLOW = ("MANN", "BEEF", "YOUNG")
DAILY = ("ENNE", "CRPR", "DRMN", "DRMX")


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
    to_c8 = mr.region_to_capri()
    import sys
    sys.path.insert(0, str(ROOT))
    from capri_mod.data.loaders import load_all_data
    herds = load_all_data(str(ROOT / "capri_data"))["animal_numbers"]
    q = pd.read_csv(ROOT / "capri_data" / "sources" / "capreg" / "pmp_quad_techn.csv")
    q = q.pivot_table(index="model_region", columns="activity", values="value")

    def stall(d, act, young):
        L, D = d.get((act, "LEVL"), 0.0), d.get((act, "DAYS"), 0.0)
        if L <= 0 or D <= 0:
            return None
        t = 365.0 / D
        rec = {"stalls": L * D / 365.0, "days": D}
        for it in ("MANN", "BEEF"):
            rec[it] = d.get((act, it), 0.0) * t
        rec["YOUNG"] = d.get((act, young), 0.0) / 1000.0 * t        # young animals per stall-year
        for it in DAILY:
            rec[it] = abs(d.get((act, it), 0.0))
        return rec

    rows = []
    for reg in herds.index:
        for animal, (lo, hi, others, young) in SPLITS.items():
            H = float(herds.at[reg, animal]) if animal in herds.columns else 0.0
            if not H > 0:
                continue
            src = None
            for c in (to_c8.get(reg), mr.national_code(reg)):
                if c and c in v and stall(v[c], lo, young) and stall(v[c], hi, young):
                    src = c
                    break
            if src is None:
                continue
            d = v[src]
            recs = {x: stall(d, x, young) for x in (lo, hi) + others}
            recs = {x: r for x, r in recs.items() if r}
            S = sum(r["stalls"] for r in recs.values())
            avg = {it: sum(r[it] * r["stalls"] for r in recs.values()) / S for it in FLOW + DAILY}
            rec = {"region": reg, "animal": animal, "capri_region": src,
                   "share_low": recs[lo]["stalls"] / S, "share_high": recs[hi]["stalls"] / S,
                   "days_low": recs[lo]["days"], "days_high": recs[hi]["days"]}
            ok = True
            for it in FLOW + DAILY:
                if avg[it] <= 0:
                    ok = False
                    break
                rec[f"d{it.lower()}_rel"] = (recs[lo][it] - recs[hi][it]) / avg[it]
            if not ok:
                continue
            rho = H / S                                              # model heads per CAPRI stall
            ql = q.at[reg, lo] if reg in q.index and lo in q.columns else float("nan")
            qh = q.at[reg, hi] if reg in q.index and hi in q.columns else float("nan")
            rec["q_z"] = (ql * (365.0 / (rho * recs[lo]["days"])) ** 2
                          + qh * (365.0 / (rho * recs[hi]["days"])) ** 2)
            rec["q_source"] = "CAPRI p_pmpQuadTechn"
            rec["heads"] = H
            rows.append(rec)
    out = pd.DataFrame(rows)
    # regions without CAPRI's own PMP terms: the country's median of q_z x heads over the region's
    # heads (REGISTERED fallback, as for the dairy and grassland splits)
    out["ms"] = [mr.national_code(r)[:2] for r in out["region"]]
    for animal in SPLITS:
        sel = out["animal"] == animal
        k = (out.loc[sel, "q_z"] * out.loc[sel, "heads"])
        med_ms = k.groupby(out.loc[sel, "ms"]).median()
        med_eu = float(k.median())
        for i in out.index[sel & ~(out["q_z"] > 0)]:
            km = med_ms.get(out.at[i, "ms"])
            km = med_eu if km is None or km != km else km
            out.at[i, "q_z"] = km / out.at[i, "heads"]
            out.at[i, "q_source"] = "country median of q x heads (REGISTERED fallback)"
    out = out.drop(columns=["ms"])
    dest = ROOT / "capri_data" / "2017" / "supply" / "cattle_intensity.csv"
    out.to_csv(dest, index=False, float_format="%.6g")
    for animal in SPLITS:
        s = out[out["animal"] == animal]
        print(f"{animal}: {len(s)} regions ({int((s.q_source == 'CAPRI p_pmpQuadTechn').sum())} own PMP terms); "
              f"low share median {s.share_low.median():.2f}; per stall low-high/avg median: beef {s.dbeef_rel.median():+.2f}, "
              f"manure N {s.dmann_rel.median():+.2f}, young {s.dyoung_rel.median():+.2f}, energy {s.denne_rel.median():+.2f}")
    print(f"wrote {dest.name}")


if __name__ == "__main__":
    main()
