"""Build the EU feed-ration data from CAPRI's 2017 regional results.

For each model region and model animal activity (docs/FEED_RATION.md):
  ration   kg of each feed group per head per year  (CAPRI total / our herd)
  req      energy (ENNE) and crude protein (CRPR) per head per year, and the
           dry-matter bounds DMIN/DMAX per head per year (CAPRI per-day values
           x DAYS x LEVL, summed over CAPRI activities, / our herd)
  content  ENNE, CRPR, DRMA per kg of each feed (region row, else member state)
  price    EUR per kg (UVAG / 1000, member state)

Same construction as livestock_revenue_coef / manure / feed per head, so units
and vintage match the herds. Input: the res_17*.txt dumps (dataOut, CAPRI 2017).

    python tools/build/build_feed_ration.py [--dump-dir DIR]

Writes capri_data/2017/feed/feed_ration_2017.csv (region, animal, block, feed, nutrient, value; capri_mod/data/
nested_tables.py; a JSON file until 31 October 2026).
"""
from __future__ import annotations

import argparse
import collections
import glob
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from paths import SOURCES, REFERENCE  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)
import sys as _sys_nc  # noqa: E402
_sys_nc.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "tools" / "lib"))
from _model_regions import national_code as _national_code  # noqa: E402  (TUR for Turkey's units, 4 November 2026)

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

FEEDS = ["FGRA", "FMAI", "FOFA", "FROO", "FCOM", "FSGM", "FSTR", "FCER",
         "FPRO", "FENE", "FMIL", "FOTH", "FRMI", "FPRI", "FENI"]
CAPRI_TO_MODEL = {
    "DCOL": "DCOW", "DCOH": "DCOW", "SCOW": "BCOW", "BULF": "BULL",
    "HEIF": "HFRS", "HEIR": "HFRS", "CAMF": "CALV", "CAFF": "CALV",
    "CAMR": "CALV", "CAFR": "CALV", "SOWS": "PIGS", "PIGF": "PIGF",
    "HENS": "LAYS", "POUF": "BROI", "SHGM": "SHGM", "SHGF": "SHGF",
}
# value: a number starting with a digit or minus, or GAMS's Eps (read as 0) -
# a bare [-\d.Ee+]+ matched the 'E' of 'Eps' and crashed the conversion
#: CAPRI PMP activities -> model animal; HEIL/HEIH (fattening heifers by
#: intensity) have no herd split in the regional results, so their mean slope
#: applies to HEIF's ration (REGISTERED)
PMP_ACTS = {"DCOL": "DCOW", "DCOH": "DCOW", "SCOW": "BCOW", "BULL": "BULL", "BULH": "BULL",
            "HEIR": "HFRS", "HEIF": "HFRS", "CAMF": "CALV", "CAFF": "CALV", "CAMR": "CALV",
            "CAFR": "CALV", "SOWS": "PIGS", "PIGF": "PIGF", "HENS": "LAYS", "POUF": "BROI",
            "SHGM": "SHGM", "SHGF": "SHGF"}
ROW = re.compile(r"^'([^']+)'\.'([^']+)'\.'([^']+)'\.'Y'\s+(-?\d[\d.Ee+\-]*|[Ee][Pp][Ss])")


def _attach_slopes(out, reg8, anim, var, slope_src, key):
    """CAPRI's feed-PMP cost slopes aggregated to the model animal (see the comment in main); returns the count."""
    n_sl = 0
    for reg, acts in out.items():
        r8 = reg8.get(reg)
        if not r8:
            continue
        for act, rec in acts.items():
            members = []
            for a in [k for k, m in PMP_ACTS.items() if m == act]:
                if a in ("BULL", "BULH"):
                    d = var.get((r8, a), {})
                else:
                    d = anim.get((r8, a), {})
                if a == "HEIF":
                    sl = {}
                    for fv in set(slope_src.get((r8, "HEIL"), {})) | set(slope_src.get((r8, "HEIH"), {})):
                        vals = [slope_src[(r8, h)][fv] for h in ("HEIL", "HEIH") if fv in slope_src.get((r8, h), {})]
                        sl[fv] = sum(vals) / len(vals)
                else:
                    sl = slope_src.get((r8, a), {})
                if d.get("LEVL", 0) > 0 and sl:
                    members.append((d, sl))
            if not members:
                continue
            L = sum(d["LEVL"] for d, _ in members)
            slopes = {}
            for f, xm in rec["ration"].items():
                xbar = sum(d["LEVL"] * d.get(f, 0.0) for d, _ in members) / L
                if xbar <= 0 or xm <= 0:
                    continue
                k = xm / xbar
                sv = sum((d["LEVL"] / L) * sl.get(f, 0.0) * (d.get(f, 0.0) / xbar) ** 2 for d, sl in members)
                if sv > 0:
                    slopes[f] = sv / k
            if slopes:
                rec[key] = slopes
                n_sl += 1
    return n_sl


#: CAPRI's PMP activities of each model animal in the 2030 weights (sim_ini's DATA at TRD has the bull and heifer
#: activities by intensity, BULL/BULH and HEIL/HEIH/HEIR, each with its herd; not the BULF and HEIF aggregates)
PMP_ACTS_2030 = {"DCOL": "DCOW", "DCOH": "DCOW", "SCOW": "BCOW", "BULL": "BULL", "BULH": "BULL",
                 "HEIR": "HFRS", "HEIL": "HFRS", "HEIH": "HFRS", "CAMF": "CALV", "CAFF": "CALV", "CAMR": "CALV",
                 "CAFR": "CALV", "SOWS": "PIGS", "PIGF": "PIGF", "HENS": "LAYS", "POUF": "BROI",
                 "SHGM": "SHGM", "SHGF": "SHGF"}


def _tables_2030(path: Path) -> dict:
    """CAPRI's 2030 herds and rations per (CAPRI region, activity): DATA(region, act, LEVL | feed, "TRD") of CAPRI's
    2030 calibration (sim_ini_21730, capri_sources/reference/simini; feed in kg per head, LEVL in 1000 heads)."""
    import gzip
    import csv as _csv
    out = collections.defaultdict(dict)
    with gzip.open(path, "rt", newline="") as fh:
        for row in _csv.DictReader(fh):
            if row["d3"] == "TRD" and row["d1"] in PMP_ACTS_2030 and (row["d2"] == "LEVL" or row["d2"] in FEEDS):
                out[(row["d0"], row["d1"])][row["d2"]] = float(row["value"])
    return out


def _attach_slopes_2030(out, reg8, anim, var, tab30, slope_src, key):
    """CAPRI's 2030 feed-PMP cost slopes aggregated to the model animal with CAPRI's 2030 weights: the same
    aggregation as _attach_slopes, slope = sum_i w_i (-SLOP_i) (x_i / xbar)^2 / k, with w_i the 2030 herd shares and
    x_i the 2030 rations per head of CAPRI's activities (DATA at TRD, _tables_2030), each heifer and bull activity
    with its own slope and herd. k = model ration / xbar stays the 2017 one: the model's 2030 rations are its 2017
    rations times CAPRI's 2030/2017 per-head factor (build_ration_trajectory_2030), which keeps that ratio. Where a
    region has no 2030 rows for any of the animal's activities, the 2017 weights (_attach_slopes); likewise a feed that
    CAPRI's 2030 rations of the animal no longer hold keeps its slope with the 2017 weights (its 2030 ration is then 0
    and the slope unused, but the ration model would otherwise reconstruct one by formula). Returns (entries with
    2030 weights, entries with the 2017 fallback, feed slopes with the 2017 fallback)."""
    n30 = n17 = nf = 0
    for reg, acts in out.items():
        r8 = reg8.get(reg)
        if not r8:
            continue
        for act, rec in acts.items():
            members = [(tab30[(r8, a)], slope_src[(r8, a)]) for a, m in PMP_ACTS_2030.items()
                       if m == act and tab30.get((r8, a), {}).get("LEVL", 0) > 0 and slope_src.get((r8, a))]
            if not members:
                one = {reg: {act: rec}}
                n17 += _attach_slopes(one, reg8, anim, var, slope_src, key)
                continue
            # the 2017 average ration of the animal's CAPRI activities (k's denominator, as _attach_slopes)
            m17 = []
            for a in [k for k, m in PMP_ACTS.items() if m == act]:
                d = var.get((r8, a), {}) if a in ("BULL", "BULH") else anim.get((r8, a), {})
                if d.get("LEVL", 0) > 0:
                    m17.append(d)
            L, L17 = sum(d["LEVL"] for d, _ in members), sum(d["LEVL"] for d in m17)
            tmp = {reg: {act: dict(rec)}}
            _attach_slopes(tmp, reg8, anim, var, slope_src, key)
            fb = tmp[reg][act].get(key, {})                  # the 2017-weighted slopes, per feed
            slopes = {}
            for f, xm in rec["ration"].items():
                xbar = sum(d["LEVL"] * d.get(f, 0.0) for d, _ in members) / L
                xbar17 = sum(d["LEVL"] * d.get(f, 0.0) for d in m17) / L17 if L17 > 0 else 0.0
                if xbar <= 0 or xbar17 <= 0 or xm <= 0:
                    if f in fb:
                        slopes[f] = fb[f]
                        nf += 1
                    continue
                k = xm / xbar17
                sv = sum((d["LEVL"] / L) * sl.get(f, 0.0) * (d.get(f, 0.0) / xbar) ** 2 for d, sl in members)
                if sv > 0:
                    slopes[f] = sv / k
            if slopes:
                rec[key] = slopes
                n30 += 1
    return n30, n17, nf


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=SOURCES / "capreg")
    ap.add_argument("--simini-data", type=Path, default=REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz",
                    help="CAPRI's 2030 calibration data, DATA of sim_ini_21730 (tools/build/build_simini_reference.py)")
    ap.add_argument("--pmp-dir", type=Path, default=SOURCES / "feed_export",
                    help="gdxdump CSVs of p_pmpFeedInpCoeff (pmppar_17XX_feedpmp.csv)")
    args = ap.parse_args()

    from capri_mod.data.loaders import load_regional_animal_numbers  # the one table needed (load_all_data read every model input, a dependency cycle in the data pipeline; 29 Oct 2026)
    herds = load_regional_animal_numbers(str(_ROOT / "capri_data"))

    # CAPRI regions -> model regions in groups covering the same territory (tools/lib/_model_regions.py:
    # splits, merges, renamed regions); a group's CAPRI totals are spread over its model regions by
    # their herds (the first-candidate rule put all of Etelae-Suomi on Uusimaa's herd)
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location("_mr", _ROOT / "tools" / "lib" / "_model_regions.py")
    _mr = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_mr)
    code_to_group, groups = _mr.capri_groups(list(herds.index))

    anim = collections.defaultdict(dict)      # (capri region, capri act) -> item -> value
    var = collections.defaultdict(dict)       # bull variants BULL/BULH (the PMP file splits them)
    cont = collections.defaultdict(dict)      # capri region -> (nutrient, feed) -> value
    for path in sorted(glob.glob(str(args.dump_dir / "res_17*.txt"))):
        for line in open(path, errors="ignore"):
            m = ROW.match(line.strip())
            if not m:
                continue
            r, a, it = m.group(1), m.group(2), m.group(3)
            v = 0.0 if m.group(4).lower() == "eps" else float(m.group(4))
            if a in CAPRI_TO_MODEL and (it in FEEDS or it in ("LEVL", "DAYS", "ENNE", "CRPR", "DRMN", "DRMX")):
                anim[(r, a)][it] = v
            if a in ("BULL", "BULH") and (it in FEEDS or it == "LEVL"):
                var[(r, a)][it] = v
            elif a in ("ENNE", "CRPR", "DRMA", "UVAG") and it in FEEDS:
                cont[r][(a, it)] = v

    def content(r8, nut, feed):
        for rr in (r8, _national_code(r8)):
            if (nut, feed) in cont.get(rr, {}):
                return cont[rr][(nut, feed)]
        return None

    tot = collections.defaultdict(lambda: collections.defaultdict(float))
    reg8 = {}
    for (r8, a), d in anim.items():
        if not _mr.regional_row(r8):
            continue                               # regional rows only (DK000000 ... are units)
        g = code_to_group.get(r8)
        lv, days = d.get("LEVL", 0.0), d.get("DAYS", 0.0)
        if g is None or lv <= 0 or days <= 0:
            continue
        act_m = CAPRI_TO_MODEL[a]
        regs_g = sorted(groups[g][1])
        hg = float(sum(herds.at[r_, act_m] for r_ in regs_g)) if act_m in herds.columns else 0.0
        for reg in regs_g:
            w = float(herds.at[reg, act_m]) / hg if hg > 0 else 1.0 / len(regs_g)
            key = (reg, act_m)
            reg8.setdefault(reg, min(groups[g][0]))
            for f in FEEDS:
                tot[key]["ration_" + f] += w * lv * d.get(f, 0.0)
            for q in ("ENNE", "CRPR"):
                tot[key]["req_" + q] += w * lv * d.get(q, 0.0) * days
            tot[key]["req_DMIN"] += w * lv * d.get("DRMN", 0.0) * days
            tot[key]["req_DMAX"] += w * lv * abs(d.get("DRMX", 0.0)) * days

    # NATIONAL REMAINDER, as in build_livestock_output_coef.py: where CAPRI
    # reports a member state's animals only nationally (or regional rows do
    # not cover all model regions), the national total minus the regional sums
    # is spread over the model regions of that member state that have no
    # regional row, per head of their herds.
    nat = collections.defaultdict(lambda: collections.defaultdict(float))
    for (r8, a), d in anim.items():
        if _mr.regional_row(r8):
            continue
        lv, days = d.get("LEVL", 0.0), d.get("DAYS", 0.0)
        if lv <= 0 or days <= 0:
            continue
        key = (r8[:2], CAPRI_TO_MODEL[a])
        for f in FEEDS:
            nat[key]["ration_" + f] += lv * d.get(f, 0.0)
        for q in ("ENNE", "CRPR"):
            nat[key]["req_" + q] += lv * d.get(q, 0.0) * days
        nat[key]["req_DMIN"] += lv * d.get("DRMN", 0.0) * days
        nat[key]["req_DMAX"] += lv * abs(d.get("DRMX", 0.0)) * days
    for (cc, act), t in nat.items():
        regs = [r for r in herds.index if r[:2] == cc]          # CAPRI's codes (BL, IR)
        covered = [r for r in regs if (r, act) in tot]
        rest = [r for r in regs if (r, act) not in tot and act in herds.columns and herds.at[r, act] > 0]
        if not rest:
            continue
        heads_rest = float(sum(herds.at[r, act] for r in rest))
        if heads_rest <= 0:
            continue
        for item, v in t.items():
            resid = v - sum(tot[(r, act)][item] for r in covered)
            if resid <= 0:
                continue
            for r in rest:
                tot[(r, act)][item] += resid * float(herds.at[r, act]) / heads_rest
        for r in rest:
            reg8.setdefault(r, cc + "000000")

    out, gaps = {}, []
    for (reg, act), t in tot.items():
        heads = float(herds.at[reg, act]) if act in herds.columns else 0.0
        if heads <= 0:
            continue
        r8 = reg8[reg]
        ration = {f: t["ration_" + f] / heads for f in FEEDS if t["ration_" + f] > 0}
        cnt = {f: {n: content(r8, n, f) for n in ("ENNE", "CRPR", "DRMA")} for f in ration}
        if any(v is None for c in cnt.values() for v in c.values()):
            gaps.append(f"{reg}|{act}")
            continue
        price = {f: (content(r8, "UVAG", f) or 0.0) / 1000.0 for f in ration}
        req = {q: t["req_" + q] / heads for q in ("ENNE", "CRPR", "DMIN", "DMAX")}
        out.setdefault(reg, {})[act] = {"ration": ration, "req": req, "content": cnt, "price": price}

    # CAPRI'S OWN FEED-PMP SLOPES (pmppar p_pmpFeedInpCoeff 'SLOP'), aggregated to
    # the model animal. CAPRI adds x*(CNST + 0.5*SLOP*x) to the profit it
    # MAXIMISES (verified: that reading explains marginal feed costs by nutrient
    # prices to a median 4.6% residual, the opposite one 54.5%), so the cost
    # slope is -SLOP. Aggregation, for a ration moving proportionally across the
    # CAPRI activities of a model animal:
    #   slope = sum_i w_i (-SLOP_i) (x_i / xbar)^2 / k,  w_i = LEVL share,
    #   xbar = LEVL-weighted mean ration per CAPRI head, k = model ration / xbar
    import csv
    slope_src = collections.defaultdict(dict)
    for fcsv in glob.glob(str(args.pmp_dir / "pmppar_17*_feedpmp.csv")):
        for row in csv.DictReader(open(fcsv, encoding="utf-8-sig")):
            if "RALL" not in row:
                break
            if row["Dim5"] == "SLOP" and row["A"] == "T":
                slope_src[(row["RALL"], row["MAACT"])][row["FEED"]] = -float(row["Val"])
    # the same slopes of CAPRI's 2030 baseline calibration (pmppar_21730, tools/build/build_pmp_2030.py), aggregated with
    # CAPRI's 2030 weights: its 2030 herds and rations per activity (sim_ini_21730's DATA at TRD; DEP-22 until
    # 5 November 2026, when the 2017 weights were used); used at the 2030 market year with SupplyModule.pmp_source
    # "capri2030" (KNOWN_ISSUES K61)
    # in the model's 2017 money: CAPRI's 2030 slopes over its inflation to 2030 (tools/lib/_money; KNOWN_ISSUES K108,
    # 31 October 2026: before, CAPRI's 2030 money)
    sys.path.insert(0, str(_ROOT / "tools" / "lib"))
    import _money
    _m30 = _money.deflator(2030)
    slope_src_2030 = collections.defaultdict(dict)
    _f30 = _ROOT / "capri_data" / "sources" / "intermediate" / "baseline_pmp" / "pmp_feed_inp_coeff_2030.parquet"
    if _f30.exists():
        for row in source_records(_f30):
            if row["coef"] == "SLOP" and row["tech"] == "T":
                slope_src_2030[(row["region"], row["activity"])][row["feed"]] = -float(row["value"]) / _m30
    if slope_src:
        n_sl = _attach_slopes(out, reg8, anim, var, slope_src, "capri_slope")
        print(f"CAPRI feed-PMP slopes (capri_slope) attached to {n_sl} region x animal entries")
    if slope_src_2030:
        tab30 = _tables_2030(args.simini_data)
        n30, n17, nf = _attach_slopes_2030(out, reg8, anim, var, tab30, slope_src_2030, "capri_slope_2030")
        print(f"CAPRI feed-PMP slopes (capri_slope_2030) attached to {n30 + n17} region x animal entries: {n30} with "
              f"CAPRI's 2030 weights, {n17} with the 2017 weights (no 2030 rows); {nf} feed slopes with the 2017 "
              f"weights (feeds CAPRI's 2030 rations no longer hold)")

    # source: CAPRI 2017 regional results (res_17*, dataOut): rations, requirements per day x DAYS, nutrient contents and
    # unit values; per head = CAPRI total / this model's herd. capri_slope: CAPRI's feed-PMP slopes (pmppar_17*
    # p_pmpFeedInpCoeff SLOP, sign-converted to a cost slope), aggregated to the model animal; capri_slope_2030: the same
    # from CAPRI's 2030 baseline calibration (pmppar_21730), over CAPRI's inflation to 2030 (the model's 2017 money).
    # Units (capri_data/schema/25_feed.sql): ration kg/head/yr; req per head per yr (ENNE energy units, CRPR kg, DMIN/DMAX
    # kg dry matter); content per kg fresh feed; price EUR/kg
    from capri_mod.data.nested_tables import write_feed_rations
    dest = _ROOT / "capri_data" / "2017" / "feed" / "feed_ration_2017.csv"
    write_feed_rations(dest, out)
    n = sum(len(v) for v in out.values())
    print(f"wrote {dest}: {len(out)} regions, {n} region x animal entries; skipped (missing contents): {len(gaps)}")


if __name__ == "__main__":
    main()
