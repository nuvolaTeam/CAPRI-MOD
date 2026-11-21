"""CAPRI's milk for feeding at its 2030 calibration point: the cows' output of milk fed to calves and the sheep and goats'
milk fed to lambs, per head, and the milk's value, for the non-tradable balances of milk for feeding (KNOWN_ISSUES
K189, 20 November 2026).

In CAPRI, COMF (cow milk for feeding) and SGMF (sheep and goat milk for feeding) are non-tradable outputs (FODDO):
the cows (DCOW, DCOL, DCOH, SCOW) and the milk sheep and goats (SHGM) produce them (PACT_TO_O), the calves and the
sheep and goats feed them as FCOM and FSGM (FEED_TO_O), and SUPBAL_ (supply/supply_model.gms l. 4551-4611) holds the
use plus the losses (FEDUSE_ l. 789-803: v_lossQuant(COMF), free between 0 and infinity, supply/prep_sim.gms
l. 222-223) at the output. The balance's dual is the milk's value in the feeding problem: CAPRI reports it as UVAG
(ES41 COMF 152.98 EUR/t; FEDM = GROF in every region, no loss, at the reference and in the Green Deal step).

Source: CAPRI's 2030 Green Deal baseline, dataOut of res_2_1730greendeal_refdefaulta (tools/lib/paths.BASELINE_REF,
the run the model's 2030 base reproduces): dataOut(R, '', act, COMF/SGMF, '2030'), the output per head (kg) of DCOW,
SCOW and SHGM (DCOL and DCOH give DCOW's per head, the model has DCOW), and dataOut(R, '', 'UVAG', COMF/SGMF,
'2030'), EUR per t in CAPRI's 2030 money, put in the model's 2017 money (KNOWN_ISSUES K108: over CAPRI's inflation to
2030, tools/lib/_money).

Output
  capri_data/baselines/capri_greendeal_ref/1730/feed/milk_for_feeding_2030.csv
      region, product (COMF, SGMF), feed (FCOM, FSGM), animal (the model's producer: DCOW, BCOW for CAPRI's SCOW,
      SHGM), output_t_head (CAPRI's output per head, t), value_eur_t (EUR of 2017 per t), uvag_capri_2030 (CAPRI's
      UVAG, EUR of 2030 per t)
  Regions of the model (capri_data/codes/regional_units.csv) where CAPRI's reference has the output and a value.

    python tools/build/build_milk_for_feeding_2030.py [--src ZIP]
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

OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "feed" / "milk_for_feeding_2030.csv"
REGIONS = ROOT / "capri_data" / "codes" / "regional_units.csv"
#: CAPRI's non-tradable milk outputs and the feeds they are fed as (FEED_TO_O)
FEED_OF = {"COMF": "FCOM", "SGMF": "FSGM"}
#: CAPRI's producing activities (PACT_TO_O) and the model's animal (DCOL and DCOH: DCOW's per head)
PRODUCERS = {"COMF": {"DCOW": "DCOW", "SCOW": "BCOW"}, "SGMF": {"SHGM": "SHGM"}}


def num(s: str) -> float:
    s = s.strip().rstrip(",").strip()
    return 0.0 if s.upper() == "EPS" else float(s)


def read(src: Path) -> tuple:
    """({(region, activity, product): kg per head}, {(region, product): CAPRI's 2030 UVAG})."""
    rx = re.compile(r"^'([A-Z0-9_]{8})'\.''\.'([A-Z0-9]+)'\.'(COMF|SGMF)'\.'2030'\s+(\S+)")
    out, uv = {}, {}
    acts = {a for d in PRODUCERS.values() for a in d}
    for line in lines(src):
        if "'2030'" not in line or ("'COMF'" not in line and "'SGMF'" not in line):
            continue
        m = rx.match(line)
        if not m:
            continue
        r, item, prod, v = m.group(1), m.group(2), m.group(3), num(m.group(4))
        if item == "UVAG":
            uv[(r, prod)] = v
        elif item in acts:
            out[(r, item, prod)] = v
    return out, uv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=BASELINE_REF)
    a = ap.parse_args()
    out, uv = read(a.src)
    defl = float(_money.deflator(2030))
    regs = sorted(set(pd.read_csv(REGIONS, dtype=str).iloc[:, 0]))
    rows = []
    for r in regs:
        for prod, acts in PRODUCERS.items():
            v = uv.get((r, prod), 0.0)
            if not v > 0:
                continue
            for ca, ma in acts.items():
                kg = out.get((r, ca, prod), 0.0)
                if kg > 0:
                    rows.append(dict(region=r, product=prod, feed=FEED_OF[prod], animal=ma, output_t_head=kg / 1000.0,
                                     value_eur_t=v / defl, uvag_capri_2030=v))
    o = pd.DataFrame(rows).sort_values(["region", "product", "animal"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    o.to_csv(OUT, index=False)
    print(f"milk_for_feeding_2030.csv: {len(o)} rows, {o.region.nunique()} regions "
          f"({o[o['product'] == 'COMF'].region.nunique()} with COMF, {o[o['product'] == 'SGMF'].region.nunique()} with "
          f"SGMF); deflator 2030 {defl:.4f}")


if __name__ == "__main__":
    main()
