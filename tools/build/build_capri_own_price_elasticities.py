"""CAPRI's calibrated own-price supply elasticities per member state, p_ElasSupp(MS, x, x, 'CAL') of CAPRI's 2020
supply-model calibration runs (KNOWN_ISSUES K101): the elasticity-calibrated PMP's CAPRI_COUNTRY source
(docs/PMP_ELASTICITY_WIRING.md), not the default PMP (CAPRI's 2030 terms).

    capri_data/2017/supply/capri_own_price_elasticities.csv   capri_country, <product>...

From the gdxdumps supply_elas_2_1720<MS>defaulta.txt (DE, ES, FR, IT, PL as files, the other member states in
supply_elas_2_1720REMAINI_NGdefaulta.zip; copies with a hash suffix in the name skipped): the own-price records
'<MS>000000'.x.x.'CAL'. Rows: CAPRI's two-letter country codes, sorted; columns: the products in the order they first
appear in the files (sorted by name); empty where a member state has no supply elasticity of the product. Until 29
October 2026 the file had no builder (the same values).

    python tools/build/build_capri_own_price_elasticities.py [--src DIR]
"""
from __future__ import annotations

import argparse
import re
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = Path("/mnt/user-data/uploads")
OUT = ROOT / "capri_data" / "2017" / "supply" / "capri_own_price_elasticities.csv"
NAME = re.compile(r"^supply_elas_2_1720([A-Z]{2})defaulta\.txt$")
REC = re.compile(r"^'([A-Z]{2})000000'\.'([A-Z0-9]+)'\.'([A-Z0-9]+)'\.'CAL'\s+([^,\s]+)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=SRC)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        for z in sorted(a.src.glob("supply_elas_2_1720*.zip")):
            with zipfile.ZipFile(z) as zf:
                zf.extractall(tmp)
        files = sorted([p for p in a.src.glob("supply_elas_2_1720*.txt") if NAME.match(p.name)]
                       + [p for p in Path(tmp).rglob("*.txt") if NAME.match(p.name)], key=lambda p: p.name)
        rows: dict = {}
        cols: list = []
        for f in files:
            ms = NAME.match(f.name).group(1)
            for line in open(f, errors="ignore"):
                m = REC.match(line)
                if m and m.group(1) == ms and m.group(2) == m.group(3):
                    rows.setdefault(ms, {})[m.group(2)] = float(m.group(4))
                    if m.group(2) not in cols:
                        cols.append(m.group(2))
    df = pd.DataFrame.from_dict(rows, orient="index").reindex(columns=cols).sort_index()
    df.index.name = "capri_country"
    df.to_csv(OUT)
    print(f"{OUT.name}: {df.shape[0]} member states x {df.shape[1]} products from {len(files)} files")


if __name__ == "__main__":
    main()
