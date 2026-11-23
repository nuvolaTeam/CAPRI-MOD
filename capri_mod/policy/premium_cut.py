"""CAPRI's premium cut (policy/prmcut.gms): the premiums per activity a region is paid, from the declared ones, when
a scheme's paid quantity or value exceeds its ceiling.

For each payment scheme s with a ceiling in a ceiling region R (an EU aggregate, a member state, a NUTS 1 region or a
regional unit; PSDPAY_T_R):

    Entl(r, a, s)   = LEVL(r, a) x w(r, a, s)                                 (the entitlements, w the weight)
    CEILACL(R, s)   = sum over R's units and activities with a declared premium of Entl
    CEILACV(R, s)   = sum of Entl x PRMD(r, a, s) x (1 + the technology factor) / 1000           (million EUR)
    CEILCUT(R, s)   = 1 / max(1, CEILACL / CEILLEV, CEILACV / CEILVAL)        (each term where its ceiling is above EPS)

A ceiling written EPS gives a cut of zero (the scheme pays nothing there). A unit takes the cut of the first level
above it that has one (member state from its EU aggregate, NUTS 1 from the member state, NUTS 2 from NUTS 1), 1
without one. Then

    PRME(r, a, s)   = PRMD(r, a, s) x CUTT(r, s) x (w(r, a, s), or the premium modification factor where it is set)
    PRME(r, a)      = sum over the schemes of the region (PSDPAY_T_R)

prmcut.gms aggregates the entitlements and values level by level (l. 66-140): an aggregate's are the sum of its
member states', a member state's of its units', a NUTS 1 region's of its NUTS 2 regions'. Each level uses its own
declared premium (PRMD) for the value: the units' for the member states and NUTS 1 / NUTS 2 regions, the member
states' for the EU aggregates. The premium modification factors' rescaling (l. 205-214, the Agenda 2000 shift of
animal payments to fodder activities) and the per-technology premiums (p_premiumsPerTechnology) are left to the
callers: the factors are applied as given and the technology factor is an input (zero without one).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from capri_mod.policy.equations._gams import EPS  # noqa: F401 (re-exported: the policy modules import it from here)
from capri_mod.policy.equations.prmcut import (
    p_premData_CEILACL, p_premData_CEILACV, p_premData_CEILCUT, p_premPaym_CUTT, p_premPaym_Entl, p_premPaym_PRME)


@dataclass
class CeilingRegions:
    """CAPRI's region hierarchy for the premium cut: each level's regions and their members (MAP_RR), in the order
    the cut is passed down (aggregates, member states, NUTS 1, units)."""
    aggregates: dict = field(default_factory=dict)        # {EU aggregate: [member states]}  (REGAGGP)
    member_states: dict = field(default_factory=dict)     # {member state: [units]}          (MAP_RR(MS, RU))
    nuts1: dict = field(default_factory=dict)             # {NUTS 1: [units]}                (MAP_RR(NUTS1A, NUTS2))

    def parents(self, unit: str) -> list:
        """The levels above a unit, nearest first: its NUTS 1 region, its member state, the member state's aggregates."""
        out = [n1 for n1, m in self.nuts1.items() if unit in m]
        ms = [s for s, m in self.member_states.items() if unit in m]
        out += ms
        out += [a for a, m in self.aggregates.items() if any(s in m for s in ms)]
        return out


def ceiling_cut(used_levels: float, used_value: float, ceil_lev=None, ceil_val=None):
    """CEILCUT of one region and scheme (prmcut.gms l. 203-211, capri_mod/policy/equations/prmcut.py): 1 / max(1, used
    / ceiling) over the ceilings that are set; EPS where a ceiling is EPS; None where the region has no ceiling of the
    scheme."""
    return p_premData_CEILCUT(used_levels, used_value, ceil_lev, ceil_val)


def premiums(levels: dict, prmd: dict, weight: dict, ceilings: dict, regions: CeilingRegions, modif: dict = None,
             techn: dict = None) -> dict:
    """The premium cut and the effective premiums (prmcut.gms).

    levels    {(unit, activity): LEVL}
    prmd      {(region, activity, scheme): declared premium}, the units' and the member states' (EUR per unit)
    weight    {(unit, activity, scheme): entitlement weight}
    ceilings  {(region, scheme): {"CEILLEV": value or EPS, "CEILVAL": value or EPS}}, at any level
    modif     {(unit, activity, scheme): premium modification factor} (optional)
    techn     {(region, activity, scheme): technology factor of the premium} (optional, 0)
    Returns {"cut": {(region, scheme): CEILCUT}, "cutt": {(unit, scheme): CUTT}, "prme": {(unit, activity, scheme): PRME},
    "used": {(region, scheme): (CEILACL, CEILACV)}}."""
    modif = modif or {}
    techn = techn or {}

    entl = {(u, a, s): p_premPaym_Entl(levels.get((u, a), 0.0), w) for (u, a, s), w in weight.items() if w > 0}

    def used(units, scheme, prmd_region=None):
        e_, p_, t_ = [], [], []
        for (u, a, s), e in entl.items():
            if s != scheme or u not in units:
                continue
            p = prmd.get((prmd_region or u, a, s))
            if p is None:
                continue
            e_.append(e)
            p_.append(p)
            t_.append(techn.get((prmd_region or u, a, s), 0.0))
        return p_premData_CEILACL(e_), p_premData_CEILACV(e_, p_, t_)

    members = {**{r: m for r, m in regions.member_states.items()}, **{r: m for r, m in regions.nuts1.items()}}
    cut, use = {}, {}
    for (r, s), c in ceilings.items():
        if r in regions.aggregates:
            # an aggregate's entitlements and values from its member states' (their entitlements, their PRMD)
            q = v = 0.0
            for ms in regions.aggregates[r]:
                qm, vm = used(regions.member_states.get(ms, []), s, prmd_region=ms)
                q += qm
                v += vm
        elif r in members:
            q, v = used(members[r], s)
        else:
            q, v = used([r], s)
        use[(r, s)] = (q, v)
        k = ceiling_cut(q, v, c.get("CEILLEV"), c.get("CEILVAL"))
        if k is not None:
            cut[(r, s)] = k

    units = {u for u, _ in levels}
    schemes = {s for (_, _, s) in prmd}
    cutt = {}
    for u in units:
        for s in schemes:
            k = cut.get((u, s))
            above = (cut.get((p, s)) for p in regions.parents(u)) if k is None else ()
            cutt[(u, s)] = p_premPaym_CUTT(k, above)

    prme = {}
    for (u, a, s), p in prmd.items():
        if u not in units or levels.get((u, a), 0.0) <= 0.0:
            continue
        prme[(u, a, s)] = p_premPaym_PRME(p, cutt[(u, s)], weight.get((u, a, s), 0.0), modif.get((u, a, s)))
    return {"cut": cut, "cutt": cutt, "prme": prme, "used": use}
