"""CAPRI's literal parameters of biofuel/resids.gms (capri_data/2017/supply/biofuel_resids_params.csv), the data of
the year's crop residues and second-generation biofuel sources in capri_mod/projection/equations/
load_base_data_and_trends.py (DATA_ARES, DATA_NECR_LEVL_1_2, DATA_SECG_ARES_bio; included by
capmod/load_base_data_and_trends.gms l. 795).

Read from CAPRI star 3.0's biofuel/resids.gms (capri_sources/gams):
- p_residYield(PACT): the crop residues' yield relative to the main yield, dry weight (l. 24-35);
- p_newEnergyCropYield: the new energy crops' biomass yield per member state, REST for the others (l. 49-57);
- p_secgConv: the conversion of biomass to second-generation biofuel (l. 64-67).

Output, long: symbol, item, value.

    python tools/build/build_resids_params.py [--gams capri_sources/gams]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from gams_text import parameter_records, read_text  # noqa: E402  (GAMS's parameter lists)
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)

OUT = ROOT / "capri_data" / "2017" / "supply" / "biofuel_resids_params.csv"
SYMBOLS = ("p_residYield", "p_newEnergyCropYield", "p_secgConv")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gams", type=Path, default=SOURCES / "gams")
    a = ap.parse_args()
    src = a.gams / "biofuel" / "resids.gms"
    text = read_text(src)
    rows = [(s, k, float(v)) for s in SYMBOLS for k, v in parameter_records(text, s, 1, str(src))]
    t = pd.DataFrame(rows, columns=["symbol", "item", "value"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(t)} rows ({', '.join(f'{s} {n}' for s, n in t.symbol.value_counts().items())})")


if __name__ == "__main__":
    main()
