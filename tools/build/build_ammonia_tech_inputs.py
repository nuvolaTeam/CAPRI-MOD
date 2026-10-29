"""Convert CAPRI's ammonia-technology input data (GDX text dumps) to CSV.

CAPRI computes its ammonia mitigation options (envind/ammo_tech.gms: low-emission
housing, storage covers, air purification, application techniques, acidification)
at run time from cost tables in the code plus three data files:

    dat\\miterra\\LitRev_non_changeable_parameters.gdx  reduction factors, control
                                                        strategies, grazing fractions
    dat\\miterra\\LitRev_inputs.gdx                    emission fractions, housing and
                                                        storage reductions (LitRev variant,
                                                        CAPRI's default: ammoLitRev = on)
    dat\\miterra\\LitRev_input_manStor.gdx             storage run-off, storage types
    dat\\miterra\\LitRevAmmoTech.gdx                   side effects of four technologies
    dat\\scen\\ghgtech\\holdingsLSU.gdx                   holdings by size class
    dat\\envind\\nvzShare_LU.gdx                          Nitrates-Directive zone shares

The exports supplied are GAMS text dumps (Parameter name(*,*) / 'a'.'b' value, ... /),
whatever their file extension. This script parses them and writes one long-format CSV
per symbol to capri_data/2017/abatement/ammonia/, with named columns, so the model
reads CSV only.

Usage:  python tools/build/build_ammonia_tech_inputs.py <dump> [<dump> ...]
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "ammonia"

# column names per symbol (index dimensions), following ammo_tech.gms usage
DIMS = {
    "ControlStrat_TS": ["region", "animal_mitt", "strategy", "year"],
    "ControlStrategies": ["region", "animal_mitt", "strategy", "item"],
    "reducControlStrategies": ["region", "animal_mitt", "strategy", "item"],
    "RCEmissions": ["region", "animal_mitt", "item"],
    "FracEmGrazing": ["region", "animal_mitt", "item"],
    "FracNVZNuts2": ["region"],
    "FracNVZNuts2_full": ["region"],
    "PercPeat": ["region"],
    "p_holdLSU": ["region", "animal_group", "size_class"],
    "p_nvzShare_lu": ["region"],
    # LitRev_inputs (CAPRI default: ammoLitRev = on)
    "FracToepHouse": ["region", "animal_mitt", "tech_class"],
    "FracToepStorage": ["region", "animal_mitt", "tech_class"],
    "reducBio": ["region", "animal_mitt", "gas"],
    "rLFManureBasis": ["region", "animal_mitt"],
    "rLFManureND": ["region", "animal_mitt"],
    "CorrND": ["region", "item"],
    "rCorrND": ["region", "item"],
    "NN_CorrFertFactDeviation": ["region", "fertiliser", "year"],
    "bNumAniRAINS": ["region", "animal_mitt", "year"],
    "ScalarArray": ["item"],
    "FracEmHouse": ["region", "animal_mitt", "gas"],
    "FracEmStorage": ["region", "animal_mitt", "gas"],
    "FracEmAppl": ["region", "animal_mitt", "gas"],
    "EmFracFert": ["region", "gas", "fertiliser"],
    "FracUseFert": ["region", "fertiliser"],
    "reducEmHouse": ["region", "animal_mitt", "gas", "tech_class"],
    "reducEmStorage": ["region", "animal_mitt", "gas", "tech_class"],
    "rLFRest": ["region", "item"],
    # LitRev_input_manStor
    "p_factRunStor": ["manure_system", "tech_class", "storage_type"],
    "p_fracStorType": ["region", "manure_system", "storage_type"],
    # LitRevAmmoTech: side effects of four technologies on other emissions
    "p_litRevAmmoTechsAdd": ["region", "technology", "activity", "manure_system", "item"],
}

_HEAD = re.compile(r"^\s*Parameter\s+(\w+)\s*\(([^)]*)\)")
# a record; the LAST record of a symbol carries the closing "/;" on its own line
_REC = re.compile(r"^\s*((?:'[^']*'\.)*'[^']*')\s+([-+0-9.eE]+|Eps|EPS|eps|Inf|-Inf|NA|UNDF)\s*(,|/;)?\s*$")


def _num(tok: str) -> float:
    t = tok.lower()
    if t == "eps":
        return 0.0
    if t in ("inf",):
        return float("inf")
    if t in ("-inf",):
        return float("-inf")
    if t in ("na", "undf"):
        return float("nan")
    return float(tok)


def parse_dump(path: Path) -> dict:
    """Return {symbol: [(keys tuple, value), ...]} from a GAMS text dump."""
    out, cur = {}, None
    with open(path, encoding="latin-1") as f:
        for raw in f:
            line = raw.rstrip("\r\n")
            m = _HEAD.match(line)
            if m:
                cur = m.group(1)
                out[cur] = []
                continue
            if cur is None:
                continue
            if line.strip().startswith("/"):
                cur = None
                continue
            r = _REC.match(line)
            if r:
                keys = tuple(k.strip("'") for k in re.findall(r"'[^']*'", r.group(1)))
                out[cur].append((keys, _num(r.group(2))))
                if r.group(3) == "/;":
                    cur = None
    return out


#: the symbols the model or a builder of its inputs reads (KNOWN_ISSUES K102; the project lead's decision of 29 October
#: 2026: the extractors write only what is read). Not written: ControlStrat_TS, CorrND, FracNVZNuts2(_full),
#: FracToepHouse, FracToepStorage, FracUseFert, PercPeat, ScalarArray, rCorrND, rLFManureBasis, rLFManureND, reducBio
#: (CAPRI's data of parts not ported, read by no code)
READ = {"ControlStrategies", "reducControlStrategies", "RCEmissions", "FracEmGrazing", "p_holdLSU", "p_nvzShare_lu",
        "NN_CorrFertFactDeviation", "bNumAniRAINS", "FracEmHouse", "FracEmStorage", "FracEmAppl", "EmFracFert",
        "reducEmHouse", "reducEmStorage", "rLFRest", "p_factRunStor", "p_fracStorType", "p_litRevAmmoTechsAdd"}


def write(symbols: dict) -> list:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for name, rows in symbols.items():
        if not rows or name not in READ:
            continue
        nd = len(rows[0][0])
        cols = DIMS.get(name, [f"dim{i + 1}" for i in range(nd)])
        if len(cols) != nd:
            cols = [f"dim{i + 1}" for i in range(nd)]
        p = OUT / f"{name}.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols + ["value"])
            for keys, v in rows:
                w.writerow(list(keys) + [repr(v) if v == v else ""])
        written.append((p.name, len(rows), cols))
    return written


if __name__ == "__main__":
    allsym = {}
    for a in sys.argv[1:]:
        allsym.update(parse_dump(Path(a)))
    for name, n, cols in write(allsym):
        print(f"{name:34s} {n:7d} rows  columns: {', '.join(cols)}")
