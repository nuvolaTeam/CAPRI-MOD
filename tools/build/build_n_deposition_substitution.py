"""Atmospheric N deposition and the fertiliser substitution terms per model region, from CAPRI's 2030 reference.

Both files were supplied without a builder until 27 October 2026 (docs/design/REGIONAL_UNITS_INVENTORY.md); on CAPRI's
regional units each region takes its own CAPRI row of capri_data/2017/environment/capri_gnb_components_2030.csv
(tools/build/build_capri_gnb_components.py: res_2_1730greendeal_refdefaulta dataOut, kg N per ha), else its member
state's row.

  n_deposition_regional.csv        deposition_kg_n_per_ha = ATMOSD
  fertiliser_substitution_2030.csv mineral_efficiency  = 1 + nutNed_mine_loss_gasRunTot_perha / fertDist_mine_perha
                                   manure_availability = 1 + nutNed_excr_unavailable_perha / fertDist_excr_perha
                                   (CAPRI stores the losses as negative N; supply/supply_model.gms NUTNED_: mineral N
                                   counts net of its losses, manure at its availability)
The two other columns the supplied substitution file had (mineral_share_of_need, need_at_floor_share) were read by no
code and are not rebuilt.

    python tools/build/build_n_deposition_substitution.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / "capri_data" / "2017" / "environment"


def main():
    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    g = pd.read_csv(ENV / "capri_gnb_components_2030.csv", float_precision="round_trip").pivot_table(
        index="capri_region", columns="item", values="kg_n_per_ha")
    dep, sub = [], []
    for reg in mr.model_regions():
        src = reg if reg in g.index else mr.national_code(reg)
        if src not in g.index:
            continue
        x = g.loc[src]
        how = f"CAPRI 2030 reference (res_2_1730greendeal_refdefaulta dataOut), {src}"
        if pd.notna(x.get("ATMOSD")):
            dep.append({"region": reg, "deposition_kg_n_per_ha": float(x["ATMOSD"]), "source": how})
        me, ex = x.get("fertDist_mine_perha"), x.get("fertDist_excr_perha")
        if pd.notna(me) and me > 0 and pd.notna(ex) and ex > 0:
            sub.append({"region": reg,
                        "manure_availability": 1.0 + float(x.get("nutNed_excr_unavailable_perha", 0.0)) / float(ex),
                        "mineral_efficiency": 1.0 + float(x.get("nutNed_mine_loss_gasRunTot_perha", 0.0)) / float(me),
                        "source": how})
    pd.DataFrame(dep).to_csv(ENV / "n_deposition_regional.csv", index=False)
    pd.DataFrame(sub).to_csv(ENV / "fertiliser_substitution_2030.csv", index=False)
    print(f"n_deposition_regional.csv: {len(dep)} regions; fertiliser_substitution_2030.csv: {len(sub)} regions "
          f"(of {len(mr.model_regions())})")


if __name__ == "__main__":
    main()
