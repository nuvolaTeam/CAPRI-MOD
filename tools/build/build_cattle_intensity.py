"""CAPRI's two-intensity cattle fattening activities, per model region: bulls BULL/BULH and fattening
heifers HEIL/HEIH (Sprint 7c; dairy cows DCOL/DCOH are in tools/build/build_dairy_intensity.py).

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
their CAPRI region through tools/lib/_model_regions.py (splits and merges), else the national row.
Output: capri_data/2017/supply/cattle_intensity.csv (region, animal, ...)

    python tools/build/build_cattle_intensity.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
#: (column suffix, terms per model region): the base year's (CAPREG), CAPRI's 2030 calibration and capri-mod's
#: recipe at 2030 (tools/build/build_intensity_q_2030.py); the model takes the suffix of its PMP source at the 2030 market
#: year (KNOWN_ISSUES K61)
Q_SOURCES = (("", ROOT / "capri_data" / "sources" / "capreg" / "pmp_quad_techn.csv"),
             ("_capri2030", ROOT / "capri_data" / "sources" / "baseline_pmp" / "intensity_q_capri2030.csv"),
             ("_recipe2030", ROOT / "capri_data" / "sources" / "baseline_pmp" / "intensity_q_recipe2030.csv"))
ITEMS = ("LEVL", "DAYS", "MANN", "BEEF", "IBUL", "IHEI", "ICAM", "ICAF", "YBUL", "YHEI", "YCOW",
         "ENNE", "CRPR", "DRMN", "DRMX")
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'(BULL|BULH|HEIL|HEIH|HEIR|CAMF|CAFF|CAMR|CAFR)'\.'(" + "|".join(ITEMS)
                 + r")'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")
#: (model animal, split, member a (+z), member b (-z), the model animal's CAPRI members, young items it buys).
#: "int": the intensity pairs (Sprint 7c); "rep": the replacement heifers HEIR against the high-intensity fattening
#: heifers (HEIR produces replacement cows YCOW instead of beef); "male" / "female": fattening calves (veal) against
#: raising calves (young bulls / heifers sold, YBUL / YHEI), per sex, and "sex": male against female raising calves
#: (22 October 2026: every CAPRI cattle activity with its own level; the young-animal markets per sex, as CAPRI's).
SPLITS = (("BULL", "int", "BULL", "BULH", ("BULL", "BULH"), ("IBUL",)),
          ("HFRS", "int", "HEIL", "HEIH", ("HEIL", "HEIH", "HEIR"), ("IHEI",)),
          ("HFRS", "rep", "HEIR", "HEIH", ("HEIL", "HEIH", "HEIR"), ("IHEI",)),
          ("CALV", "male", "CAMF", "CAMR", ("CAMF", "CAFF", "CAMR", "CAFR"), ("ICAM", "ICAF")),
          ("CALV", "female", "CAFF", "CAFR", ("CAMF", "CAFF", "CAMR", "CAFR"), ("ICAM", "ICAF")),
          ("CALV", "sex", "CAMR", "CAFR", ("CAMF", "CAFF", "CAMR", "CAFR"), ("ICAM", "ICAF")))
FLOW = ("MANN", "BEEF", "YOUNG")
DAILY = ("ENNE", "CRPR", "DRMN", "DRMX")
#: the model's young-animal goods (tools/build/build_young_animals.py): CAPRI items produced / used per animal
GOODS_PROD = {"young_m": ("YBUL",), "young_f": ("YHEI",), "cows": ("YCOW",)}
GOODS_USE = {"calves_m": ("ICAM",), "calves_f": ("ICAF",), "young_m": ("IBUL",), "young_f": ("IHEI",)}


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
    to_c8 = mr.region_to_capri()
    import sys
    sys.path.insert(0, str(ROOT))
    from capri_mod.data.loaders import load_all_data
    herds = load_all_data(str(ROOT / "capri_data"))["animal_numbers"]
    Q = {sfx: pd.read_csv(f).pivot_table(index="model_region", columns="activity", values="value")
         for sfx, f in Q_SOURCES if f.exists()}

    def stall(d, act, young):
        L, D = d.get((act, "LEVL"), 0.0), d.get((act, "DAYS"), 0.0)
        if L <= 0 or D <= 0:
            return None
        t = 365.0 / D
        rec = {"stalls": L * D / 365.0, "days": D}
        for it in ("MANN", "BEEF"):
            rec[it] = d.get((act, it), 0.0) * t
        rec["YOUNG"] = sum(d.get((act, y), 0.0) for y in young) / 1000.0 * t    # young animals per stall-year
        for g, its in GOODS_PROD.items():
            rec["P_" + g] = sum(d.get((act, y), 0.0) for y in its) / 1000.0 * t
        for g, its in GOODS_USE.items():
            rec["U_" + g] = sum(d.get((act, y), 0.0) for y in its) / 1000.0 * t
        for it in DAILY:
            rec[it] = abs(d.get((act, it), 0.0))
        return rec

    rows = []
    for reg in herds.index:
        for animal, split, lo, hi, members, young in SPLITS:
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
            recs = {x: stall(d, x, young) for x in members}
            recs = {x: r for x, r in recs.items() if r}
            S = sum(r["stalls"] for r in recs.values())
            extra = tuple("P_" + g for g in GOODS_PROD) + tuple("U_" + g for g in GOODS_USE)
            avg = {it: sum(r[it] * r["stalls"] for r in recs.values()) / S for it in FLOW + DAILY + extra}
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
            for sfx, q in Q.items():
                ql = q.at[reg, lo] if reg in q.index and lo in q.columns else float("nan")
                qh = q.at[reg, hi] if reg in q.index and hi in q.columns else float("nan")
                rec["q_z" + sfx] = (ql * (365.0 / (rho * recs[lo]["days"])) ** 2
                                    + qh * (365.0 / (rho * recs[hi]["days"])) ** 2)
                rec["q_source" + sfx] = ("CAPRI p_pmpQuadTechn" if sfx != "_recipe2030"
                                         else "capri-mod recipe p_pmpQuadTechn")
                # the shared member's own curvature: the cross term between two splits of the animal that move
                # stalls out of the same member (HFRS int and rep both out of HEIH)
                rec["q_b" + sfx] = qh * (365.0 / (rho * recs[hi]["days"])) ** 2
                if sfx == "":
                    rec["heads"] = H
            rec.update({"split": split, "member_low": lo, "member_high": hi})
            for g in GOODS_PROD:
                k = "P_" + g
                rec[f"dprod_{g}_rel"] = (recs[lo][k] - recs[hi][k]) / avg[k] if avg[k] > 0 else 0.0
            for g in GOODS_USE:
                k = "U_" + g
                rec[f"duse_{g}_rel"] = (recs[lo][k] - recs[hi][k]) / avg[k] if avg[k] > 0 else 0.0
            rows.append(rec)
    out = pd.DataFrame(rows)
    # regions without CAPRI's own PMP terms: the country's median of q_z x heads over the region's
    # heads (REGISTERED fallback, as for the dairy and grassland splits)
    out["ms"] = [mr.national_code(r)[:2] for r in out["region"]]
    for sfx in Q:
        for animal, split, *_ in SPLITS:
            sel = (out["animal"] == animal) & (out["split"] == split)
            qz, qb = "q_z" + sfx, "q_b" + sfx
            own = sel & (out[qz] > 0) & (out[qb] > 0)
            k = (out.loc[sel, qz] * out.loc[sel, "heads"])
            med_ms = k.groupby(out.loc[sel, "ms"]).median()
            med_eu = float(k.median())
            # the giving-up activity's part of q_z, from the regions with their own terms (country, else EU median)
            fr = (out.loc[own, qb] / out.loc[own, qz])
            fr_ms = fr.groupby(out.loc[own, "ms"]).median()
            fr_eu = float(fr.median()) if len(fr) else 0.5
            for i in out.index[sel & ~((out[qz] > 0) & (out[qb] > 0))]:
                km = med_ms.get(out.at[i, "ms"])
                km = med_eu if km is None or km != km else km
                f_ = fr_ms.get(out.at[i, "ms"])
                f_ = fr_eu if f_ is None or f_ != f_ else f_
                out.at[i, qz] = km / out.at[i, "heads"]
                out.at[i, qb] = f_ * out.at[i, qz]
                out.at[i, "q_source" + sfx] = "country median of q x heads (REGISTERED fallback)"
    out = out.drop(columns=["ms"])
    # the base year's columns first, as before the 2030 columns were added
    base_cols = ["region", "animal", "capri_region", "share_low", "share_high", "days_low", "days_high"] + \
        [f"d{it.lower()}_rel" for it in FLOW + DAILY] + ["q_z", "q_source", "heads"]
    first = base_cols + [c for c in out.columns if c not in base_cols
                         and not (c.endswith("_capri2030") or c.endswith("_recipe2030"))]
    out = out[first + [c for c in out.columns if c not in first]]
    dest = ROOT / "capri_data" / "2017" / "supply" / "cattle_intensity.csv"
    out.to_csv(dest, index=False, float_format="%.6g")
    for animal, split, *_ in SPLITS:
        s = out[(out["animal"] == animal) & (out["split"] == split)]
        print(f"{animal} {split}: {len(s)} regions ({int((s.q_source == 'CAPRI p_pmpQuadTechn').sum())} own PMP terms); "
              f"low share median {s.share_low.median():.2f}; per stall low-high/avg median: beef {s.dbeef_rel.median():+.2f}, "
              f"manure N {s.dmann_rel.median():+.2f}, young {s.dyoung_rel.median():+.2f}, energy {s.denne_rel.median():+.2f}")
    print(f"wrote {dest.name}")


if __name__ == "__main__":
    main()
