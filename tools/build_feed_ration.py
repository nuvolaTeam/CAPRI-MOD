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

    python tools/build_feed_ration.py [--dump-dir DIR]
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

FEEDS = ["FGRA", "FMAI", "FOFA", "FROO", "FCOM", "FSGM", "FSTR", "FCER",
         "FPRO", "FENE", "FMIL", "FOTH", "FRMI", "FPRI", "FENI"]
CAPRI_TO_MODEL = {
    "DCOL": "DCOW", "DCOH": "DCOW", "SCOW": "BCOW", "BULF": "BULL",
    "HEIF": "HFRS", "HEIR": "HFRS", "CAMF": "CALV", "CAFF": "CALV",
    "CAMR": "CALV", "CAFR": "CALV", "SOWS": "PIGS", "PIGF": "PIGS",
    "HENS": "LAYS", "POUF": "BROI", "SHGM": "SHGP", "SHGF": "SHGP",
}
# value: a number starting with a digit or minus, or GAMS's Eps (read as 0) -
# a bare [-\d.Ee+]+ matched the 'E' of 'Eps' and crashed the conversion
#: CAPRI PMP activities -> model animal; HEIL/HEIH (fattening heifers by
#: intensity) have no herd split in the regional results, so their mean slope
#: applies to HEIF's ration (REGISTERED)
PMP_ACTS = {"DCOL": "DCOW", "DCOH": "DCOW", "SCOW": "BCOW", "BULL": "BULL", "BULH": "BULL",
            "HEIR": "HFRS", "HEIF": "HFRS", "CAMF": "CALV", "CAFF": "CALV", "CAMR": "CALV",
            "CAFR": "CALV", "SOWS": "PIGS", "PIGF": "PIGS", "HENS": "LAYS", "POUF": "BROI",
            "SHGM": "SHGP", "SHGF": "SHGP"}
ROW = re.compile(r"^'([^']+)'\.'([^']+)'\.'([^']+)'\.'Y'\s+(-?\d[\d.Ee+\-]*|[Ee][Pp][Ss])")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    ap.add_argument("--pmp-dir", type=Path, default=Path("/home/claude/work/feedexp/feed_export"),
                    help="gdxdump CSVs of p_pmpFeedInpCoeff (pmppar_17XX_feedpmp.csv)")
    args = ap.parse_args()

    from capri_mod.data.loaders import load_all_data
    herds = load_all_data(str(_ROOT / "capri_data"))["animal_numbers"]
    corr = json.loads((_ROOT / "capri_data" / "shared" /
                       "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]

    def to_model(code8):
        for cand in corr.get(code8, []):
            if cand in herds.index:
                return cand
        return None

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
        for rr in (r8, r8[:2] + "000000"):
            if (nut, feed) in cont.get(rr, {}):
                return cont[rr][(nut, feed)]
        return None

    tot = collections.defaultdict(lambda: collections.defaultdict(float))
    reg8 = {}
    for (r8, a), d in anim.items():
        if r8.endswith("000000"):
            continue                               # regional rows only
        reg = to_model(r8)
        lv, days = d.get("LEVL", 0.0), d.get("DAYS", 0.0)
        if reg is None or lv <= 0 or days <= 0:
            continue
        key = (reg, CAPRI_TO_MODEL[a])
        reg8[reg] = r8
        for f in FEEDS:
            tot[key]["ration_" + f] += lv * d.get(f, 0.0)
        for q in ("ENNE", "CRPR"):
            tot[key]["req_" + q] += lv * d.get(q, 0.0) * days
        tot[key]["req_DMIN"] += lv * d.get("DRMN", 0.0) * days
        tot[key]["req_DMAX"] += lv * abs(d.get("DRMX", 0.0)) * days

    # NATIONAL REMAINDER, as in build_livestock_output_coef.py: where CAPRI
    # reports a member state's animals only nationally (or regional rows do
    # not cover all model regions), the national total minus the regional sums
    # is spread over the model regions of that member state that have no
    # regional row, per head of their herds.
    PREFIX = {"BL": ("BE", "LU"), "IR": ("IE",)}
    nat = collections.defaultdict(lambda: collections.defaultdict(float))
    for (r8, a), d in anim.items():
        if not r8.endswith("000000"):
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
        prefixes = PREFIX.get(cc, (cc,))
        regs = [r for r in herds.index if r[:2] in prefixes]
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
                rec["capri_slope"] = slopes
                n_sl += 1
    print(f"CAPRI feed-PMP slopes attached to {n_sl} region x animal entries")

    dest = _ROOT / "capri_data" / "2017" / "feed" / "feed_ration_2017.json"
    dest.write_text(json.dumps({
        "_source": "CAPRI 2017 regional results (res_17*, dataOut): rations, requirements per day x DAYS, "
                   "nutrient contents and unit values; per head = CAPRI total / this model's herd. capri_slope: CAPRI's "
                   "feed-PMP slopes (pmppar_17* p_pmpFeedInpCoeff SLOP, sign-converted to a cost slope), aggregated to "
                   "the model animal",
        "_units": "ration kg/head/yr; req per head per yr (ENNE energy units, CRPR kg, DMIN/DMAX kg dry matter); "
                  "content per kg fresh feed; price EUR/kg",
        "regions": out}, indent=1))
    n = sum(len(v) for v in out.values())
    print(f"wrote {dest}: {len(out)} regions, {n} region x animal entries; skipped (missing contents): {len(gaps)}")


if __name__ == "__main__":
    main()
