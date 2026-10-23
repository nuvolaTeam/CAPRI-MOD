"""CAPRI's oilseed crushing per model trade region: capri_data/2017/market/crushing_parameters.csv.

Per (trade region, seed) for rapeseed, sunflower and soybeans, from CAPRI's FAO_agg base period (FAO_agg_17_defaulta
p_dataMarket, 'BAS'): crush = the seed's industrial use (INDM), oil and cake yields = their production (MAPR) / crush,
and the crushing elasticity p_ElasProc(r, seed, seed, 'CAL') (elas_2_1717defaulta). CAPRI regions that the model does
not trade separately are summed into ROW (tools/build/recalibrate_trade_2017.REGION_MAP; the 44 trading regions of
sources/capri_trade_regions_2017.json, without the EU), their elasticity the crush-weighted mean of the members'.

EU27: the sums over CAPRI's member states (crush, yields, crush share of domestic use DOMM) and the median of their
p_ElasProc; they reproduce the earlier file's rounded values.

Until 23 October 2026 the file was JSON, held 20 non-EU regions, and pairs whose yields fell outside a plausibility
band (oil + cake > 1.05 t per t, a yield outside 0.1-0.95) were left out. Those regions' oil and cake supply then fell
back to a flat elasticity of 0.10-0.107 (armington_params.csv eps, no CAPRI source). Now every region with CAPRI
crushing data has its row, with CAPRI's yields as they are.

    python tools/build/build_crushing_parameters.py [--fao FILE] [--elas FILE]

Checked on 23 October 2026: it reproduces every pair of the earlier JSON (to its 4-decimal rounding), EU27 included.
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
FAO = Path("/mnt/user-data/uploads/fao_agg_17_datamarket.txt")
ELAS = Path("/mnt/user-data/uploads/elas_2_1717defaulta.csv")
OUT = ROOT / "capri_data" / "2017" / "market" / "crushing_parameters.csv"
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


def read_fao(path: Path, regions):
    rx = re.compile(r"^'([^']+)'\.'(INDM|MAPR)'\.'(RAPE|SUNF|SOYA|RAPO|RAPC|SUNO|SUNC|SOYO|SOYC)'\.'BAS'\s+([-\d.Ee+]+)")
    d = defaultdict(dict)
    with open(path, errors="ignore") as f:
        for line in f:
            if not line.startswith("'"):
                continue
            m = rx.match(line)
            if m and m.group(1) in regions:
                d[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4)) / 1000.0     # t -> kt
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


def build(fao: Path, elas: Path):
    rmap = region_map()
    d = read_fao(fao, set(rmap))
    e = read_elas(elas)
    agg = defaultdict(lambda: defaultdict(float))
    wel = defaultdict(lambda: [0.0, 0.0])
    members = defaultdict(list)
    for c, tr in rmap.items():
        v = d.get(c, {})
        for seed, (oil, cake) in CHAINS.items():
            crush = v.get(("INDM", seed), 0.0)
            if crush <= 0:
                continue
            a = agg[(tr, seed)]
            a["crush"] += crush
            a["oil"] += v.get(("MAPR", oil), 0.0)
            a["cake"] += v.get(("MAPR", cake), 0.0)
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


def eu_build(fao: Path, elas: Path):
    """EU27 rows from CAPRI's member states (capri_member_state_codes.csv without NO and UK): crush = sum of INDM,
    yields = sum of MAPR / crush, crush share of use = crush / sum of DOMM, elasticity = median of the member states'
    p_ElasProc (the market's EU base crush = this share x its aligned EU seed use)."""
    import statistics
    with open(ROOT / "capri_data" / "shared" / "capri_member_state_codes.csv", newline="") as f:
        eu = {r["capri_ms"] for r in csv.DictReader(f) if r["nuts_prefix"] not in ("NO", "GB", "UK")}
    rx = re.compile(r"^'([A-Z]{2}000000)'\.'(INDM|MAPR|DOMM)'\.'(RAPE|SUNF|SOYA|RAPO|RAPC|SUNO|SUNC|SOYO|SOYC)'\.'BAS'\s+([-\d.Ee+]+)")
    d = defaultdict(dict)
    with open(fao, errors="ignore") as f:
        for line in f:
            m = rx.match(line)
            if m and m.group(1) in eu:
                d[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4)) / 1000.0
    e = read_elas(elas)
    rows = []
    for seed, (oil, cake) in CHAINS.items():
        crush = sum(v.get(("INDM", seed), 0.0) for v in d.values())
        dom = sum(v.get(("DOMM", seed), 0.0) for v in d.values())
        els = [e[(ms, seed)] for ms in sorted(eu) if (ms, seed) in e]
        rows.append({"region": "EU27", "seed": seed, "crush_kt": crush,
                     "oil_yield": sum(v.get(("MAPR", oil), 0.0) for v in d.values()) / crush,
                     "cake_yield": sum(v.get(("MAPR", cake), 0.0) for v in d.values()) / crush,
                     "elasticity": statistics.median(els), "elasticity_source": "p_ElasProc median of member states",
                     "crush_share_of_use": crush / dom, "capri_regions": "EU27 member states"})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fao", type=Path, default=FAO)
    ap.add_argument("--elas", type=Path, default=ELAS)
    a = ap.parse_args()
    rows = build(a.fao, a.elas)
    out = eu_build(a.fao, a.elas) + rows
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in out:
            w.writerow({k: (repr(r[k]) if isinstance(r[k], float) else r[k]) for k in COLS})
    print(f"{OUT.name}: {len(out)} pairs ({len(rows)} non-EU)")


if __name__ == "__main__":
    main()
