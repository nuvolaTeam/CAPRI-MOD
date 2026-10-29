"""CAPRI's oilseed crushing per model trade region and market year: capri_data/2017/market/crushing_parameters_<YEAR>.csv.

Per (trade region, seed) for rapeseed, sunflower and soybeans, from CAPRI's market data of the market year (dataOut of
the market model's calibration point: market_base_1717 for 2017, markmarket_greendeal_1730et_base_1717 for 2030):
crush = the seed's processing PROC, oil and cake yields = CAPRI's PRCY (summed over CAPRI regions as sum PROD / sum
PROC), and the crushing elasticity p_ElasProc(r, seed, seed, 'CAL') (elas_2_17<YEAR>defaulta). In CAPRI's data the
processing identity ProcO_ holds (PROD(oil, cake) = PROC(seed) x PRCY; arm/calibrate_market_data.gms l. 72-82 and
1123-1130), so the market's crushing reproduces CAPRI's oil and cake production of the market year. CAPRI regions that
the model does not trade separately are summed into ROW (tools/build/recalibrate_trade_2017.REGION_MAP; the 44 trading
regions of sources/capri_trade_regions_2017.json, without the EU), their elasticity the crush-weighted mean of the
members'.

EU27: the sums over CAPRI's member states (crush, PROD, crush share of domestic use, the use as PROD + IMPORTS - EXPORTS
of the seed) and the median of their p_ElasProc.

Until 30 October 2026 the file was one, crushing_parameters.csv, with the yields of FAO_agg's base period (p_dataMarket
'BAS': INDM, MAPR), the raw data before CAPRI's market calibration: the oils then fell short of CAPRI's production
(Australia's soybean oil yield 0.1776 against CAPRI's 0.1937) and the market's export cap had to absorb it (KNOWN_ISSUES
K106).

Until 23 October 2026 the file was JSON, held 20 non-EU regions, and pairs whose yields fell outside a plausibility
band (oil + cake > 1.05 t per t, a yield outside 0.1-0.95) were left out. Those regions' oil and cake supply then fell
back to a flat elasticity of 0.10-0.107 (armington_params.csv eps, no CAPRI source). Now every region with CAPRI
crushing data has its row, with CAPRI's yields as they are.

    python tools/build/build_crushing_parameters.py --year 2017 --market market_base_1717.txt --elas elas_2_1717defaulta.csv
    python tools/build/build_crushing_parameters.py --year 2030 --market markmarket_greendeal_1730et_base_1717.txt \
        --elas elas_2_1730defaulta.csv
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "capri_data" / "2017" / "market"
CHAINS = {"RAPE": ("RAPO", "RAPC"), "SUNF": ("SUNO", "SUNC"), "SOYA": ("SOYO", "SOYC")}
COLS = ["region", "seed", "crush_kt", "oil_yield", "cake_yield", "elasticity", "elasticity_source", "crush_share_of_use",
        "capri_regions"]


def region_map():
    sp = importlib.util.spec_from_file_location("_rt", ROOT / "tools" / "build" / "recalibrate_trade_2017.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    trading = json.load(open(ROOT / "capri_data" / "sources" / "capri_trade_regions_2017.json"))["trading_regions"]
    out = {}
    for r in trading:
        if r == "EU27yr19":
            continue
        out[r] = m.REGION_MAP.get(r, "ROW")
    return out


def read_market(path: Path, year: str, regions):
    """{CAPRI region: {(item, product): value}} of dataOut(region, '', item, product, year) for PROC, PROD, PRCY,
    IMPORTS, EXPORTS of the seeds, oils and cakes (1000 t; PRCY t per t)."""
    rx = re.compile(r"^'([^']+)'\.''\.'(PROC|PROD|PRCY|IMPORTS|EXPORTS)'\.'(RAPE|SUNF|SOYA|RAPO|RAPC|SUNO|SUNC|SOYO|SOYC)'\."
                    r"'" + year + r"'\s+([-\d.Ee+]+)")
    d = defaultdict(dict)
    with open(path, errors="ignore") as f:
        for line in f:
            if not line.startswith("'"):
                continue
            m = rx.match(line)
            if m and m.group(1) in regions:
                d[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    return d


def read_elas(path: Path):
    rx = re.compile(r"^'([^']+)'\.'(RAPE|SUNF|SOYA)'\.'\2'\.'CAL'\s+([-\d.Ee+]+)")
    e, on = {}, False
    with open(path, errors="ignore") as f:
        for line in f:
            if line.startswith("Parameter "):
                on = line.startswith("Parameter p_ElasProc(")
                continue
            if on:
                m = rx.match(line)
                if m:
                    e[(m.group(1), m.group(2))] = float(m.group(3))
    return e


def build(market: Path, year: str, elas: Path):
    rmap = region_map()
    d = read_market(market, year, set(rmap))
    e = read_elas(elas)
    agg = defaultdict(lambda: defaultdict(float))
    wel = defaultdict(lambda: [0.0, 0.0])
    members = defaultdict(list)
    for c, tr in rmap.items():
        v = d.get(c, {})
        for seed, (oil, cake) in CHAINS.items():
            crush = v.get(("PROC", seed), 0.0)
            if crush <= 0:
                continue
            a = agg[(tr, seed)]
            a["crush"] += crush
            a["oil"] += crush * v.get(("PRCY", oil), 0.0)        # CAPRI's PROD of the oil (ProcO_)
            a["cake"] += crush * v.get(("PRCY", cake), 0.0)
            members[(tr, seed)].append(c)
            if (c, seed) in e:
                wel[(tr, seed)][0] += crush * e[(c, seed)]
                wel[(tr, seed)][1] += crush
    rows = []
    for (tr, seed), a in sorted(agg.items()):
        if a["oil"] <= 0 and a["cake"] <= 0:
            continue
        w = wel.get((tr, seed))
        if not w or w[1] <= 0:
            # CAPRI has no p_ElasProc for the pair: its processing has no price response there (no Hessian terms)
            el, src = 0.0, "none in CAPRI: crush fixed at base"
        else:
            el = w[0] / w[1]
            src = "p_ElasProc region" if len(members[(tr, seed)]) == 1 else "p_ElasProc, crush-weighted mean of the members"
        rows.append({"region": tr, "seed": seed, "crush_kt": a["crush"], "oil_yield": a["oil"] / a["crush"],
                     "cake_yield": a["cake"] / a["crush"], "elasticity": el, "elasticity_source": src,
                     "crush_share_of_use": "", "capri_regions": " ".join(members[(tr, seed)])})
    return rows


def eu_build(market: Path, year: str, elas: Path):
    """EU27 rows from CAPRI's member states (capri_member_state_codes.csv without NO and UK): crush = sum of PROC,
    yields = sum of PROC x PRCY / crush, crush share of use = crush / sum of (PROD + IMPORTS - EXPORTS) of the seed,
    elasticity = median of the member states' p_ElasProc (the market's EU base crush = this share x its aligned EU
    seed use)."""
    import statistics
    with open(ROOT / "capri_data" / "shared" / "capri_member_state_codes.csv", newline="") as f:
        eu = {r["capri_ms"] for r in csv.DictReader(f) if r["nuts_prefix"] not in ("NO", "GB", "UK")}
    d = read_market(market, year, eu)
    e = read_elas(elas)
    rows = []
    for seed, (oil, cake) in CHAINS.items():
        crush = sum(v.get(("PROC", seed), 0.0) for v in d.values())
        dom = sum(v.get(("PROD", seed), 0.0) + v.get(("IMPORTS", seed), 0.0) - v.get(("EXPORTS", seed), 0.0)
                  for v in d.values())
        els = [e[(ms, seed)] for ms in sorted(eu) if (ms, seed) in e]
        rows.append({"region": "EU27", "seed": seed, "crush_kt": crush,
                     "oil_yield": sum(v.get(("PROC", seed), 0.0) * v.get(("PRCY", oil), 0.0) for v in d.values()) / crush,
                     "cake_yield": sum(v.get(("PROC", seed), 0.0) * v.get(("PRCY", cake), 0.0) for v in d.values()) / crush,
                     "elasticity": statistics.median(els), "elasticity_source": "p_ElasProc median of member states",
                     "crush_share_of_use": crush / dom, "capri_regions": "EU27 member states"})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["2017", "2030"])
    ap.add_argument("--market", type=Path, required=True)
    ap.add_argument("--elas", type=Path, required=True)
    a = ap.parse_args()
    rows = build(a.market, a.year, a.elas)
    out = eu_build(a.market, a.year, a.elas) + rows
    OUT = OUT_DIR / f"crushing_parameters_{a.year}.csv"
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in out:
            w.writerow({k: (repr(r[k]) if isinstance(r[k], float) else r[k]) for k in COLS})
    print(f"{OUT.name}: {len(out)} pairs ({len(rows)} non-EU)")


if __name__ == "__main__":
    main()
