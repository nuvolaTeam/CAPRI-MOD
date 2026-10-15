"""CAPRI's exemptions in the crop-specific mineral fertiliser reduction (pol_input/greendeal/minfert_redu_by_crop.gms).

minfert_redu_by_crop.gms caps mineral N per hectare of each crop group (NGRP) at its baseline x (1 - r) and exempts:
  - every group whose baseline mineral N is below 0.03 t/ha (30 kg/ha; applied in the model, not listed here);
  - listed (region, group) pairs, "adhoc fixes for unclear infeasibilities", capped at a factor (1, 1.1 or 1.2)
    times their baseline instead, each from a simulation year on ($ifthene %simy%>YYYY) and some only with
    othPol == high;
and relaxes the "limCres" regulation (crop residues to a group at most 1.3 x baseline per ha) by +0.5 or +1 for
listed pairs, again by simulation year.

This builder reads the file as CAPRI ships it and writes both lists; the model picks the rows that apply to its
simulation year (CAPRI's conditions are strict: simy > YYYY).

Outputs (capri_data/2017/policy/)
  mineral_redu_exemptions.csv   capri_region, ngrp, factor, after_year, othpol_high
  mineral_redu_limcres.csv      capri_region, ngrp, add, after_year

    python tools/build_mineral_redu_rules.py [--gms /home/claude/work/allgms/gams/pol_input/greendeal/minfert_redu_by_crop.gms]
"""
from __future__ import annotations
import argparse, re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "capri_data" / "2017" / "policy"
SRC = ROOT / "capri_data" / "sources" / "policy" / "minfert_redu_by_crop.gms"


def parse(text: str):
    year, oth, skip = [None], [False], False
    exm, lim = [], []
    stmt = ""
    for raw in text.splitlines():
        line = raw.strip()
        low = line.lower()
        if low.startswith("$ontext"):
            skip = True
            continue
        if low.startswith("$offtext"):
            skip = False
            continue
        if skip or line.startswith("*"):
            continue
        m = re.match(r"\$ifthene\.\S+\s+%simy%>(\d+)", line, re.I)
        if m:
            year.append(int(m.group(1)))
            continue
        if re.match(r"\$iftheni\.oth\S*\s+%othPol%==high", line, re.I):
            oth.append(True)
            continue
        m = re.match(r"\$endif\.(\S+)", line, re.I)
        if m:
            (oth if m.group(1).lower().startswith("oth") else year).pop()
            continue
        # limCres relaxations: $ife %simy%>YYYY  +.5 $ (sameas(ru,"X") $ sameas(ngrp,"Y"))
        m = re.match(r'\$ife\s+%simy%>(\d+)\s+\+\s*([0-9.]+)\s*\$\s*\(sameas\(ru,"([A-Z0-9]+)"\)\s*\$\s*sameas\(ngrp,"([A-Z]+)"\)\)',
                     line, re.I)
        if m:
            lim.append(dict(capri_region=m.group(3), ngrp=m.group(4), add=float(m.group(2)), after_year=int(m.group(1))))
            continue
        if line.startswith("p_checkSmallMine(ru,NGRP)") or stmt:
            stmt += " " + line
            if not stmt.rstrip().endswith(";"):
                continue
            s, stmt = stmt, ""
            r = re.search(r'sameas\(ru,"([A-Z0-9]+)"\)', s)
            if r is None:
                continue
            f = re.search(r"=\s*([0-9.]*)\s*\*?\s*p_minfertBaseline", s)
            fac = float(f.group(1)) if f and f.group(1) not in ("", ".") else 1.0
            for g in re.findall(r'sameas\(ngrp,"([A-Z]+)"\)', s, re.I):
                exm.append(dict(capri_region=r.group(1), ngrp=g.upper(), factor=fac,
                                after_year=year[-1] if year[-1] is not None else 0, othpol_high=int(oth[-1])))
    return pd.DataFrame(exm), pd.DataFrame(lim)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gms", type=Path,
                    default=Path("/home/claude/work/allgms/gams/pol_input/greendeal/minfert_redu_by_crop.gms"))
    a = ap.parse_args()
    if a.gms.exists():
        SRC.parent.mkdir(parents=True, exist_ok=True)
        SRC.write_text(a.gms.read_text(errors="ignore"))
    exm, lim = parse(SRC.read_text(errors="ignore"))
    exm.to_csv(DEST / "mineral_redu_exemptions.csv", index=False)
    lim.to_csv(DEST / "mineral_redu_limcres.csv", index=False)
    print(f"exemptions: {len(exm)} rows; for 2030 (simy > year, othPol not high): "
          f"{len(exm[(exm.after_year < 2030) & (exm.othpol_high == 0)])}")
    print(exm[(exm.after_year < 2030) & (exm.othpol_high == 0)].to_string(index=False))
    print(f"limCres relaxations: {len(lim)} rows; for 2030: {len(lim[lim.after_year < 2030])}")


if __name__ == "__main__":
    main()
