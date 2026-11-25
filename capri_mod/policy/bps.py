"""CAPRI's basic payment scheme per region (policy/implement_bps.gms with scen/Premiums/bps_convergence.gms): the
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

from capri_mod.policy.equations.implement_bps import (
    ord_bpsYear, p_bps_aiuv, p_bps_entitlements, p_bps_envelope, p_bps_envelopeOvershoot, p_bps_noConvergence,
    p_bps_targetIUV, p_premData_ceilacv_MS, p_premData_ceillev, p_premDataE_ceilval, p_premDataE_ceilval_fill,
    p_premDataE_pgsaps_linear, p_premDataE_pgsaps_lo, p_premDataE_pgsaps_lo_overshoot, p_premDataE_pgsaps_rest,
    p_premDataE_pgsaps_rule30, rbpsLo, rbpsUp, rcur, ybpsPre)
from capri_mod.supply import entitlements as _entl
from capri_mod.supply import inputs as _inputs

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
    """{year: {unit: IUV}} of one BPS region (implement_bps.gms l. 196-326, the statements in
    capri_mod/policy/equations/implement_bps.py): ceil {year: {unit: million EUR}}, entl {unit: entitlements}, opts the
    region's options."""
    years = sorted(years)
    pre = ybpsPre(years, opts["final"])
    units = rcur(entl, entl)
    out = {}
    env = {y: p_bps_envelope(ceil[y].values()) for y in years}
    tot_e = p_bps_entitlements(entl.values())
    aiuv = {y: p_bps_aiuv(env[y], tot_e) for y in years}
    iuv0 = {y: {u: p_bps_noConvergence(ceil[y].get(u, 0.0), entl[u]) for u in units} for y in years}
    fin = opts["final"]
    lo = [u for u in units if rbpsLo(iuv0[fin][u], p_bps_targetIUV(aiuv[fin], opts["target_share"]))]
    up = [u for u in units if rbpsUp(iuv0[fin][u], aiuv[fin])]
    for y in years:
        target = p_bps_targetIUV(aiuv[y], opts["target_share"])
        r = {u: p_premDataE_pgsaps_rest(iuv0[y][u]) for u in units}
        for u in lo:
            r[u] = p_premDataE_pgsaps_lo(iuv0[y][u], target, opts["gap"], ord_bpsYear(y), len(pre))

        def overshoot():
            return p_bps_envelopeOvershoot([entl[u] for u in units], [r[u] for u in units], env[y])

        if opts["linear"] and up:
            o = overshoot()
            e_up, x_up = [entl[u] for u in up], [iuv0[y][u] for u in up]
            for u in up:
                r[u] = p_premDataE_pgsaps_linear(iuv0[y][u], aiuv[y], o, e_up, x_up)
        if opts["rule30"]:
            for u in up:
                r[u] = p_premDataE_pgsaps_rule30(r[u], iuv0[y][u])
        if lo:
            o = overshoot()
            e_lo = [entl[u] for u in lo]
            for u in lo:
                r[u] = p_premDataE_pgsaps_lo_overshoot(r[u], o, e_lo)
        out[y] = r
    return out


def bps_rates(units, levels: dict, key: dict, year: int, d: dict = None, detail: bool = False):
    """{unit: dp_bps rate per level (EUR / ha)} of the simulation year for the member states with the BPS among the
    units' (implement_bps.gms, the year's rate the last reform year's, def_policy.gms). levels {(unit, activity):
    trend level}, key {unit: the unit's MTR payments, million EUR}. detail: also the units' ceilings of the year
    {(unit, "dp_bps"): {"CEILLEV": entitlements, "CEILVAL": the unit's share of the ceiling before the convergence,
    million EUR}} (implement_bps.gms l. 147-160)."""
    d = d or data()
    ent = _entl.data()
    saps = set(ent["settings"].get("saps", {}))
    years = list(range(2015, 2021))
    by_ms = defaultdict(list)
    from capri_mod.data.definitions import capri_ms
    for u in units:
        by_ms[capri_ms(u)].append(u)
    out, ceilings = {}, {}
    for ms, us in by_ms.items():
        if ms in saps or ms not in set(d["regions"].ms):
            continue
        entl = defaultdict(float)
        for u in us:
            lv = [v for (u_, a), v in levels.items() if u_ == u and a in d["mcact"]]
            if lv:
                entl[u] = p_premData_ceillev(lv)
        kms = {u: key.get(u, 0.0) for u in us}
        if not any(kms.values()):
            # no unit has MTR payments (Croatia: CAPRI's key for it is not found in the chain, KNOWN_ISSUES K142):
            # the entitlements as the key, a uniform IUV; for a member state of one unit CAPRI's result whatever its key
            kms = {u: entl[u] for u in us}
        ksum = p_premData_ceilacv_MS(kms.values())
        ceil = {}
        last = None
        for y in years:
            c = _entl.ms_ceilings(y, ent).get(ms, {}).get("dp_bps")
            c = p_premDataE_ceilval_fill(c, last)
            last = c
            ceil[y] = {u: p_premDataE_ceilval(kms[u], c, ksum) for u in us if kms.get(u) and ksum and c}
        for b, bu in bps_regions(ms, us, d).items():
            conv = converge({y: {u: ceil[y].get(u, 0.0) for u in bu} for y in years}, {u: entl[u] for u in bu}, years,
                            _options(ms, b, d))
            out.update(conv[min(max(years), year)])
        y = min(max(years), year)
        for u in us:
            if u in out:
                ceilings[(u, "dp_bps")] = {"CEILLEV": entl[u], "CEILVAL": ceil[y].get(u, 0.0)}
    return (out, ceilings) if detail else out
