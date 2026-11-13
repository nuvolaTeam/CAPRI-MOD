"""CAPRI's declared premiums per activity (policy/policy.gms, P2b): the premium a region's activity is declared under
each payment scheme (PRMD) and the activity's entitlement weight, from the year's premium declarations. prmcut.gms
(capri_mod/policy/premium_cut.py) then cuts them to the schemes' ceilings.

A declaration is a scheme's rate per premium group in a region (an EU aggregate, a member state, a NUTS 1 region or a
regional unit), with the scheme's application type there. policy.gms:

1. an activity belongs to a scheme where some region declares a rate above EPS for one of its groups (PSDPAY_T_A);
2. the rate of an activity (PRMR) in a region with a level of it: the sum of the region's rates over the activity's
   groups (a_psg); its application type: the region's own;
3. regions without a rate of their own take it from the level above, where they have a level of the activity: the
   member states from the EU-10/EU-15 aggregates (REGEU1015), then from the other aggregates (REGAGGP); the NUTS 1
   regions from their member state; the NUTS 2 regions from their NUTS 1 region (each the sum over the regions above
   it in R_RAGG). The application type and the entitlement weight (p_entlWght1) the same way where the region has a
   rate above EPS and none of its own; a rate or weight written EPS is the region's own (GAMS's EPS is nonzero in a
   condition) and stops the inheritance;
4. PRMD = PRMR x the application factor: 1 per level or per slaughtered head, the main yield / 1000 per yield, the
   historical yield (the cereals' where the activity has none) per historical yield, the livestock units per
   livestock unit; a rate written EPS gives none;
5. the units' PRMD where they have no level is 0; re-aggregated, weighted by the levels, to NUTS 1 and the member
   states (ntslvl) and to the EU aggregates (REGAGGP);
6. the entitlement weight: p_entlWght1 (1 where none, 0 where EPS) x the slaughtered share of the activity's heads
   (the slaughter coefficient / 1000) for the schemes per slaughtered head.

Left to P2c: the farm types (p_AggregNUTS2 is 0 in CAPMOD's NUTS 2 runs), Norway's schemes, the subsidies per unit of
output of the non-CAP payments (DPNONCAP: noncap_factor here, given by the caller), the set-aside floor of the
Agenda 2000 regime (DATA OSET Floor, end of policy.gms).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from capri_mod.policy.premium_cut import EPS

#: CAPRI's application types and the numbers policy.gms gives them to sum them over the levels above (l. 166-173)
APPTYPES = {"perLevl": 1, "perSlgthd": 2, "perYield": 3, "perHistY": 4, "perLiveStockUnit": 5}
_APPTYPE_CI = {k.lower(): v for k, v in APPTYPES.items()}    # GAMS's identifiers ignore case (perLivestockUnit)


def nonzero(x) -> bool:
    """A GAMS $-condition on a value: true for EPS and any number but zero."""
    return x == EPS or (x is not None and x != 0)


def above_eps(x) -> bool:
    """GAMS's "x gt eps": a positive number (EPS and zero are not)."""
    return x is not None and x != EPS and x > 0


def gams_sum(values):
    """GAMS's sum of values that may be EPS: the sum of the numbers; EPS where the terms are EPS and zeros only; None
    (no record) for no term or a zero sum."""
    total, eps = 0.0, False
    for v in values:
        if v == EPS:
            eps = True
        elif v:
            total += v
    if total != 0.0:
        return total
    return EPS if eps else None


def _need(table, name):
    """An input of an application type that occurs: missing entries are 0 as in GAMS, a missing table stops."""
    if table is None:
        raise ValueError(f"declared_premiums: a scheme's application type needs {name}, not given")
    return table


@dataclass
class PolicyRegions:
    """The regions policy.gms works on and CAPRI's links between them (codes/capri: MAP_RR, R_RAGG, REGEU1015,
    REGAGGP, MSAGG, NUTS1A, SRNUTS1), restricted to the regional units of the run."""
    units: list
    member_states: list
    nuts1: list
    eu1015: list
    aggregates: list
    members: dict = field(default_factory=dict)      # MAP_RR: region -> its members
    above: dict = field(default_factory=dict)        # R_RAGG: region -> the regions it belongs to (itself included)
    srnuts1: set = field(default_factory=set)

    @classmethod
    def from_codes(cls, units, inp=None) -> "PolicyRegions":
        from capri_mod.supply import inputs as _inputs
        inp = inp or _inputs.current()

        def one(name):
            return [str(c) for c in inp.csv(f"capri/{name}.csv", "codes", keep_default_na=False).code]

        units = list(units)
        mapping = inp.csv("capri/MAP_RR.csv", "codes", keep_default_na=False)
        ragg = inp.csv("capri/R_RAGG.csv", "codes", keep_default_na=False)
        members, above = defaultdict(list), defaultdict(set)
        for r, m in zip(mapping.region, mapping.member):
            members[r].append(m)
        for r, g in zip(ragg["region"], ragg["aggregate"]):
            above[r].add(g)
        ms = one("MSAGG")
        unit_ms = {u for u in units}
        used_ms = [m for m in ms if any(u in unit_ms for u in members.get(m, []))]
        return cls(units=units, member_states=used_ms, nuts1=one("NUTS1A"), eu1015=one("REGEU1015"),
                   aggregates=one("REGAGGP"), members=dict(members), above=dict(above), srnuts1=set(one("SRNUTS1")))


def _levels(regions: PolicyRegions, levels: dict, acts) -> dict:
    """The activity levels of the units, their NUTS 1 regions, member states and EU aggregates (policy.gms l. 129-137)."""
    units = set(regions.units)
    out = {(u, a): v for (u, a), v in levels.items() if u in units and a in acts and v}
    for n in regions.nuts1:
        below = [u for u in regions.members.get(n, []) if u in units] + ([n] if n in units else [])
        for a in acts:
            v = sum(levels.get((u, a), 0.0) for u in set(below))
            if v:
                out[(n, a)] = v
    for m in regions.member_states:
        below = [u for u in regions.members.get(m, []) if u in units]
        for a in acts:
            v = sum(levels.get((u, a), 0.0) for u in below)
            if v:
                out[(m, a)] = v
    for g in regions.aggregates:
        below = [m for m in regions.members.get(g, []) if m in regions.member_states]
        for a in acts:
            v = sum(out.get((m, a), 0.0) for m in below)
            if v:
                out[(g, a)] = v
    return out


def declared_premiums(declarations: dict, groups: dict, regions: PolicyRegions, levels: dict, *, entl_weight=None,
                      yields=None, hist_yields=None, slaughter=None, lu_units=None, noncap_factor=None,
                      ntslvl: bool = True) -> dict:
    """PRMD and the entitlement weights of the year (policy.gms).

    declarations  {(region, scheme): {"rates": {premium group: EUR or EPS}, "APPTYPE": an APPTYPES name}}
    groups        {premium group: [activities]} (PSG_TO_A)
    levels        {(unit, activity): level}
    entl_weight   {(region, activity, scheme): weight or EPS} (p_EntlWght1)
    yields        {(region, activity): the main output's yield} (PACT_TO_Y), for the schemes per yield
    hist_yields   {(region, activity): historical yield, HSTY} (the cereals' under "CERE"), per historical yield
    slaughter     {(region, activity): the slaughter coefficient, heads per 1000}, for the schemes per slaughtered head
    lu_units      {activity: livestock units}, for the schemes per livestock unit
    noncap_factor {(region, activity): sum over the outputs of yield / 1000 x the subsidy per unit}, for DPNONCAP
    Returns {"prmd": {(region, activity, scheme): EUR}, "weight": {(region, activity, scheme): w},
    "apptype": {(region, activity, scheme): number}, "schemes_of_region": {region: {schemes}}} for the units and the
    regions above them."""
    entl_weight = entl_weight or {}

    # 1. the activities of each scheme
    acts_of = defaultdict(set)
    for (_, s), d in declarations.items():
        for g, v in d.get("rates", {}).items():
            if above_eps(v):
                acts_of[s].update(groups.get(g, []))
    acts = set().union(*acts_of.values()) if acts_of else set()
    levl = _levels(regions, levels, acts)
    groups_of = defaultdict(list)
    for g, members in groups.items():
        for a in members:
            groups_of[a].append(g)

    all_regions = regions.units + [r for r in regions.nuts1 if r not in regions.units] + [
        m for m in regions.member_states if m not in regions.units and m not in regions.nuts1] + [
        g for g in regions.aggregates if g not in regions.member_states]

    # 2. each region's own rate and application type
    prmr, app, w1 = {}, {}, {}
    for (r, s), d in declarations.items():
        rates = d.get("rates", {})
        for a in acts_of.get(s, ()):
            if not levl.get((r, a)):
                continue
            v = gams_sum(rates.get(g) for g in groups_of[a])
            if v is not None:
                prmr[(r, a, s)] = v
                t = d.get("APPTYPE")
                if above_eps(v) and t:
                    app[(r, a, s)] = _APPTYPE_CI[t.lower()] if isinstance(t, str) else int(t)
    for (r, a, s), v in entl_weight.items():
        w1[(r, a, s)] = v

    def ups_of(r, parents):
        return [p for p in regions.above.get(r, ()) if p in parents and p != r]

    def each(targets, parents):
        parents = set(parents)
        for r in targets:
            ups = ups_of(r, parents)
            if ups:
                for s, acts_s in acts_of.items():
                    for a in acts_s:
                        if levl.get((r, a)):
                            yield (r, a, s), [(p, a, s) for p in ups]

    def inherit_rates(targets, parents):
        for k, ups in each(targets, parents):
            if not nonzero(prmr.get(k)):
                v = gams_sum(prmr.get(u) for u in ups)
                if v is not None:
                    prmr[k] = v

    def inherit_apptypes(targets, parents):
        for k, ups in each(targets, parents):
            if above_eps(prmr.get(k)) and not app.get(k):
                t = sum(app.get(u, 0) for u in ups)
                if t:
                    app[k] = t

    def inherit_weights(targets, parents):
        for k, ups in each(targets, parents):
            if above_eps(prmr.get(k)) and not nonzero(w1.get(k)):
                v = gams_sum(w1.get(u) for u in ups)
                if v is not None:
                    w1[k] = v

    # 3. down the levels (policy.gms l. 194-278, in its order): the member states' rates from REGEU1015, then from
    # REGAGGP, their application types and weights the same way; NUTS 1 from the member states; NUTS 2 from NUTS 1
    for step in (inherit_rates, inherit_apptypes, inherit_weights):
        step(regions.member_states, regions.eu1015)
        step(regions.member_states, regions.aggregates)
    for targets, parents in ((regions.nuts1, regions.member_states), (regions.units, regions.nuts1)):
        for step in (inherit_rates, inherit_weights, inherit_apptypes):
            step(targets, parents)

    # 4. the application factor and PRMD
    prmd, weight = {}, {}
    for k, v in prmr.items():
        if not above_eps(v):
            continue
        r, a, s = k
        t = app.get(k, 0)
        f = 0.0
        if t in (1, 2):
            f = 1.0
        elif t > 2:
            if t == 3:
                f += _need(yields, "yields").get((r, a), 0.0) * 0.001
            elif t == 4:
                h = _need(hist_yields, "hist_yields")
                f += h.get((r, a)) or h.get((r, "CERE"), 0.0)
            elif t == 5:
                f += _need(lu_units, "lu_units").get(a, 0.0)
            if s == "DPNONCAP":
                f += _need(noncap_factor, "noncap_factor").get((r, a), 0.0)
        if f:
            prmd[k] = v * f
        # 6. the entitlement weight
        w = w1.get(k)
        base = 1.0 if not nonzero(w) else (w if above_eps(w) else 0.0)
        if t == 2:
            base *= _need(slaughter, "slaughter").get((r, a), 0.0) * 0.001
        weight[k] = base

    # 5. re-aggregation to NUTS 1, the member states and the EU aggregates, weighted by the levels
    units = set(regions.units)
    for k in [k for k in prmd if k[0] in units and not levl.get((k[0], k[1]))]:
        prmd[k] = 0.0

    def reaggregate(r, below):
        for s, acts_s in acts_of.items():
            for a in acts_s:
                lv = levl.get((r, a), 0.0)
                if lv > 0:
                    v = sum(prmd.get((b, a, s), 0.0) * levl.get((b, a), 0.0) for b in below if prmd.get((b, a, s)))
                    if v:
                        prmd[(r, a, s)] = v / lv
                    else:
                        prmd.pop((r, a, s), None)
                else:
                    prmd.pop((r, a, s), None)

    if ntslvl:
        for n in regions.nuts1:
            reaggregate(n, [u for u in regions.members.get(n, []) if u in units])
        for m in regions.member_states:
            reaggregate(m, [n for n in regions.members.get(m, []) if n in regions.srnuts1])
    for g in regions.aggregates:
        reaggregate(g, [m for m in regions.members.get(g, []) if m in regions.member_states])

    by_region = defaultdict(set)
    for (r, a, s), v in prmd.items():
        if v:
            by_region[r].add(s)
    return {"prmd": prmd, "weight": weight, "apptype": app, "schemes_of_region": dict(by_region),
            "regions": all_regions}
