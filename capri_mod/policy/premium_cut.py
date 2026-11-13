"""CAPRI's premium cut (policy/prmcut.gms, P2a): the premiums per activity a region is paid, from the declared ones, when
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

#: CAPRI's EPS as a value (a ceiling written EPS: the scheme pays nothing in the region)
EPS = "EPS"


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


def _ratio(used: float, ceiling) -> float:
    return used / ceiling if isinstance(ceiling, (int, float)) and ceiling > 0 else 0.0


def ceiling_cut(used_levels: float, used_value: float, ceil_lev=None, ceil_val=None):
    """CEILCUT of one region and scheme: 1 / max(1, used / ceiling) over the ceilings that are set; EPS where a
    ceiling is EPS; None where the region has no ceiling of the scheme."""
    if ceil_lev == EPS or ceil_val == EPS:
        return EPS
    if ceil_lev is None and ceil_val is None:
        return None
    return 1.0 / max(1.0, _ratio(used_levels, ceil_lev), _ratio(used_value, ceil_val))


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

    entl = {(u, a, s): levels.get((u, a), 0.0) * w for (u, a, s), w in weight.items() if w > 0}

    def used(units, scheme, prmd_region=None):
        q = v = 0.0
        for (u, a, s), e in entl.items():
            if s != scheme or u not in units:
                continue
            p = prmd.get((prmd_region or u, a, s))
            if p is None:
                continue
            q += e
            v += e * p * (1.0 + techn.get((prmd_region or u, a, s), 0.0)) * 0.001
        return q, v

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
            if k is None:
                k = next((cut[(p, s)] for p in regions.parents(u) if (p, s) in cut), 1.0)
            cutt[(u, s)] = 0.0 if k == EPS else k

    prme = {}
    for (u, a, s), p in prmd.items():
        if u not in units or levels.get((u, a), 0.0) <= 0.0:
            continue
        f = modif.get((u, a, s)) or weight.get((u, a, s), 0.0)
        prme[(u, a, s)] = p * cutt[(u, s)] * f
    return {"cut": cut, "cutt": cutt, "prme": prme, "used": use}
