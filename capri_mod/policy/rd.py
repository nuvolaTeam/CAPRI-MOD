"""CAPRI's rural development (pillar 2) payments of the year (P2c): policy/extend_rd_baseline.gms and policy/rd_logic.gms,
called from scen/Premiums/rd/define_second_pillar_baseline.gms in CAP_2014_2020.gms's chain. They turn the public
money of the rural development programmes (rd_budget.gdx: planned and spent per region, year and RDP measure) into
CAPRI premium declarations: the ceilings, rates per premium group and application types of the less-favoured-area
payment (DPRD_LFA), the Natura 2000 payment (DPRD_N2K) and the agri-environment payments by farm type (DPRD_AE1-8,
Sweden's DPRD_Se*), and the entitlement weights of the animals; policy.gms (declared.py) and prmcut.gms
(premium_cut.py) then make them premiums per activity.

extend_rd_baseline.gms (the total public money only, rdSpendPublic: CAPRI's ceilings use it alone):
  1. the planned money of a year without a plan is the year before's, up to the year after the simulation year;
  2. each NUTS 2 region's weight in its member state's money per measure in 2007-2013: its share of the spend (rule 1),
     else of the spend on the measure's policy shock in 2000-2006 (rule 3), else CAPRI's key for new measures (rule
     4), the weights rescaled to sum to one by member state;
  3. the planned money not spent in 2007-2013 is spread to the years without spend: a NUTS 2 region's own, then its
     NUTS 1 region's and its member state's by the weights;
  4. every year after 2013 is a NUTS 2 region's average spend of 2007-2013.
rd_logic.gms:
  5. the regions with RD money (member states, their NUTS 1 and 2 regions); the money summed up from NUTS 2 to NUTS 1 and
     the member states where these have none of their own;
  6. the ceiling of a scheme in a year: the spend on its measures in the year's programme (psDpay_RDP_rdMeasure), the
     plan where nothing is spent, EPS without money (so that a higher level's declaration does not reach the region);
     the agri-environment money split by farm type by FADN's agri-environment euros (ae_lfa_fes.gdx), else by
     FADN's hectares outside LFA without agri-environment, else by the regions' levels;
  7. the rates per hectare: LFA 250 EUR x the region's LFA share of each land cover (clueLandPartition.gdx), Natura
     2000 500 EUR x its N2K share (grassland's to the grazing animals, PGGRZE), agri-environment by farm type FADN's
     expected payment per hectare in and out of LFA by the region's LFA share (at most 2000); per level;
  8. the agri-environment entitlement weights of the animals: their livestock units (the heavy dairy cows, bulls and
     heifers half: extensification); Natura 2000's the livestock units of all animals in the member states and units
     (RS; a NUTS 1 region's animals keep weight 1 in step 9's scaling);
  9. each region's rates of a scheme scaled to pay 1.5 times its ceiling at the levels (at most 2000 EUR); prmcut then
     cuts them to the ceiling;
 10. Sweden's expert data for 2007 to the simulation year (rd_spend_2007_2013_se.gdx, 2004-2013 kept): its LFA,
     grazing, ley and extensification measures at 300 EUR/ha replace the agri-environment payments.
The year's values are then each item's last one up to the year (def_policy.gms); the years before it are deleted
(del_policy.gms).

Not here: the technology factors of the Natura 2000 and agri-environment payments (rd_logic l. 235-241, 340-346: T2
paid more than T1), which the model carries as prem_diff_share of capri_mod/supply/techn_mix.py; the mitigation
measures of PSDPAY_RD (no RDP measure, so no ceiling); article 68's 2010 payments (scheme dp68*, not RD).
"""
from __future__ import annotations

from collections import defaultdict

from capri_mod.policy.premium_cut import EPS
from capri_mod.supply import inputs as _inputs

#: rd_logic.gms's caps and factors (l. 259, 270, 298-305, 319, 368-389)
AE_RATE_MAX = 2000.0          # EUR per ha: the agri-environment rate and the scaled rates at most
SCALE_OVER_CEILING = 1.5      # the rates are scaled to pay 1.5 times the ceiling at the levels (prmcut cuts them)
EXTENSIVE_SHARE = 0.5         # the heavy variants' share of the animals' agri-environment entitlement
EXTENSIVE_ANIMALS = ("DCOH", "BULH", "HEIH")
AE_DEFAULT_RATE = 100.0       # EUR per ha where FADN has no agri-environment payment of the member state
SE_EXPERT_RATE = 300.0        # EUR per ha of Sweden's expert measures


def _mul(x, f):
    """GAMS's product with a value that may be EPS (EPS times a number stays EPS)."""
    if x == EPS:
        return EPS
    return x * f


def _nz(x) -> bool:
    return x == EPS or bool(x)


def _load(inp):
    def csv(name, where="policy"):
        return inp.csv(name, where, keep_default_na=False)

    def one(name):
        return [str(c) for c in csv(f"capri/{name}.csv", "codes").code]

    mp = csv("capri/MAP_RR.csv", "codes")
    members = defaultdict(list)
    for r, m in zip(mp.region, mp.member):
        members[r].append(m)
    sets = csv("rd_sets.csv")
    lu = inp.csv("pipeline/captrd/dat/p_luunits.csv", "root", keep_default_na=False)
    return {
        "budget": csv("rd_budget.csv"), "years": csv("rd_programme_years.csv"),
        "scheme_measures": csv("rd_scheme_measures.csv"), "shock_measures": csv("rd_shock_measures.csv"),
        "keys": csv("rd_new_measure_keys.csv"), "land": csv("rd_land_partition.csv"), "fadn": csv("rd_fadn_ae.csv"),
        "sweden": csv("rd_sweden_expert.csv"), "settings": csv("rd_settings.csv"),
        "sets": {n: [(str(a), str(b)) for a, b in zip(g.a, g.b)] for n, g in sets.groupby("set")},
        "members": dict(members), "nuts0": one("NUTS0"), "srnuts1": set(one("SRNUTS1")),
        "srnuts2": set(one("SRNUTS2")), "srnuts2_ext": set(one("SRNUTS2_EXT")), "ms": one("MSAGG"),
        "nuts1a": set(one("NUTS1A")), "rd_schemes": one("PSDPAY_RD"), "ae_schemes": one("PSDPAY_AE"),
        "mcact": set(one("MCACT")),
        "lu": {str(a): float(v) for a, v in zip(lu.act, lu.value)}}


def data(inp=None) -> dict:
    """The RD chain's inputs (capri_data/<base year>/policy/rd_*.csv, build_rd_inputs.py; the region and scheme sets
    of codes/capri; the livestock units), read once per run."""
    inp = inp or _inputs.current()
    return inp.cached("rd_chain", _load)


# ------------------------------------------------------------------------------------------------------------------
# extend_rd_baseline.gms
# ------------------------------------------------------------------------------------------------------------------

def _num(x) -> float:
    """A value in GAMS's arithmetic and comparisons: EPS is zero."""
    return 0.0 if x == EPS or x is None else x


def _div(a, b):
    """GAMS's a / b with EPS (EPS / b stays EPS)."""
    if a == EPS:
        return EPS
    return a / b if a else None


def extend_budget(d: dict, target_year: int) -> dict:
    """The public RD money per (region, year, measure, "plan" or "spend") after extend_rd_baseline.gms (steps 1-4 of
    the module docstring), in million EUR; EPS where CAPRI's data or arithmetic gives EPS (a spend recorded as
    nothing)."""
    B = {}
    for r, y, m, ps, v, e in zip(d["budget"].region, d["budget"].year, d["budget"].measure, d["budget"].plan_spend,
                                 d["budget"].meur, d["budget"].eps):
        B[(str(r), int(y), str(m), str(ps))] = EPS if int(e) else float(v)
    rdp_years = defaultdict(list)
    for p, y in zip(d["years"].rdp, d["years"].year):
        rdp_years[str(p)].append(int(y))
    members = d["members"]
    nuts0 = d["nuts0"]
    in0 = {n: list(members.get(n, [])) for n in nuts0}
    runr = set(nuts0) | {r for n in nuts0 for r in in0[n] if r in d["srnuts1"] or r in d["srnuts2"]}
    measures = sorted({k[2] for k in B})
    years_all = sorted({k[1] for k in B})

    # 1. the plan carried forward to the year after the simulation year
    for y in range(max(2006, min(years_all) + 1), target_year + 2):
        for r in runr:
            for m in measures:
                if not _nz(B.get((r, y, m, "plan"))) and _nz(B.get((r, y - 1, m, "plan"))):
                    B[(r, y, m, "plan")] = B[(r, y - 1, m, "plan")]

    # the sums and counts per programme
    Sp, nobs = {}, {}
    for r in runr:
        for p, ys in rdp_years.items():
            for m in measures:
                for ps in ("plan", "spend"):
                    v = _gsum(B.get((r, y, m, ps)) for y in ys)
                    if v is not None:
                        Sp[(r, p, m, ps)] = v
                n = sum(1 for y in ys if _num(B.get((r, y, m, "spend"))) > 0)
                if n:
                    nobs[(r, p, m)] = n

    ext = d["srnuts2_ext"]
    below = {n: [s for s in in0[n] if s in ext] for n in nuts0}
    p07, p00 = "RDP 2007-2013", "RDP 2000-2006"

    # 2. the weights. Rule 1: the member state's spend the sum of its NUTS 2 regions'; their shares
    for n in nuts0:
        for p in rdp_years:
            for m in measures:
                v = _gsum(Sp.get((s, p, m, "spend")) for s in below[n])
                if v is not None:
                    Sp[(n, p, m, "spend")] = v
                else:
                    Sp.pop((n, p, m, "spend"), None)
    W = {}
    for n in nuts0:
        for m in measures:
            tot = _num(Sp.get((n, p07, m, "spend")))
            if tot > 0:
                for s in below[n]:
                    v = _div(Sp.get((s, p07, m, "spend")), tot) if _nz(Sp.get((s, p07, m, "spend"))) else None
                    if v is not None:
                        W[(s, m)] = v
    # rules 3 and 4, by member state and policy shock, where a region has no weight (EPS is one)
    shock_m = defaultdict(lambda: defaultdict(set))
    for sh, p, m in zip(d["shock_measures"].shock, d["shock_measures"].rdp, d["shock_measures"].measure):
        shock_m[str(sh)][str(p)].add(str(m))
    key = {(str(r), str(sh)): float(v) for r, sh, v in zip(d["keys"].region, d["keys"].shock, d["keys"].share)}
    for n in nuts0:
        for sh, by_p in shock_m.items():
            old = by_p.get(p00, set())
            tot = _gsum(Sp.get((n, p00, m1, "spend")) for m1 in old)
            for s in below[n]:
                for m in old & set(measures):
                    if _nz(W.get((s, m))):
                        continue
                    if _nz(tot):
                        num = _gsum(Sp.get((s, p00, m1, "spend")) for m1 in old)
                        if tot == EPS:
                            if num not in (None, EPS):
                                raise ValueError(f"extend_rd_baseline rule 3: {n} {sh} a share over EPS")
                            v = EPS if num == EPS else None
                        else:
                            v = _div(num, tot) if num is not None else None
                        if v is not None:
                            W[(s, m)] = v
                            continue
                    if key.get((s, sh)):
                        W[(s, m)] = key[(s, sh)]
    # rescaled by member state; the member state keeps the sum before the rescaling (CAPRI's p_rdSpendingPeriod)
    Wsum = {}
    for n in nuts0:
        for m in measures:
            t = _gsum(W.get((s, m)) for s in below[n])
            if t is None:
                continue
            Wsum[(n, m)] = t
            if t != EPS:
                for s in below[n]:
                    if (s, m) in W:
                        W[(s, m)] = _div(W[(s, m)], t)

    # 3. the money not spent in 2007-2013, spread over its years without spend (CAPRI writes their number "7 - nobs")
    y07 = rdp_years[p07]
    YEARS_OF_RDP = len(y07)

    def rest(r, m):
        return max(0.0, _num(Sp.get((r, p07, m, "plan"))) - _num(Sp.get((r, p07, m, "spend"))))

    def nob(r, m):
        return nobs.get((r, p07, m), 0)

    for s in ext:
        for m in measures:
            rs = rest(s, m)
            if _nz(W.get((s, m))) and rs and nob(s, m) < YEARS_OF_RDP:
                for y in y07:
                    if _num(B.get((s, y, m, "spend"))) == 0:
                        B[(s, y, m, "spend")] = rs / (YEARS_OF_RDP - nob(s, m))
    n1s = sorted(r for r in d["srnuts1"] if any(r in in0[n] for n in nuts0)
                 and _num(_gsum(Sp.get((r, p07, m, "plan")) for m in measures)))
    ms_with_plan = [n for n in nuts0 if _num(_gsum(Sp.get((n, p07, m, "plan")) for m in measures))]
    for parents, own_nobs in ((n1s, False), (ms_with_plan, True)):
        for r in parents:
            sub = [s for s in members.get(r, []) if s in ext]
            for m in measures:
                if not _nz(Sp.get((r, p07, m, "spend"))):
                    v = _gsum(Sp.get((s, p07, m, "spend")) for s in sub)
                    if v is not None:
                        Sp[(r, p07, m, "spend")] = v
                rs = rest(r, m)
                if not _nz(Wsum.get((r, m))):
                    v = _gsum(W.get((s, m)) for s in sub)
                    if v is not None:
                        Wsum[(r, m)] = v
                wr = _num(Wsum.get((r, m)))
                if not rs:
                    continue
                for s in sub:
                    ws = _num(W.get((s, m)))
                    if ws <= 0 or (nob(r, m) if own_nobs else nob(s, m)) >= YEARS_OF_RDP:
                        continue
                    for y in y07:
                        if _num(B.get((s, y, m, "spend"))) == 0:
                            B[(s, y, m, "spend")] = rs * ws / wr / (YEARS_OF_RDP - nob(s, m))

    # 4. after 2013: the NUTS 2 regions' average spend of 2007-2013
    s2 = [s for n in nuts0 for s in in0[n] if s in d["srnuts2"]]
    for s in s2:
        for m in measures:
            tot = _gsum(B.get((s, y, m, "spend")) for y in y07)
            ave = EPS if tot == EPS else (tot / len(y07) if tot else None)
            for y in range(2014, target_year + 2):
                if ave is not None:
                    B[(s, y, m, "spend")] = ave
                else:
                    B.pop((s, y, m, "spend"), None)
    return B


# ------------------------------------------------------------------------------------------------------------------
# rd_logic.gms
# ------------------------------------------------------------------------------------------------------------------

def _gsum(values):
    """GAMS's sum with EPS terms: the sum of the numbers, EPS where only EPS and zeros, None for nothing."""
    tot, eps = 0.0, False
    for v in values:
        if v == EPS:
            eps = True
        elif v:
            tot += v
    return tot if tot else (EPS if eps else None)


def rd_declarations(levels: dict, year: int, groups: dict, d: dict = None, budget: dict = None,
                    base_weights: dict = None) -> dict:
    """The RD schemes' declarations of the year (steps 5-10 of the module docstring and def_policy.gms's fill):
    {"declarations": {(region, scheme): {"rates": {group: EUR}, "APPTYPE": "perLevl"}}, "ceilings": {(region,
    scheme): {"CEILVAL": million EUR or EPS}}, "entl_weight": {(region, activity, scheme): weight}}. The weights are
    those of the chain after rd_logic (the restart file's with rd_logic's own): they scale its rates and serve the
    base-year pass of calc_mtr_top.gms, but CAP_2014_2020.gms l. 77 kills them before the year's policy.gms, where
    every weight is 1.

    levels   {(unit, activity): level}, DATA(..., "LEVL", "Y") of the regional units at the time the chain runs (the
             NUTS 1 regions' and member states' are their sums)
    groups   {premium group: [activities]} (PSG_TO_A after the chain's redefinitions, cap14_premiums.data())
    budget   extend_budget's output (computed here when not given)
    base_weights the entitlement weights the chain starts from (sim_ini's p_EntlWght1, cap14_premiums.
             entitlement_weights()): rd_logic writes its own over them"""
    d = d or data()
    B = budget if budget is not None else extend_budget(d, year)
    members = d["members"]
    rdp_of = defaultdict(list)
    for p, y in zip(d["years"].rdp, d["years"].year):
        rdp_of[int(y)].append(str(p))
    rd_years = sorted(rdp_of)
    measures_of = defaultdict(lambda: defaultdict(set))
    for s, p, m in zip(d["scheme_measures"].scheme, d["scheme_measures"].rdp, d["scheme_measures"].measure):
        measures_of[str(s)][str(p)].add(str(m))
    sets = d["sets"]
    ae_tf8 = defaultdict(list)
    for s, t in sets.get("dpae_tf8", []):
        ae_tf8[s].append(t)
    pg_tf8 = defaultdict(list)
    for g, t in sets.get("psgroup_tf8", []):
        pg_tf8[t].append(g)
    tf8_lc = defaultdict(list)
    for t, lc in sets.get("tf8_lc", []):
        tf8_lc[t].append(lc)
    rdmax = {str(k): float(v) for i, k, v in zip(d["settings"].item, d["settings"].key, d["settings"].value)
             if i == "rd_max"}
    lu = d["lu"]
    ae = [s for s in d["ae_schemes"] if s in ae_tf8]
    rd_schemes = d["rd_schemes"]

    # 5. the regions with RD money and their money summed up where they have none
    money = defaultdict(float)
    for (r, y, m, ps), v in B.items():
        if v:
            money[r] += 1
    rd_ms = [m for m in d["ms"] if any(money.get(r) for r in members.get(m, []) + [m])]
    runr = set(rd_ms)
    for m in rd_ms:
        runr |= {r for r in members.get(m, []) if r in d["srnuts1"] or r in d["srnuts2"]}
    B = dict(B)
    keys = {(m, ps) for (_, _, m, ps) in B}
    for y in rd_years:
        for r in sorted(runr & d["srnuts1"]):
            sub = [s for s in members.get(r, []) if s in d["srnuts2"] and s in runr]
            for m, ps in keys:
                if not _nz(B.get((r, y, m, ps))):
                    v = _gsum(B.get((s, y, m, ps)) for s in sub)
                    if v is not None:
                        B[(r, y, m, ps)] = v
        for r in rd_ms:
            sub = [s for s in members.get(r, []) if s in d["srnuts1"] and s in runr]
            for m, ps in keys:
                if not _nz(B.get((r, y, m, ps))):
                    v = _gsum(B.get((s, y, m, ps)) for s in sub)
                    if v is not None:
                        B[(r, y, m, ps)] = v

    # the land partition summed to NUTS 1 and the member states, then the policy areas' shares of each land cover
    LP = defaultdict(float)
    for r, lc, t, v in zip(d["land"].region, d["land"].land_cover, d["land"].area_type, d["land"].kha):
        LP[(str(r), str(lc), str(t))] = float(v)
    lcs = {(lc, t) for (_, lc, t) in LP}
    for r in sorted(runr & d["srnuts1"]) + rd_ms:
        sub = [s for s in members.get(r, []) if s in d["srnuts2"]]
        for lc, t in lcs:
            v = sum(LP.get((s, lc, t), 0.0) for s in sub)
            if v:
                LP[(r, lc, t)] = v
            else:
                LP.pop((r, lc, t), None)
    share = {}
    for (r, lc, t), v in LP.items():
        if r in runr and t != "Total" and LP.get((r, lc, "Total")):
            share[(r, lc, t)] = v / LP[(r, lc, "Total")]

    # the levels of the regions run: the units', the NUTS 1 regions' and member states' sums
    lev = defaultdict(float)
    for (u, a), v in levels.items():
        lev[(u, a)] += v
    acts = {a for _, a in levels}
    for r in sorted(runr):
        if (r in d["nuts1a"] or r in d["ms"]) and not any((r, a) in levels for a in acts):
            sub = [s for s in members.get(r, []) if s in d["srnuts2"]]
            for a in acts:
                v = sum(levels.get((s, a), 0.0) for s in sub)
                if v:
                    lev[(r, a)] = v

    # FADN completed: Belgium-Luxembourg, the totals over the farm types and over in / out of LFA
    F = defaultdict(float)
    for ms, t, lfa, aes, unit, v in zip(d["fadn"].ms, d["fadn"].farm_type, d["fadn"].lfa, d["fadn"].ae,
                                       d["fadn"].unit, d["fadn"].value):
        F[(str(ms), str(t), str(lfa), str(aes), str(unit))] = float(v)
    for k in [k for k in F if k[0] in ("BE000000", "LU000000")]:
        F[("BL000000",) + k[1:]] += F[k]
        if k[0] == "LU000000":
            F[("BL400000",) + k[1:]] = F[k]
    regions_f = {k[0] for k in F}
    tf8 = sorted({k[1] for k in F if k[1] != "Total"})
    for r in regions_f:
        for lfa in ("LFA", "NoLFA"):
            for aes in ("AE", "NoAE"):
                for unit in ("Ha", "EUR"):
                    v = sum(F.get((r, t, lfa, aes, unit), 0.0) for t in tf8)
                    if v:
                        F[(r, "Total", lfa, aes, unit)] = v
        for t in tf8 + ["Total"]:
            for aes in ("AE", "NoAE"):
                for unit in ("Ha", "EUR"):
                    v = F.get((r, t, "LFA", aes, unit), 0.0) + F.get((r, t, "NoLFA", aes, unit), 0.0)
                    if v:
                        F[(r, t, "Tot", aes, unit)] = v

    def in_ms(ms):
        return [r for r in members.get(ms, []) if r in runr]

    mcact = d["mcact"]

    def crop_level(r, tfs):
        return sum(lev.get((r, a), 0.0) for t in tfs for g in pg_tf8.get(t, []) for a in groups.get(g, [])
                   if a in mcact)

    # the agri-environment payments' expected rate per ha in and out of LFA (FADN; 100 EUR without any)
    ae_lfa = {}
    for ms in rd_ms:
        for t in tf8 + ["Total"]:
            for lfa in ("LFA", "NoLFA", "Tot"):
                ha = F.get((ms, t, lfa, "AE", "Ha"), 0.0) + F.get((ms, t, lfa, "NoAE", "Ha"), 0.0)
                if ha:
                    v = F.get((ms, t, lfa, "AE", "EUR"), 0.0) / ha
                    if v:
                        ae_lfa[(ms, t, lfa)] = v
        if not any(k[0] == ms for k in ae_lfa):
            for t in tf8 + ["Total"]:
                for lfa in ("LFA", "NoLFA", "Tot"):
                    ae_lfa[(ms, t, lfa)] = AE_DEFAULT_RATE

    # 6-7 per year: P[y] {(region, scheme, item): value}, item CEILVAL, APPTYPE or a premium group
    P = {}
    for y in rd_years:
        ceil = {}
        for r in runr:
            for s in rd_schemes:
                terms = []
                for p in rdp_of[y]:
                    for m in measures_of.get(s, {}).get(p, ()):
                        sp = B.get((r, y, m, "spend"))
                        terms.append(sp if _nz(sp) else B.get((r, y, m, "plan")))
                        terms.append(EPS)
                v = _gsum(terms)
                if v is not None:
                    ceil[(r, s)] = v
        # the agri-environment money split by farm type
        for ms in rd_ms:
            tot = F.get((ms, "Total", "Tot", "AE", "EUR"), 0.0)
            if tot:
                for s in ae:
                    f = sum(F.get((ms, t, "Tot", "AE", "EUR"), 0.0) for t in ae_tf8[s]) / tot
                    for r in in_ms(ms):
                        if (r, s) in ceil:
                            ceil[(r, s)] = _mul(ceil[(r, s)], f) if f else None
            if sum(F.get((ms, t, "Tot", "AE", "EUR"), 0.0) for t in tf8 + ["Total"]) == 0:
                ha_any = sum(F.get((ms, t, "NoLFA", "NoAE", "Ha"), 0.0) for t in tf8 + ["Total"])
                ha_all = sum(F.get((ms, t, "NoLFA", "NoAE", "Ha"), 0.0) for t in tf8)
                if ha_any:
                    for s in d["ae_schemes"]:
                        f = sum(F.get((ms, t, "NoLFA", "NoAE", "Ha"), 0.0) for t in ae_tf8.get(s, [])) / ha_all
                        for r in in_ms(ms):
                            if ceil.get((r, s)) is not None:
                                ceil[(r, s)] = _mul(ceil[(r, s)], f) if f else None
                if sum(F.get((ms, t, "Tot", "AE", "EUR"), 0.0) + F.get((ms, t, "NoLFA", "NoAE", "Ha"), 0.0)
                       for t in tf8 + ["Total"]) == 0:
                    for r in in_ms(ms):
                        tot_l = crop_level(r, tf8)
                        if tot_l:
                            for s in d["ae_schemes"]:
                                if ceil.get((r, s)) is not None:
                                    f = crop_level(r, ae_tf8.get(s, [])) / tot_l
                                    ceil[(r, s)] = _mul(ceil[(r, s)], f) if f else None
        Py = {}
        for (r, s), v in ceil.items():
            if v is not None:
                Py[(r, s, "CEILVAL")] = v
        # LFA and Natura 2000
        for r in runr:
            if _nz(Py.get((r, "DPRD_LFA", "CEILVAL"))):
                for lc in ("PGANNC", "PGGRAS", "PGPERM"):
                    v = rdmax["LFA"] * share.get((r, lc, "LFA"), 0.0)
                    if v:
                        Py[(r, "DPRD_LFA", lc)] = v
                Py[(r, "DPRD_LFA", "APPTYPE")] = "perLevl"
            if _nz(Py.get((r, "DPRD_N2K", "CEILVAL"))):
                for lc in ("PGANNC", "PGPERM"):
                    v = rdmax["N2K"] * share.get((r, lc, "N2K"), 0.0)
                    if v:
                        Py[(r, "DPRD_N2K", lc)] = v
                v = rdmax["N2K"] * share.get((r, "PGGRAS", "N2K"), 0.0)
                if v:
                    Py[(r, "DPRD_N2K", "PGGRZE")] = v
                Py[(r, "DPRD_N2K", "APPTYPE")] = "perLevl"
        # agri-environment by farm type
        for ms in rd_ms:
            for s in ae:
                for t in ae_tf8[s]:
                    if not (ae_lfa.get((ms, t, "LFA")) or ae_lfa.get((ms, t, "NoLFA"))):
                        continue
                    for r in in_ms(ms):
                        if not _nz(Py.get((r, s, "CEILVAL"))):
                            continue
                        v = min(AE_RATE_MAX, sum(
                            share.get((r, lc, "LFA"), 0.0) * ae_lfa.get((ms, t, "LFA"), 0.0)
                            + (1 - share.get((r, lc, "LFA"), 0.0)) * ae_lfa.get((ms, t, "NoLFA"), 0.0)
                            for lc in tf8_lc.get(t, [])))
                        for g in pg_tf8.get(t, []):
                            if v:
                                Py[(r, s, g)] = v
        for r in runr:
            for s in d["ae_schemes"]:
                if _nz(Py.get((r, s, "CEILVAL"))):
                    Py[(r, s, "APPTYPE")] = "perLevl"
        P[y] = Py

    # 8. the entitlement weights, over the restart file's (CAPRI does not reset p_entlWght1): Natura 2000 the
    # livestock units of every animal in the supply model's regions (RS: the member states and units, not NUTS 1);
    # agri-environment those of the animals of a group with a rate
    # in any year, the heavy dairy cows, bulls and heifers half
    W1 = dict(base_weights or {})
    for r in set(d["ms"]) | d["srnuts2"]:
        for a, v in lu.items():
            if v:
                W1[(r, a, "DPRD_N2K")] = v
    for (r, s, g), v in [(k, v) for y in rd_years for k, v in P[y].items()]:
        if s in d["ae_schemes"] and g.startswith("PG") and _nz(v) and r in runr:
            for a in groups.get(g, []):
                if a in lu and lu[a]:
                    W1[(r, a, s)] = lu[a]
    for k in list(W1):
        if k[2] in d["ae_schemes"] and k[1] in EXTENSIVE_ANIMALS and k[0] in runr and _nz(W1[k]):
            W1[k] = _mul(W1[k], EXTENSIVE_SHARE)

    # 9. the rates scaled to pay 1.5 times the ceiling at the levels
    for y in rd_years:
        Py = P[y]
        by_rs = defaultdict(dict)
        for (r, s, g), v in Py.items():
            if g not in ("CEILVAL", "APPTYPE") and s in rd_schemes:
                by_rs[(r, s)][g] = v
        for (r, s), rr in by_rs.items():
            c = Py.get((r, s, "CEILVAL"))
            f = 0.0
            if r in runr and _nz(c):
                tot = 0.0
                for g, v in rr.items():
                    if not _nz(v):
                        continue
                    for a in groups.get(g, []):
                        lv = lev.get((r, a), 0.0)
                        w = W1.get((r, a, s))
                        if lv:
                            tot += lv * (1.0 if not _nz(w) else (0.0 if w == EPS else w)) * (0.0 if v == EPS else v) * 0.001
                f = (EPS if c == EPS else c / tot) if tot > 0 else 0.0
            for g, v in rr.items():
                x = EPS if (f == EPS and _nz(v)) or (v == EPS and f) else ((v * f) if f else 0.0)
                if x == EPS:
                    Py[(r, s, g)] = EPS
                elif x:
                    Py[(r, s, g)] = min(AE_RATE_MAX, x * SCALE_OVER_CEILING)
                else:
                    Py.pop((r, s, g), None)

    # 10. Sweden's expert data from 2007 to the simulation year (its years from 2014 not trusted, deleted)
    se_regions = {"SE000000"} | {s for s in members.get("SE000000", []) if s in d["srnuts2"]}
    se = defaultdict(dict)
    for r, yy, s, v in zip(d["sweden"].region, d["sweden"].year, d["sweden"].scheme, d["sweden"].ceiling_meur):
        if int(yy) < 2014 and float(v):
            se[(str(r), int(yy))][str(s)] = float(v)
    expert_rates = {"DPRD_LFA": ("PGGRAS", "PGSILA"), "DPRD_SeBete": ("PGGRAS",), "DPRD_SeVall": ("PGSILA",),
                    "DPRD_SeExte": ("PGFRM",)}
    for y in rd_years:
        if not 2007 <= y <= year:
            continue
        Py = P[y]
        for k in [k for k in Py if k[0] in se_regions]:
            r, s, it = k
            if s in d["ae_schemes"]:
                if it == "CEILVAL" and _nz(Py[k]):
                    Py[k] = EPS
                elif it != "CEILVAL":
                    del Py[k]
            elif s == "DPRD_LFA" and it not in ("CEILVAL", "APPTYPE") and _nz(Py[k]):
                Py[k] = EPS
        for r in se_regions:
            for s, c in se.get((r, y), {}).items():
                Py[(r, s, "CEILVAL")] = c
                Py[(r, s, "APPTYPE")] = "perLevl"
                for g in expert_rates.get(s, ()):
                    Py[(r, s, g)] = SE_EXPERT_RATE

    # def_policy.gms: each item its last nonzero value (EPS counts) up to the year; del_policy.gms deletes the rest
    items = {}
    for y in rd_years:
        if y <= year:
            for k, v in P[y].items():
                if _nz(v):
                    items[k] = v
    decl, ceilings = {}, {}
    for (r, s, it), v in items.items():
        x = decl.setdefault((r, s), {"rates": {}})
        if it == "CEILVAL":
            ceilings[(r, s)] = {"CEILVAL": v}
        elif it == "APPTYPE":
            x["APPTYPE"] = v
        else:
            x["rates"][it] = v
    return {"declarations": decl, "ceilings": ceilings, "entl_weight": W1}
