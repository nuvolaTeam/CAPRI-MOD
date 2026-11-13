"""The long-run change factors CAPTRD reads (p_longRunInfoAll of results/global/longrun_info_fac_%reg_agg%.gdx,
captrd/longrun_supports.gms l. 97-104), as CSV: the records of the long-run selection (the setting
captrd.longrun_scenario, CAPTRD's %SelecScen%) for the member states CAPTRD projects and World.

Source: the project lead's CAPRI installation, results/global/longrun_info_fac_defaulta.gdx, converted by
tools/build/convert_capri_gdx.py (dat_parquet/global/longrun_info_fac_defaulta/p_longRunInfoAll). In the file in hand
(11 November 2026) the reference run's selection globiom_eu_bright_s0_2023+REFERENCE+REFERENCE has no records: the
output then holds none, as CAPTRD's p_longrunInfo in that run (its results hold no Longrun records).
Output: capri_data/pipeline/captrd/dat/longrun_p_longruninfoall.csv.

    python tools/build/build_captrd_longrun.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import SOURCES                                  # noqa: E402

PARQ = SOURCES / "dat_parquet" / "global" / "longrun_info_fac_defaulta" / "p_longRunInfoAll.parquet"
OUT = ROOT / "capri_data" / "pipeline" / "captrd" / "dat" / "longrun_p_longruninfoall.csv"


def main() -> None:
    import pandas as pd
    from capri_mod.pipeline.captrd import prepare as P
    from capri_mod.settings import current
    scen = str(current().get("captrd.longrun_scenario")).upper()
    d = pd.read_parquet(PARQ)
    if d["special"].fillna("").ne("").any():
        raise ValueError(f"{PARQ}: special values")
    regs = set(P.read_sets().ms) | {"WORLD"}
    d = d[d.d5.str.upper().eq(scen) & d.d1.str.upper().isin(regs)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["region", "col", "row", "info", "scenario", "year", "value"])
        for r in d.itertuples(index=False):
            w.writerow([r.d1.upper(), r.d2.upper(), r.d3.upper(), r.d4, r.d5, r.d6, repr(float(r.value))])
    print(f"{OUT.relative_to(ROOT)}: {len(d)} records (scenario {scen})")


if __name__ == "__main__":
    main()
