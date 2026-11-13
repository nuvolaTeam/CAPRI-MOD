"""CAPRI's Norwegian premiums (policy/norw_pol.gms, policy/def_no_policy.gms, policy/policy.gms; P2): the national
rates of each payment group by year (NO000000) times the regional factors of the NUTS 2 units, as CAPRI computes them
for the simulation year.

- def_policy.gms carries each record to the simulation year: its last value up to the year (a cell written 0 is no
  record in GAMS, so the year before holds).
- def_no_policy.gms: a unit's rate is the national rate times its factor (l. 20-21), the national rate where it has no
  factor (l. 38-39); a data base activity's rate reaches its variants (DCOW -> DCOL, DCOH; BULF; HEIF: l. 56-60,
  codes/capri/DACT_TO_PACT.csv).
- policy.gms: DPNOR1-DPNOR5 (APPTYPE noDirPay, l. 344) pay that rate per activity unit, with no ceiling, so the
  effective premium is the rate. DPNOR6 and DPNOR7 (noPriceSup, l. 347-348) are paid per t of the activity's output,
  with the yields of p_dataCopy(rsNorw, pppact, o, %1), which l. 97 copies from DATA at the year's own column
  ("2030"), empty in CAPMOD (DATA holds "Y", "BAS", "TRD"): in the simulation they pay nothing, as here (CAPRI's 2030
  reference has no output payment in Norway's premiums; KNOWN_ISSUES K144: a CAPRI bug, kept as CAPRI computes it).

At sim_ini_21730's chain the 2030 premiums are CAPRI's reference PRME at every Norwegian unit and production activity
(capri_mod/tests/test_norway.py).
"""
from __future__ import annotations

from collections import defaultdict

from capri_mod.supply import inputs as _inputs

NATIONAL = "NO000000"


def _load(inp):
    t = inp.csv("norway_premiums.csv", "policy", keep_default_na=False)
    d2p = inp.csv("capri/DACT_TO_PACT.csv", "codes", keep_default_na=False)
    variants = defaultdict(list)
    for a, p in zip(d2p.dact, d2p.pact):
        variants[str(a)].append(str(p))
    mrr = inp.csv("capri/MAP_RR.csv", "codes", keep_default_na=False)
    units = sorted(str(m) for r, m in zip(mrr.region, mrr.member) if r == NATIONAL and m != NATIONAL)
    return {"table": t, "variants": dict(variants), "units": units}


def data(inp=None) -> dict:
    """Norway's tables (capri_data/<base year>/policy/norway_premiums.csv, build_norway_premiums.py), read once per run."""
    inp = inp or _inputs.current()
    return inp.cached("norway_premiums", _load)


def norway_premiums(year: int, d: dict = None) -> dict:
    """{(unit, activity, scheme): EUR per activity unit} of the year at Norway's units, the direct payments
    (DPNOR1-DPNOR5) per production activity; the output payments pay nothing in the simulation (see the module)."""
    d = d or data()
    t = d["table"]
    last = {}
    for k, r, y, s, c, v in zip(t.kind, t.region, t.year, t.scheme, t.code, t.value):
        y, v = int(y), float(v)
        if k != "pact" or v == 0.0 or y > year:
            continue
        key = (str(r), str(s), str(c))
        if key not in last or y > last[key][0]:
            last[key] = (y, v)
    rec = {k: v for k, (_, v) in last.items()}
    units = d["units"]                                   # MAP_RR("NO000000", ru)
    out = {}
    for (r, s, c), nat in rec.items():
        if r != NATIONAL:
            continue
        for u in units:
            f = rec.get((u, s, c))
            v = nat * f if f is not None else nat
            for a in d["variants"].get(c, [c]):
                out[(u, a, s)] = v
    return out
