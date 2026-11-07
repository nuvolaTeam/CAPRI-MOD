"""Build the regional fodder balance data (docs/FODDER_BALANCE.md).

Per region and non-tradable fodder (grass, fodder maize, other fodder):
  crop          the supply activity producing it (GRAS, MAIF, OFAR, ROOF: CAPRI's FODCRP; until S2, 7 November
                2026, OFOD = OFAR + ROOF produced FOFA and fodder root crops FROO had no balance)
  u_t_per_ha    usable fresh fodder per ha = CAPRI base fodder use / base area
                (CAPRI SUPBAL_: use = production x (1 - on-farm share); the
                coefficient embeds CAPRI's loss share and yield)
  value_eur_t   the fodder's base value = CAPRI unit value (UVAG), the dual the
                balance carries at base
  use_t_head    fodder per head per animal (t), from feed_ration_2017.csv

Base fodder use = sum(heads x use_t_head), so use = u x area holds exactly at base.

    python tools/build/build_fodder_balance.py

Writes capri_data/2017/feed/fodder_balance_2017.csv (region, fodder, crop, u_t_per_ha, value_eur_t) and
fodder_balance_2017_use.csv (region, fodder, animal, use_t_head), capri_mod/data/nested_tables.py (JSON until
31 October 2026).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
from capri_mod.data.nested_tables import read_feed_rations, write_fodder_balances  # noqa: E402
FODDER = {"FGRA": "GRAS", "FMAI": "MAIF", "FOFA": "OFAR", "FROO": "ROOF"}   # CAPRI's SUPBAL_ of FODF


def main() -> None:
    data = _ROOT / "capri_data" / "2017"
    rations = read_feed_rations(data / "feed" / "feed_ration_2017.csv")
    areas = _read_csv(data / "supply" / "base_areas.csv", index_col=0)
    herds = _read_csv(data / "supply" / "animal_numbers.csv", index_col=0)
    # The raw file uses CAPRI-style names (SCOW, HEIF, SHGO); the model and the rations
    # use BCOW, HFRS, SHGM and SHGF (split from SHGO by tools/build/build_shg_split.py). Without the loader's aliases suckler cows, heifers and sheep
    # were silently left out of every fodder balance (their fodder tied to no land).
    import sys as _sys
    _sys.path.insert(0, str(_ROOT))
    from capri_mod.data.loaders import HERD_ALIASES
    herds = herds.rename(columns=HERD_ALIASES)
    out, worst = {}, 0.0
    for reg, acts in rations.items():
        if reg not in areas.index:
            continue
        for feed, crop in FODDER.items():
            per_head = {a: rec["ration"][feed] / 1000.0 for a, rec in acts.items()
                        if rec["ration"].get(feed, 0.0) > 0 and a in herds.columns}
            use_kt = sum(float(herds.at[reg, a]) * t for a, t in per_head.items())   # 1000 head x t
            area = float(areas.at[reg, crop]) if crop in areas.columns else 0.0       # 1000 ha
            if use_kt <= 0 or area <= 0:
                continue
            u = use_kt / area                                                         # t per ha
            prices = [acts[a]["price"].get(feed, 0.0) for a in per_head]
            value = 1000.0 * max(prices) if prices else 0.0                           # EUR/t
            out.setdefault(reg, {})[feed] = {"crop": crop, "u_t_per_ha": u, "value_eur_t": value,
                                             "use_t_head": per_head}
            worst = max(worst, abs(sum(float(herds.at[reg, a]) * t for a, t in per_head.items()) - u * area))
    # source: feed_ration_2017.csv (CAPRI 2017 rations x herds), base_areas.csv and CAPRI unit values (UVAG); CAPRI
    # supply_model.gms SUPBAL_ for non-tradable fodder. Units: u t fresh fodder per ha; value EUR per t; use t per head
    dest = data / "feed" / "fodder_balance_2017.csv"
    write_fodder_balances(dest, out)
    n = sum(len(v) for v in out.values())
    print(f"wrote {dest}: {len(out)} regions, {n} region x fodder balances; max base residual {worst:.2e} kt")


if __name__ == "__main__":
    main()
