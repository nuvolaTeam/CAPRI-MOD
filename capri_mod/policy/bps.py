"""CAPRI's basic payment scheme per region (policy/implement_bps.gms with scen/Premiums/bps_convergence.gms, P2c): the
member state's BPS ceiling of each year distributed to its regional units by their historical (MTR) payments, then
converged within each BPS region to its average unit value (IUV) by the member state's model.

For a member state with the BPS and each year of the reform (2015-2020; a year without a ceiling takes the year
before's):
  ceiling(r)    = key(r) / sum of the member state's keys x the member state's dp_bps ceiling (key: the unit's MTR
                  payments, sum PRME x Entl / 1000 of DPFRMS, DPFRMF, DPREG, DPSAPS at the simulation year's levels,
                  CAPRI's policyIUV.gdx, capri_mod/policy/mtr.py; without a key a unit has no ceiling; a member
                  state none of whose units has a key takes their entitlements as the key, K142)
  entl(r)       = the unit's trend level of CAPRI's crops (MCACT): its payment entitlements
  aiuv          = the BPS region's envelope (sum of its units' ceilings) x 1000 / its entitlements
  iuv0(r)       = ceiling(r) x 1000 / entl(r)                     (before convergence)
  target        = aiuv x the target share
then, with F the final year and the years before it in equal steps (min(1, (year - 2014) / (1 + years before F))):
  units below target in F:  iuv = iuv0 + (target - iuv0) x gap closure x step
  the others:               iuv = iuv0
  units above aiuv in F, linear model: iuv = aiuv + (iuv0 - aiuv) x (1 - overshoot / sum over them of entl x (iuv0 -
                            aiuv) / 1000), the overshoot being the envelope's
  30% rule:                 iuv >= 0.7 x iuv0 for them
  the overshoot left:       taken from the units below target, divided by their entitlements as implement_bps.gms
                            l. 309 writes it (million EUR over thousand ha, without the factor 1000: the envelope
                            stays overshot where the 30% rule binds: a CAPRI bug, kept as CAPRI computes it, KNOWN_ISSUES K141)
The year's rate (pgsaps of dp_bps, per level) is the simulation year's by def_policy.gms: the last year's, 2020.
The proportional model (bps_proportional) no member state uses; it is not ported.
"""
from __future__ import annotations

from collections import defaultdict

from capri_mod.supply import entitlements as _entl
from capri_mod.supply import inputs as _inputs

#: the 30% rule: an IUV above the average falls by at most 30% (implement_bps.gms l. 299-300)
RULE_30_FLOOR = 0.70


def _load(inp):
    def csv(name, where="policy"):
        return inp.csv(name, where, keep_default_na=False)

    mp = csv("capri/MAP_RR.csv", "codes")
    members = defaultdict(list)
    for r, m in zip(mp.region, mp.member):
        members[str(r)].append(str(m))
    return {"regions": csv("bps_convergence_regions.csv"), "options": csv("bps_convergence_options.csv"),
            "members": dict(members), "srnuts2": set(str(c) for c in csv("capri/SRNUTS2.csv", "codes").code),
            "mcact": set(str(c) for c in csv("capri/MCACT.csv", "codes").code)}


def data(inp=None) -> dict:
    """The member states' BPS regions and convergence options (bps_convergence_regions.csv, bps_convergence_options.csv,
    transcribed from bps_convergence.gms) and the region sets, read once per run."""
    inp = inp or _inputs.current()
    return inp.cached("bps_convergence", _load)


def bps_regions(ms: str, units, d: dict = None) -> dict:
    """{BPS region: [units]} of a member state (bps_region_to_ru): a region's units are those of the CAPRI region named
    (MAP_RR, itself included), REST the member state's units in no other region, EACH every NUTS 2 region its own."""
    d = d or data()
    units = list(units)
    rows = d["regions"][d["regions"].ms == ms]
    out = {}
    for b, of in zip(rows.bps_region, rows.members_of):
        if b == "EACH":
            for i, s in enumerate(u for u in units if u in d["srnuts2"]):
                out[f"rbps{i + 1}"] = [s]
        elif of != "REST":
            m = set(d["members"].get(of, [])) | {of}
            out.setdefault(b, []).extend(u for u in units if u in m)
    taken = {u for v in out.values() for u in v}
    for b, of in zip(rows.bps_region, rows.members_of):
        if of == "REST":
            out[b] = [u for u in units if u not in taken]
    return out


def _options(ms, b, d):
    o = d["options"]
    row = o[(o.ms == ms) & (o.bps_region == b)]
    if row.empty:
        row = o[(o.ms == ms) & (o.bps_region == "EACH")]
    r = row.iloc[0]
    return {"linear": bool(int(r.linear)), "rule30": bool(int(r.rule_30_percent)), "final": int(r.final_year),
            "target_share": float(r.target_share), "gap": float(r.gap_closure)}


def converge(ceil: dict, entl: dict, years, opts: dict) -> dict:
    """{year: {unit: IUV}} of one BPS region (implement_bps.gms l. 196-326): ceil {year: {unit: million EUR}}, entl
    {unit: entitlements}, opts the region's options."""
    years = sorted(years)
    pre = [y for y in years if y < opts["final"]]
    units = [u for u in entl if entl[u]]
    out = {}
    env = {y: sum(ceil[y].values()) for y in years}
    tot_e = sum(entl.values())
    aiuv = {y: env[y] * 1000.0 / tot_e if tot_e else 0.0 for y in years}
    iuv0 = {y: {u: ceil[y].get(u, 0.0) * 1000.0 / entl[u] for u in units} for y in years}
    fin = opts["final"]
    lo = [u for u in units if iuv0[fin][u] < aiuv[fin] * opts["target_share"]]
    up = [u for u in units if iuv0[fin][u] > aiuv[fin]]
    for y in years:
        step = min(1.0, (y - 2014) / (1 + len(pre)))
        target = aiuv[y] * opts["target_share"]
        r = {u: iuv0[y][u] for u in units}
        for u in lo:
            r[u] = iuv0[y][u] + (target - iuv0[y][u]) * opts["gap"] * step

        def overshoot():
            return sum(entl[u] * r[u] / 1000.0 for u in units) - env[y]

        if opts["linear"] and up:
            den = sum(entl[u] * (iuv0[y][u] - aiuv[y]) / 1000.0 for u in up)
            gap_up = sum(iuv0[y][u] - aiuv[y] for u in up)
            f = (1.0 - overshoot() / den) if gap_up else 0.0
            for u in up:
                r[u] = aiuv[y] + (iuv0[y][u] - aiuv[y]) * f
        if opts["rule30"]:
            for u in up:
                r[u] = max(r[u], iuv0[y][u] * RULE_30_FLOOR)
        if lo:
            # implement_bps.gms l. 309: million EUR over thousand ha (a CAPRI bug kept as CAPRI computes it, K141)
            e_lo = sum(entl[u] for u in lo)
            o = overshoot()
            for u in lo:
                r[u] -= o / e_lo
        out[y] = r
    return out


def bps_rates(units, levels: dict, key: dict, year: int, d: dict = None) -> dict:
    """{unit: dp_bps rate per level (EUR / ha)} of the simulation year for the member states with the BPS among the
    units' (implement_bps.gms, the year's rate the last reform year's, def_policy.gms). levels {(unit, activity):
    trend level}, key {unit: the unit's MTR payments, million EUR}."""
    d = d or data()
    ent = _entl.data()
    saps = set(ent["settings"].get("saps", {}))
    years = list(range(2015, 2021))
    by_ms = defaultdict(list)
    from capri_mod.data.definitions import capri_ms
    for u in units:
        by_ms[capri_ms(u)].append(u)
    out = {}
    for ms, us in by_ms.items():
        if ms in saps or ms not in set(d["regions"].ms):
            continue
        entl = defaultdict(float)
        for (u, a), v in levels.items():
            if u in us and a in d["mcact"]:
                entl[u] += v
        kms = {u: key.get(u, 0.0) for u in us}
        if not any(kms.values()):
            # no unit has MTR payments (Croatia: CAPRI's key for it is not found in the chain, KNOWN_ISSUES K142):
            # the entitlements as the key, a uniform IUV; for a member state of one unit CAPRI's result whatever its key
            kms = {u: entl[u] for u in us}
        ksum = sum(kms.values())
        ceil = {}
        last = None
        for y in years:
            c = _entl.ms_ceilings(y, ent).get(ms, {}).get("dp_bps")
            c = c if c else last
            last = c
            ceil[y] = {u: kms[u] * c / ksum for u in us if kms.get(u) and ksum and c}
        for b, bu in bps_regions(ms, us, d).items():
            conv = converge({y: {u: ceil[y].get(u, 0.0) for u in bu} for y in years}, {u: entl[u] for u in bu}, years,
                            _options(ms, b, d))
            out.update(conv[min(max(years), year)])
    return out
