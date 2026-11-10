"""CAPRI's obligatory set-aside scenario (scen/set_aside/set_aside_10.gms, "Flat rate 10% set-aside for Grandes
Cultures") as the model's scenario table capri_data/scenarios/set_aside_10/set_aside_rates.csv: region, activity,
setr_pct.

CAPRI's file sets, for the regional units of the EU (RUNR(RMSSUP) $ MAP_RR("EU027000", RMSSUP), then RU):
  DATA(RUNR, GRCU, "SETR", SIMY) = 10;   the rate on the Grandes Cultures (sets.gms l. 2243: SET.CERE, SET.OILS, PULS,
                                          ISET, GSET, TSET, VSET, MAIF; CERE = CERE_COLS, OILS = OILS_COLS, l. 112-128)
  DATA(RUNR, RSET, "SETR", SIMY) = eps;  none on the obligatory set-aside activities themselves (RSET: ISET, GSET, TSET)
  DATA(RUNR, "VSET", "SETR", SIMY) = eps;  none on voluntary set-aside
  DATA(RUNR, MPACT, "NONS", "Y") = 0;    no non-food production on set-aside (the model has no NONS: 0 throughout)
  DATA(RUNR, "OSET", "FLOOR", ...) = 0;  the obligation is a rate, not a fixed area (SETA_ applies only without it)
  p_smallProducerScheme = 0              no small-producer exemption (the model has none)
This builder reads the rate and the sets from CAPRI's files and writes one row per EU regional unit and model activity
with a positive rate (CAPRI's codes mapped to the model's, MAIZ -> CORN; ISET, GSET, TSET are not model activities and
carry no rate). The obligation itself is supply/land.py _obligatory_set_aside (CAPRI's SETA_).

    python tools/build/build_set_aside_scenario.py [CAPRI gams folder, default capri_sources/gams]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)
sys.path.insert(0, str(ROOT))
from capri_mod.csvio import read_csv, to_csv  # noqa: E402

import pandas as pd  # noqa: E402

OUT = ROOT / "capri_data" / "scenarios" / "set_aside_10" / "set_aside_rates.csv"


def _set_members(text: str, name: str) -> list:
    """The members of SET <name>( ... ) / ... / in sets.gms, SET.<other> expanded (one level of nesting is enough for
    GRCU, CERE, OILS); comments and $-lines dropped."""
    m = re.search(rf"SET\s+{name}\b[^/]*/(.*?)/\s*;", text, re.S | re.I)
    if m is None:
        raise SystemExit(f"sets.gms: SET {name} not found")
    out = []
    for ln in m.group(1).splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("*") or ln.startswith("$"):
            continue
        for tok in re.split(r"\s*,\s*", ln):
            tok = tok.split()[0] if tok.split() else ""
            if not tok:
                continue
            if tok.upper().startswith("SET."):
                out += _set_members(text, tok[4:])
            else:
                out.append(tok.upper())
    return out


def parse(scen: str, sets: str):
    """(rate in percent, the activities with the rate, the activities set to eps) of CAPRI's scenario file."""
    blk = "\n".join(l for l in scen.splitlines() if not l.lstrip().startswith("*"))
    m = re.search(r'DATA\(RUNR\s*,\s*GRCU\s*,\s*"SETR"\s*,\s*SIMY\)\s*=\s*([\d.]+)\s*;', blk, re.I)
    if m is None:
        raise SystemExit("set_aside_10.gms: the GRCU rate (DATA(RUNR,GRCU,\"SETR\",SIMY) = ...) not found")
    rate = float(m.group(1))
    grcu = _set_members(sets, "GRCU")
    eps_ = set()
    if re.search(r'DATA\(RUNR\s*,\s*RSET\s*,\s*"SETR"\s*,\s*SIMY\)\s*=\s*eps', blk, re.I):
        eps_ |= set(_set_members(sets, "RSET"))
    for a in re.findall(r'DATA\(RUNR\s*,\s*"(\w+)"\s*,\s*"SETR"\s*,\s*SIMY\)\s*=\s*eps', blk, re.I):
        eps_.add(a.upper())
    return rate, [a for a in grcu if a not in eps_], sorted(eps_)


def main():
    gams = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCES / "gams"
    scen = (gams / "scen" / "set_aside" / "set_aside_10.gms").read_text(encoding="latin-1")
    sets = (gams / "sets.gms").read_text(encoding="latin-1")
    rate, acts, eps_ = parse(scen, sets)
    from capri_mod.data.definitions import CAPRI_TO_MODEL_ACTIVITY, CROPS, EU_MS_BLOCK
    model_acts = sorted({CAPRI_TO_MODEL_ACTIVITY.get(a, a) for a in acts} & set(CROPS))
    units = read_csv(ROOT / "capri_data" / "shared" / "regional_units.csv")
    eu = sorted(units.loc[units.capri_ms.isin(set(EU_MS_BLOCK)), "region"])
    df = pd.DataFrame([(r, a, rate) for r in eu for a in model_acts], columns=["region", "activity", "setr_pct"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    to_csv(df, OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {rate}% on {model_acts} (CAPRI's GRCU less {eps_}) in {len(eu)} EU units")


if __name__ == "__main__":
    main()
