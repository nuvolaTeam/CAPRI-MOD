"""CAPRI's exemptions in the crop-specific mineral fertiliser reduction (pol_input/greendeal/minfert_redu_by_crop.gms).

minfert_redu_by_crop.gms caps mineral N per hectare of each crop group (NGRP) at its baseline x (1 - r) and exempts:
  - every group whose baseline mineral N is below 0.03 t/ha (30 kg/ha; applied in the model, not listed here);
  - listed (region, group) pairs, "adhoc fixes for unclear infeasibilities", capped at a factor (1, 1.1 or 1.2)
    times their baseline instead, each from a simulation year on ($ifthene %simy%>YYYY) and some only with
    othPol == high;
and relaxes the "limCres" regulation (crop residues to a group at most 1.3 x baseline per ha) by +0.5 or +1 for
listed pairs, again by simulation year.

The file's statements were converted to CSV by tools/build/convert_sources_to_csv.py (its parse of the file, moved
there unchanged): capri_data/sources/policy/minfert_redu_by_crop_p_checkSmallMine.csv and
minfert_redu_by_crop_limCres.csv. This builder reads both and writes them for the model, which picks the rows that
apply to its simulation year (CAPRI's conditions are strict: simy > YYYY).

Outputs (capri_data/2017/policy/)
  mineral_redu_exemptions.csv   capri_region, ngrp, factor, after_year, othpol_high
  mineral_redu_limcres.csv      capri_region, ngrp, add, after_year

    python tools/build/build_mineral_redu_rules.py
"""
from __future__ import annotations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "capri_data" / "2017" / "policy"
SRC = ROOT / "capri_data" / "sources" / "policy"


def main():
    exm = pd.read_csv(SRC / "minfert_redu_by_crop_p_checkSmallMine.csv", keep_default_na=False,
                      float_precision="round_trip")
    lim = pd.read_csv(SRC / "minfert_redu_by_crop_limCres.csv", keep_default_na=False, float_precision="round_trip")
    exm.to_csv(DEST / "mineral_redu_exemptions.csv", index=False)
    lim.to_csv(DEST / "mineral_redu_limcres.csv", index=False)
    print(f"exemptions: {len(exm)} rows; for 2030 (simy > year, othPol not high): "
          f"{len(exm[(exm.after_year < 2030) & (exm.othpol_high == 0)])}")
    print(exm[(exm.after_year < 2030) & (exm.othpol_high == 0)].to_string(index=False))
    print(f"limCres relaxations: {len(lim)} rows; for 2030: {len(lim[lim.after_year < 2030])}")


if __name__ == "__main__":
    main()
