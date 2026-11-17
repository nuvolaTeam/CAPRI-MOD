"""CAPRI's 2030 value of the non-tradable fodders, per region and fodder, as the fodder balance's base dual (KNOWN_ISSUES
K161; the project lead's decision of 16 November 2026).

Source: CAPRI's 2030 Green Deal baseline, dataOut of res_2_1730greendeal_refdefaulta (tools/lib/paths.BASELINE_REF,
the run the model's 2030 base reproduces): dataOut(R, '', 'UVAG', fodder, '2030'), the unit value of the fed fodder
(FGRA, FMAI, FOFA, FROO), EUR per t fed in CAPRI's 2030 money. It is the dual of CAPRI's SUPBAL_ per t of the fodder
(supply/supply_model.gms: FEDM + DEMD = output), the item the 2017 data's base value is taken from (UVAG,
tools/build/build_fodder_balance.py), and EAAG = UVAG x FEDM: the value of the crops' output where all of it is fed
(ES41 grass: UVAG 14.41 x FEDM 9924 = MPRI 6.94 x PROD 20592 = 143 million EUR). The model's balance
(capri_data/2017/feed/fodder_balance_2017.csv) is in t of usable fodder, u per ha the fed quantity per ha, so its dual
is per t fed, as UVAG. The value is put in the model's 2017 money (K108: CAPRI's 2030 money over its inflation to 2030,
tools/lib/_money).

Not taken: CAPRI's crop price MPRI x YILD per ha over the model's u per ha. It gives UVAG where the model's u is
CAPRI's fed quantity per ha (ES41 grass: 11.28 EUR/t with the projected u), but where most of the crop is not fed
(DE91's fodder maize: 712 kt produced, 0.03 kt fed, the rest CAPRI's exogenous demand) it puts the crop's whole value
on the fed tonnes (77,560 EUR/t). Before, the base value was the highest 2017 ration price of the region's animals
(build_fodder_balance.py) scaled to 2030 by the fodder's price index (capri_mod/projection/prices.py): for grass and
other fodder about 1.8 times CAPRI's 2030 UVAG (median), for fodder maize and fodder roots 1.15 to 1.2 times.

Output
  capri_data/baselines/capri_greendeal_ref/1730/feed/fodder_value_2030.csv
      region, fodder, value_eur_t (EUR of 2017 per t fed), uvag_capri_2030 (CAPRI's UVAG, EUR of 2030 per t fed)
  Region and fodder pairs of the fodder balance without CAPRI's UVAG are left out (the model keeps its projected 2017
  value).

    python tools/build/build_fodder_value_2030.py [--src ZIP]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import BASELINE_REF  # noqa: E402  (CAPRI's material outside the repository)
from _grep import lines  # noqa: E402  (a listing's lines, plain or zipped)
import _money  # noqa: E402

FB = ROOT / "capri_data" / "2017" / "feed" / "fodder_balance_2017.csv"
OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "feed" / "fodder_value_2030.csv"
FODDERS = ("FGRA", "FMAI", "FOFA", "FROO")


def num(s: str) -> float:
    s = s.strip().rstrip(",").strip()
    return 0.0 if s.upper() == "EPS" else float(s)


def read(src: Path) -> dict:
    """{(region, fodder): CAPRI's 2030 UVAG} for the non-tradable fodders."""
    rx = re.compile(r"^'([A-Z0-9_]{8})'\.''\.'UVAG'\.'([A-Z]+)'\.'2030'\s+(\S+)")
    out = {}
    for line in lines(src):
        if "'UVAG'" not in line or "'2030'" not in line:
            continue
        m = rx.match(line)
        if m and m.group(2) in FODDERS:
            out[(m.group(1), m.group(2))] = num(m.group(3))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=BASELINE_REF)
    a = ap.parse_args()
    cap = read(a.src)
    defl = float(_money.deflator(2030))
    pairs = pd.read_csv(FB, float_precision="round_trip")[["region", "fodder"]].drop_duplicates()
    rows = [dict(region=r, fodder=f, value_eur_t=cap[(r, f)] / defl, uvag_capri_2030=cap[(r, f)])
            for r, f in pairs.itertuples(index=False) if cap.get((r, f), 0.0) > 0]
    o = pd.DataFrame(rows).sort_values(["region", "fodder"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    o.to_csv(OUT, index=False)
    print(f"fodder_value_2030.csv: {len(o)} region x fodder rows ({o.region.nunique()} regions) of {len(pairs)} in "
          f"the fodder balance; deflator 2030 {defl:.4f}")


if __name__ == "__main__":
    main()
