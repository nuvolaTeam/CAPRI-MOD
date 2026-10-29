"""CAPRI's market supply Hessian (p_hessNQSupp) as its market model uses it.

The calibration export (elas_2_1730defaulta.csv) stores each region's Hessian at the calibration point ("CAL") with
one entry per pair of products: a cross term is stored as (x, y) or as (y, x), not both (USA: MAIZ's row carries
WHEA, WHEA's row does not carry MAIZ). CAPRI's market model completes it on loading (arm/market1.gms l. 539-574):

  1. tiny terms deleted: an off-diagonal term whose stored elasticity p_elasSupp is non-zero and at most 1e-6 in
     absolute value (l. 549);
  2. terms deleted where the row or the column is a product without a ProdNQ_ equation (l. 561; the set
     xx_no_prodNQ_equation of arm/market_model.gms l. 530-544: DDGS, the biofuels, the oils and cakes of the crushed
     seeds, the dairy products except raw milk, and for the regions with supply models FPRI, FENI, FEDE; the young
     animals are excluded from this step, l. 559-564);
  3. made symmetric: a missing term takes the transposed one (l. 574).

read_supply_hessian returns the completed terms {(region, x, y): h}. A builder that reads only the stored rows misses
the half of the cross terms stored under the other product's row.
"""
from __future__ import annotations

import re
from pathlib import Path

#: arm/market_model.gms l. 530-531 and arm/arm_sets.gms (XXBIOF, OIL, CAK, MLK): products without ProdNQ_
NO_PRODNQ = {"DDGS", "BIOE", "BIOD", "SOYO", "SUNO", "RAPO", "SOYC", "SUNC", "RAPC",
             "BUTT", "SMIP", "CHES", "FRMI", "CREM", "COCM", "WMIO", "CASE", "WHEP"}
#: l. 542-544: also without ProdNQ_ in the regions with supply models (RMSSUP)
NO_PRODNQ_RMSSUP = {"FPRI", "FENI", "FEDE"}
_PAT = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'CAL'\s+(\S+)")


def _num(s: str) -> float:
    s = s.rstrip(",").strip()
    return 0.0 if s.lower() in ("eps", "na", "undf", "") else float(s)


def _read(path: Path, name: str, keep) -> dict:
    out, cur = {}, None
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            if line.startswith("Parameter"):
                cur = line.split("(")[0].split()[1]
                continue
            if cur != name or not line.startswith("'"):
                continue
            m = _PAT.match(line)
            if m and keep(m.group(1)):
                out[(m.group(1), m.group(2), m.group(3))] = _num(m.group(4))
    return out


def read_supply_hessian(path: Path, keep_region, rmssup=()) -> dict:
    """CAPRI's p_hessNQSupp at CAL for the regions keep_region accepts, completed as arm/market1.gms does."""
    h = {k: v for k, v in _read(path, "p_hessNQSupp", keep_region).items() if v != 0.0}
    el = _read(path, "p_elasSupp", keep_region)
    rmssup = set(rmssup)
    for (r, x, y) in list(h):
        e = el.get((r, x, y), 0.0)
        if x != y and e != 0.0 and abs(e) <= 1e-6:
            del h[(r, x, y)]                                           # step 1
            continue
        no = NO_PRODNQ | (NO_PRODNQ_RMSSUP if r in rmssup else set())
        if x in no or y in no:
            del h[(r, x, y)]                                           # step 2
    for (r, x, y), v in list(h.items()):
        if (r, y, x) not in h:
            h[(r, y, x)] = v                                           # step 3
    return h
