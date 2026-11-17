"""CAPRI's Norwegian premiums (capri_mod/policy/norway.py; policy/norw_pol.gms, def_no_policy.gms, policy.gms) against
CAPRI's 2030 reference PRME (capri_data/validation/greendeal_2030/capri_marginal_terms_ref_2030.csv, used as a
check): every Norwegian unit and production activity, the direct payments only (the output payments pay nothing in
the simulation year, K144)."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import pytest

from capri_mod.policy import norway

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_marginal_terms_ref_2030.csv"


def _reference(units, mpact):
    prme, levl = {}, {}
    with open(REF, newline="") as f:
        for r in csv.DictReader(f):
            if r["region"] in units and r["activity"] in mpact:
                if r["item"] == "PRME":
                    prme[(r["region"], r["activity"])] = float(r["value"])
                elif r["item"] == "LEVL":
                    levl[(r["region"], r["activity"])] = float(r["value"])
    return prme, levl


def test_norways_2030_premiums_are_capris_reference():
    d = norway.data()
    with open(ROOT / "capri_data" / "codes" / "capri" / "MPACT.csv", newline="") as f:
        mpact = {r[0] for r in csv.reader(f)}
    prme, levl = _reference(set(d["units"]), mpact)
    tot = defaultdict(float)
    for (u, a, s), v in norway.norway_premiums(2030, d).items():
        tot[(u, a)] += v
    assert len(prme) > 100
    for k, v in prme.items():
        assert tot.get(k, 0.0) == pytest.approx(v, rel=1e-6), k
    # a rate where CAPRI reports none: the activity has no level in 2030 (NO070000's broilers)
    assert all(not levl.get(k) for k in set(tot) - set(prme))
    # the rate of a data base activity reaches its variants (def_no_policy.gms l. 56-60)
    assert tot[("NO080000", "BULL")] == tot[("NO080000", "BULH")] > 0
