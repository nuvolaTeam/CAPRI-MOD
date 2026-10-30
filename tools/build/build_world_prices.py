"""The model's world market prices of 2017 (EUR/t), every row from its CAPRI source: capri_data/2017/market/world_prices.csv
(this builder its one writer since 29 October 2026). The source of each row (build() returns it with the prices) is summarised in
capri_data/schema/02_provenance_notes.sql; until 30 October 2026 it was also written to
capri_data/sources/world_price_provenance.csv (a JSON file before), which nothing read: removed, the project lead's
decision (KNOWN_ISSUES K103).

Rows
  every market commodity (definitions.MARKET_COMMODITIES) with a world price in CAPRI's FAO_agg market data:
      p_dataMarket 'World'.'PMRK'.<CAPRI product>.'BAS', the product being the commodity's CAPRI code
      (capri_data/schema/codes/model_commodities.csv); the model's wheat market SWHE is CAPRI's market product WHEA
      (196.6; until 29 October 2026 CAPRI's 'SWHE' price, 171.9, which no market of CAPRI's carries: KNOWN_ISSUES K90)
  DWHE, SUGB  not market commodities, kept as rows: the outer loop's price signal takes its index from this table and
        sets them from soft wheat and sugar (model.py); their values are FAO_agg's 'DWHE' and 'SUGB'
  OLIV  the model's olive market is in tonnes of olives, CAPRI trades olive oil (OLIO): OLIO's world price times the
        EU's oil extraction, FAO_agg's EU olive oil production (MAPR OLIO BAS of the EU member states of the regional
        units) over CAPRI's EU olives for oil (res_17 OLIV YILD x LEVL of the same member states, kg) in t
  FPRI  FAO_agg has no world price for it: CAPRI's 2017 market, export-weighted market prices of the exporting
        regions (bilateral_flows_2017.csv, bilateral_regions_2017.csv; written by build_feed_byproducts.py until
        29 October 2026)

Until 29 October 2026 most rows had no builder: written by an earlier one, at 2 decimals (1 for the oilseed oils and
cakes and for olives), with two placeholder rows of removed markets (FATS 900, OFOD_M 400) and build_feed_byproducts.py
updating eleven rows in place. The rows now hold the source's value to the last digit (the largest changes OLIV 520.8
-> 520.70, -0.020%, and RAPC -0.018%; the others at most 0.012%), and the placeholders are gone.

    python tools/build/build_world_prices.py [--fao FILE] [--dumps DIR]
"""
from __future__ import annotations

import argparse
import csv
import glob
import re
import sys
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from capri_mod.data import definitions as D  # noqa: E402

MKT = ROOT / "capri_data" / "2017" / "market"
OUT = MKT / "world_prices.csv"
CODES = ROOT / "capri_data" / "schema" / "codes" / "model_commodities.csv"
UNITS = ROOT / "capri_data" / "shared" / "regional_units.csv"
FAO = Path("/mnt/user-data/uploads/fao_agg_17_datamarket.txt")
DUMPS = Path("/home/claude/work/capreg")
FAO_SRC = "FAO_agg_17_defaulta p_dataMarket 'World'.'PMRK'.'BAS'"
#: the CAPRI product whose world price a row takes where it is not the commodity's CAPRI code (model_commodities.csv),
#: and the rows that are not market commodities
SOURCE_CODE = {"DWHE": "DWHE", "SUGB": "SUGB"}


def fao_market(path: Path):
    """FAO_agg's world prices ('World' PMRK BAS) and production of olive oil per region (MAPR OLIO BAS)."""
    world, olio = {}, {}
    rx = re.compile(r"^'([^']+)'\.'(PMRK|MAPR)'\.'([^']+)'\.'BAS'\s+([-\d.Ee+]+)")
    with open(path, errors="ignore") as fh:
        for line in fh:
            m = rx.match(line)
            if not m:
                continue
            reg, item, prod, v = m.groups()
            if item == "PMRK" and reg == "World":
                world[prod] = float(v)
            elif item == "MAPR" and prod == "OLIO":
                olio[reg] = float(v)
    return world, olio


def olives_for_oil(dumps: Path, member_states) -> float:
    """CAPRI's olives for oil in 2017 over the member states, t: res_17 OLIV YILD (kg/ha) x LEVL (1000 ha)."""
    rx = re.compile(r"^'([A-Z]{2}000000)'\.'OLIV'\.'(LEVL|YILD)'\.'Y'\s+([-\d.Ee+]+)")
    d = {}
    for f in sorted(glob.glob(str(dumps / "res_17*.txt"))):
        with open(f, errors="ignore") as fh:
            for line in fh:
                m = rx.match(line)
                if m and m.group(1) in member_states:
                    d.setdefault(m.group(1), {})[m.group(2)] = float(m.group(3))
    return sum(v.get("LEVL", 0.0) * v.get("YILD", 0.0) for v in d.values())


def fpri_price() -> float:
    """FPRI: the export-weighted market price of the exporting regions in CAPRI's 2017 market."""
    fl = _read_csv(MKT / "bilateral_flows_2017.csv")
    f = fl[(fl.commodity == "FPRI") & (fl.importer != fl.exporter)]
    rg = _read_csv(MKT / "bilateral_regions_2017.csv")
    pm = rg[rg.commodity == "FPRI"].set_index("region")["pmrk"]
    ex = f.groupby("exporter")["q_kt"].sum()
    return float(sum(q * float(pm.get(r, 0.0)) for r, q in ex.items()) / ex.sum())


def build(fao: Path = FAO, dumps: Path = DUMPS):
    world, olio = fao_market(fao)
    with open(CODES, newline="", encoding="utf-8") as fh:
        capri_code = {r["code"]: r["capri_code"] for r in csv.DictReader(fh)}
    with open(UNITS, newline="", encoding="utf-8") as fh:
        ms = sorted({r["capri_ms"] for r in csv.DictReader(fh) if r["country"] != "NO"})
    prices, prov, missing = {}, {}, []
    for c in list(D.MARKET_COMMODITIES) + ["DWHE", "SUGB"]:
        if c == "OLIV":
            oil = sum(olio.get(m, 0.0) for m in ms)                  # t of olive oil
            olives = olives_for_oil(dumps, set(ms))                  # kg x 1000 ha = t
            ratio = oil / olives
            prices[c] = world["OLIO"] * ratio
            prov[c] = {"capri_code": "OLIO", "source": f"FAO_agg World PMRK OLIO BAS ({world['OLIO']:.1f} EUR/t) x the "
                       f"EU's olive oil per t of olives for oil ({oil / 1e3:,.0f} kt oil, FAO_agg MAPR OLIO BAS of the "
                       f"member states / {olives / 1e3:,.0f} kt olives, res_17 OLIV YILD x LEVL = {ratio:.4f}): the "
                       "model's OLIV market is in t of olives; tools/build/build_world_prices.py"}
        elif c == "FPRI":
            prices[c] = fpri_price()
            prov[c] = {"capri_code": "FPRI", "source": "CAPRI market_base_1717: export-weighted PMRK of the exporting "
                       "regions (FAO_agg has no World PMRK for FPRI); tools/build/build_world_prices.py"}
        else:
            code = SOURCE_CODE.get(c, capri_code.get(c))
            if code not in world:
                missing.append(f"{c} ({code})")
                continue
            prices[c] = world[code]
            prov[c] = {"capri_code": code, "source": FAO_SRC}
    if missing:
        raise SystemExit(f"no FAO_agg world price for {missing}")
    return prices, prov


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fao", type=Path, default=FAO)
    ap.add_argument("--dumps", type=Path, default=DUMPS)
    a = ap.parse_args()
    prices, _prov = build(a.fao, a.dumps)
    s = pd.Series(prices, name="price")
    s.index.name = "commodity"
    s.to_frame().to_csv(OUT)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(s)} rows")


if __name__ == "__main__":
    main()
