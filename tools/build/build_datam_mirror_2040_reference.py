"""CAPRI's 2040 results of the JRC study on stronger alignment of import production standards (pesticide active
substances not approved in the EU), as extracted from the JRC DataM dashboard, to CSV in the reference folder.

Source: the project lead's extracts of https://datam.jrc.ec.europa.eu/datam/mashup/MRL_TO_LOQ_2/ (uploaded
5 November 2026; the dashboard states the data valid as of February 2026, scenario assessments, not forecasts), kept in
capri_sources/datam_mirror_2040/:

  area_member_states.xlsx    utilised area per member state (1000 ha); the dashboard gave the same table four times,
                             each with another scenario as the reference column, identical in levels: one is kept
  production_change_eu.xlsx  EU production change per product (fraction); the scenario is not stated in the extract
  producer_prices.xlsx       producer price per trade region and product (EUR/t)
  trade_flows.xlsx           bilateral trade per reporter, product and partner; the variable and its unit are not
                             stated in the extract (to be asked)

Scenarios: Baseline, switchX-scaleEFSA_5, switchX-scaleEFSA+min20, noadapt-noscale (the dashboard's names). Not an
input of the model: kept as a future 2040 check for CAPTRD-MOD (the project lead, 5 November 2026; MODEL_CONTENT_PLAN
§14 item 19). The shock inputs (restriction shares and cost increases per exporter and product) and CAPRI's scenario
code are not in the extracts.

Writes capri_sources/reference/datam_mirror_2040/:
  area_member_states.csv    member_state, scenario, area_1000ha
  production_change_eu.csv  product, production_change
  producer_prices.csv       trade_region, product, scenario, price_eur_t
  trade_flows.csv           reporter_block, reporter, product_aggregate, product, scenario, partner_block, partner, value
  Cells the dashboard left empty or marked '-' are not written; the dashboard's labels are kept as they are (including
  its spellings) so that rows can be traced back to the extract.

    python tools/build/build_datam_mirror_2040_reference.py [--src DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import SOURCES, REFERENCE  # noqa: E402

SRC = SOURCES / "datam_mirror_2040"
OUT = REFERENCE / "datam_mirror_2040"


def _rows(path: Path) -> list:
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _write(path: Path, header: list, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{path.name}: {len(rows)} rows")


def area(src: Path) -> list:
    r = _rows(src)
    scen, what = r[0], r[1]
    out = []
    for row in r[2:]:
        for j in range(1, len(row)):
            if what[j] == "Area (1000 ha)" and _num(row[j]) is not None:
                out.append([row[0], scen[j], repr(float(row[j]))])
    return out


def production(src: Path) -> list:
    r = _rows(src)
    return [[row[0], repr(float(row[1]))] for row in r[1:] if row[0] and _num(row[1]) is not None]


def prices(src: Path) -> list:
    r = _rows(src)
    scen, what = r[0], r[1]
    out = []
    for row in r[2:]:
        for j in range(2, len(row)):
            if what[j] == "Producer price (€/T)" and _num(row[j]) is not None:
                out.append([row[0], row[1], scen[j], repr(float(row[j]))])
    return out


def flows(src: Path) -> list:
    r = _rows(src)
    scen, pblock, partner = r[0], r[1], r[2]
    out = []
    for row in r[3:]:
        for j in range(5, len(row)):
            if _num(row[j]) is not None:
                out.append([row[0], row[1], row[2] or "", row[3] or "", scen[j], pblock[j], partner[j] or "",
                            repr(float(row[j]))])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    for f in ("area_member_states.xlsx", "production_change_eu.xlsx", "producer_prices.xlsx", "trade_flows.xlsx"):
        if not (a.src / f).exists():
            sys.exit(f"missing {a.src / f}: the project lead's DataM extracts (docs/EXTERNAL_SOURCES.md, datam_mirror_2040)")
    a.out.mkdir(parents=True, exist_ok=True)
    _write(a.out / "area_member_states.csv", ["member_state", "scenario", "area_1000ha"],
           area(a.src / "area_member_states.xlsx"))
    _write(a.out / "production_change_eu.csv", ["product", "production_change"],
           production(a.src / "production_change_eu.xlsx"))
    _write(a.out / "producer_prices.csv", ["trade_region", "product", "scenario", "price_eur_t"],
           prices(a.src / "producer_prices.xlsx"))
    _write(a.out / "trade_flows.csv", ["reporter_block", "reporter", "product_aggregate", "product", "scenario",
                                       "partner_block", "partner", "value"], flows(a.src / "trade_flows.xlsx"))


if __name__ == "__main__":
    main()
