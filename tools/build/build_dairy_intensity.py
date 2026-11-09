"""CAPRI's two dairy-cow activities, low-yield DCOL and high-yield DCOH, per model region.

CAPRI models dairy cows as two activities with their own milk yield, feed requirements, manure N,
costs and PMP terms; at base each holds half the herd (res_17: DCOL LEVL = DCOH LEVL). The model has
one DCOW (their sum) and represents CAPRI's split by the heads moved from DCOH to DCOL, z (1000 heads;
DCOL = s0 x DCOW + z), with per-head changes relative to the average cow (DCOW):

  share_low          s0, DCOL's share of DCOW (LEVL)
  d<item>_rel        (item of DCOL - item of DCOH) / item of DCOW, for COMI (milk), MANN, MANP, MANK (manure
                     N, P2O5, K2O: CAPRI's ManureNPK_ per activity), ENNE (net energy need), CRPR (crude
                     protein need), DRMN, DRMX (dry matter intake limits; DRMX is stored negative by CAPRI,
                     magnitudes used)
  <column>_2030      the same at CAPRI's 2030 calibration point (share_low and the d<item>_rel), from CAPRI's
                     2030 reference the model's 2030 base is taken from (res_2_1730greendeal_refpol_endotech_all_ini,
                     dataOut LEVL at 2030); the model uses them at the 2030 market year (S6 item 6, 9 November 2026:
                     before, the 2017 differences were used at the 2030 point)
  q_low, q_high      CAPRI's own PMP diagonal terms of DCOL and DCOH (p_pmpQuadTechn,
                     capri_data/sources/intermediate/capreg/pmp_quad_techn.parquet); regions without them: the
                     country's median of q x heads over the region's heads (REGISTERED fallback,
                     column q_source), as for the grassland split (tools/build/build_grass_intensity.py)

Calves, cull-cow beef and replacement (YCAM, YCAF, BEEF, ICOW) are the same for both activities.

Sources: CAPRI 2017 results res_17<MS>.txt (DCOL, DCOH, DCOW); CAPRI's 2030 reference
res_2_1730greendeal_refpol_endotech_all_inidefaulta (the _2030 columns). Output:
capri_data/2017/supply/dairy_intensity.csv

    python tools/build/build_dairy_intensity.py [--dump-dir capri_sources/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, json, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from paths import EXPORTS, SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from _grep import grep  # noqa: E402  (grep -E in Python: any system)
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
#: (column suffix, terms per model region): the base year's (CAPREG), CAPRI's 2030 calibration and capri-mod's
#: recipe at 2030 (tools/build/build_intensity_q_2030.py); the model takes the suffix of its PMP source at the 2030 market
#: year (KNOWN_ISSUES K61)
Q_SOURCES = (("", ROOT / "capri_data" / "sources" / "intermediate" / "capreg" / "pmp_quad_techn.parquet"),
             ("_capri2030", ROOT / "capri_data" / "sources" / "intermediate" / "baseline_pmp" / "intensity_q_capri2030.parquet"),
             ("_recipe2030", ROOT / "capri_data" / "sources" / "intermediate" / "baseline_pmp" / "intensity_q_recipe2030.parquet"))
ITEMS = ("LEVL", "COMI", "MANN", "MANP", "MANK", "ENNE", "CRPR", "DRMN", "DRMX")
#: the per-head items whose low-minus-high difference the split carries
REL_ITEMS = ("COMI", "MANN", "MANP", "MANK", "ENNE", "CRPR", "DRMN", "DRMX")
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'(DCOL|DCOH|DCOW)'\.'(" + "|".join(ITEMS)
                 + r")'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")
#: CAPRI's 2030 reference the model's 2030 base comes from (capri_data/scenarios/capri_ref_2030)
REF_2030 = EXPORTS / "res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv"


def read_2030(ref: Path, acts, items) -> dict:
    """{CAPRI region: {(activity, item): value}} of CAPRI's 2030 reference (dataOut, 2030), activities and items
    given."""
    pat = rf"^'[A-Z]{{2}}[0-9A-Z]{{6}}'\.''\.'({'|'.join(acts)})'\.'({'|'.join(items)})'\.'2030'"
    rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'([A-Z]+)'\.'([A-Z]+)'\.'2030'\s+([-\d.Ee+]+)")
    out = defaultdict(dict)
    for line in grep(pat, str(ref)).splitlines():
        m = rx.match(line)
        if m:
            out[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    return out


def split_terms(d: dict):
    """(share_low, {item: (DCOL - DCOH) / DCOW}) of one CAPRI region's records, or None where incomplete."""
    L, Hh = d.get(("DCOL", "LEVL"), 0.0), d.get(("DCOH", "LEVL"), 0.0)
    if L + Hh <= 0 or d.get(("DCOW", "COMI"), 0.0) <= 0:
        return None
    rel = {}
    for it in REL_ITEMS:
        lo, hi, av = (abs(d.get((x, it), 0.0)) for x in ("DCOL", "DCOH", "DCOW"))
        if av <= 0:
            return None
        rel[it] = (lo - hi) / av
    return L / (L + Hh), rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=SOURCES / "capreg")
    ap.add_argument("--ref-2030", type=Path, default=REF_2030)
    a = ap.parse_args()
    v30 = read_2030(a.ref_2030, ("DCOL", "DCOH", "DCOW"), ITEMS)
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
    from capri_mod.data.loaders import load_regional_animal_numbers  # the one table needed (load_all_data read every model input, a dependency cycle in the data pipeline; 29 Oct 2026)
    herds = load_regional_animal_numbers(str(ROOT / "capri_data"))
    Q = {sfx: read_source(f)[lambda d: d["activity"].isin(["DCOL", "DCOH"])].pivot_table(
             index="model_region", columns="activity", values="value") for sfx, f in Q_SOURCES if f.exists()}

    rows = []
    for reg in herds.index:
        H = float(herds.at[reg, "DCOW"]) if "DCOW" in herds.columns else 0.0
        if not H > 0:
            continue
        c8 = to_c8.get(reg)
        src = c8 if c8 in v and ("DCOL", "COMI") in v[c8] else mr.national_code(reg)
        t17 = split_terms(v.get(src, {}))
        if t17 is None:
            continue
        rec = {"region": reg, "capri_region": src, "share_low": t17[0]}
        rec.update({f"d{it.lower()}_rel": x for it, x in t17[1].items()})
        # CAPRI's 2030 point: the region's own CAPRI unit, else its member state's (as for 2017)
        src30 = c8 if c8 in v30 and ("DCOL", "COMI") in v30[c8] else mr.national_code(reg)
        t30 = split_terms(v30.get(src30, {}))
        if t30 is not None:
            rec["share_low_2030"] = t30[0]
            rec.update({f"d{it.lower()}_rel_2030": x for it, x in t30[1].items()})
        rec["heads_low"] = rec["share_low"] * H
        rec["heads_high"] = (1.0 - rec["share_low"]) * H
        rows.append(rec)
    out = pd.DataFrame(rows).set_index("region")
    out["ms"] = [mr.national_code(r)[:2] for r in out.index]
    for sfx, q in Q.items():
        out["q_low" + sfx] = q["DCOL"].reindex(out.index)
        out["q_high" + sfx] = q["DCOH"].reindex(out.index)
        out["q_source" + sfx] = "CAPRI p_pmpQuadTechn" if sfx != "_recipe2030" else "capri-mod recipe p_pmpQuadTechn"
        for col, hd in (("q_low" + sfx, "heads_low"), ("q_high" + sfx, "heads_high")):
            k = (out[col] * out[hd]).where(out[col].notna())
            med_ms = k.groupby(out["ms"]).median()
            med_eu = float(k.median())
            miss = out[col].isna() & (out[hd] > 0)
            for r in out.index[miss]:
                km = med_ms.get(out.at[r, "ms"])
                km = med_eu if km is None or km != km else km
                out.at[r, col] = km / out.at[r, hd]
                out.at[r, "q_source" + sfx] = "country median of q x heads (REGISTERED fallback)"
    out = out.drop(columns=["ms"])
    # the columns as before S6 item 6 first, then manure P2O5 and K2O, then CAPRI's 2030 point
    new = ["dmanp_rel", "dmank_rel"] + [c for c in out.columns if c.endswith("_2030")]
    out = out[[c for c in out.columns if c not in new] + new]
    dest = ROOT / "capri_data" / "2017" / "supply" / "dairy_intensity.csv"
    out.to_csv(dest)
    print(f"wrote {dest.name}: {len(out)} regions, {int((out.q_source == 'CAPRI p_pmpQuadTechn').sum())} with CAPRI's own "
          f"PMP terms; low-yield share median {out.share_low.median():.2f}; milk low-high / mean median "
          f"{out.dcomi_rel.median():.2f}, manure N {out.dmann_rel.median():.2f}, energy {out.denne_rel.median():.2f}; "
          f"at CAPRI's 2030 point ({int(out.dmann_rel_2030.notna().sum())} regions): milk "
          f"{out.dcomi_rel_2030.median():.2f}, manure N / P2O5 / K2O {out.dmann_rel_2030.median():.2f} / "
          f"{out.dmanp_rel_2030.median():.2f} / {out.dmank_rel_2030.median():.2f}")


if __name__ == "__main__":
    main()
