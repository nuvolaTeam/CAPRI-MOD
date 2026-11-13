"""CAPRI's 2004-2013 premium regime as its CAP 2014-2020 chain evaluates it for the BPS's historical key (P2c, port A):
pol_input/mtr_until2013.gms (run by CAP_2014_2020.gms through mtr_RD.gms), policy/calc_mtr_top.gms and
policy/calc_mtr.gms, then the pass CAP_2014_2020.gms l. 50-66 writes to policyIUV.gdx.

1. The declarations (mtr_series): sim_ini_21730's time series of the schemes the key needs, with mtr_until2013.gms
   executed on it in its order: its literal assignments (mtr_declarations.csv, line > 0) and its other assignments,
   ported below as rules at their lines (_RULES). A value assigned 0 deletes the record (GAMS stores no zero), EPS
   and NA are records (NA: policy.gms reads it as missing, l. 25).
2. The year (declarations_of_year): def_policy.gms gives each record its last value up to the simulation year (EPS and
   NA count); calc_mtr_top.gms l. 94-119 then fills the member states from EU015000 and EU025000 and BL400000 from
   BL000000, and l. 159-186 scales the EU-10's Agenda 2000 schemes to the SAPS budget (DPMTR's ceiling).
3. The base-year payments (base_payments): policy.gms and prmcut.gms with the year's declarations at the base year's
   data (calc_mtr_top.gms l. 188-206: levels, the main yields and the young animals' inputs at BAS, the EU-10's and
   BUR's levels at TRD; the historical yields at Y) and the payments per scheme (aggreg_ppepay.gms: million EUR).
4. The decoupled budgets (decoupled_budgets): the modulation (calc_mtr_top.gms l. 220-230, by PSGG_TO_P and
   p_percAffByModulation's total), the national ceiling's correction (calc_mtr.gms l. 40-82), the budget of each
   decoupling target (l. 259-287) by the coupling degree of the year (mtr_until2013.gms l. 974-991) and the targets
   (l. 1554-1581 with calc_mtr_top.gms l. 47-68); the greening share is 0 (policy_sets.gms kills it).
5. The decoupled schemes (decoupled_declarations): DPFRMS and DPFRMF per unit (calc_mtr.gms l. 298-316), DPREG per
   member state or NUTS 1 region by p_premToDDTargetNuts (l. 369-570), all per level.
6. The key (mtr_key): policy.gms and prmcut.gms at the simulation year's levels with those schemes; implement_bps.gms
   l. 147-150: sum over PSDPAY_MTR of PRME x Entl / 1000 per unit (million EUR).

Not ported, as they touch none of the key's schemes: the coupled remainder's rescaling (calc_mtr.gms l. 105-224, it
changes only coupled schemes), the agri-environment boost (l. 230-250, off), the EU flat rate (l. 324-358: no world
region has a p_premToDDTargetNuts), the greening top-up (l. 584-646, share 0), the endogenous cut's limits (l. 658-745,
the supply model's), the fallow-land variants (l. 765-813), the farm types (p_AggregNUTS2 0) and mtr_until2013.gms's
DPCN, DPENERCRP, DPADDSHGM, DPIRSCOW, DPNONCAP and set-aside statements and its RDel deletion (regions outside the
run).
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from capri_mod.policy.declared import PolicyRegions, declared_premiums, nonzero
from capri_mod.policy.premium_cut import EPS, CeilingRegions, premiums
from capri_mod.supply import inputs as _inputs

#: GAMS's NA in p_premDataE (agenda.gms l. 1225: "treated as a missing value" by policy.gms l. 25)
NA = "NA"


def _load(inp):
    def csv(name, where="policy"):
        return inp.csv(name, where, keep_default_na=False)

    def codes(name):
        return [str(c) for c in csv(f"capri/{name}.csv", "codes").code]

    mp = csv("capri/MAP_RR.csv", "codes")
    members = defaultdict(set)
    for r, m in zip(mp.region, mp.member):
        members[str(r)].add(str(m))
    sets = csv("mtr_sets.csv")
    st = defaultdict(list)
    for s, m in zip(sets.set, sets.member):
        st[str(s)].append(str(m))
    aggregates = set(codes("REGAGGP")) | set(codes("REGEU1015"))
    return {
        "decl": csv("mtr_declarations.csv"), "tables": csv("mtr_ceiling_tables.csv"),
        "coupling": csv("mtr_coupling.csv"), "targets": csv("mtr_dd_targets.csv"),
        "target_rules": csv("mtr_dd_target_rules.csv"), "nuts": csv("mtr_dd_nuts.csv"),
        "modulation": csv("mtr_modulation.csv"), "classes": csv("mtr_modulation_classes.csv"),
        "base": csv("mtr_base_data.csv"), "modif": csv("mtr_modif.csv"), "lu": csv("mtr_lu_units.csv"),
        "rules": csv("mtr_rules.csv"), "settings": csv("mtr_settings.csv"),
        "sets": dict(st), "members": dict(members), "ms": codes("MSAGG"), "aggregates": aggregates,
        "mcact": set(codes("MCACT")), "groups": csv("capri/PSG_TO_A.csv", "codes")}


def data(inp=None) -> dict:
    """The MTR tables (capri_data/<base year>/policy/mtr_*.csv, build_mtr_inputs.py), read once per run."""
    inp = inp or _inputs.current()
    return inp.cached("mtr", _load)


def _value(v, special):
    if special == "EPS":
        return EPS
    if special == "NA":
        return NA
    if special == "APPTYPE":
        return str(v)
    return float(v)


def _num(v) -> float:
    """A value in GAMS arithmetic: EPS 0, no record 0 (NA, which propagates, does not reach the rules that compute)."""
    if v is None or v == EPS:
        return 0.0
    if v == NA:
        raise ValueError("mtr: NA in arithmetic")
    return float(v)


class _Series:
    """p_premDataE as GAMS holds it: {(region, year, scheme, item): value}; assigning 0 deletes the record."""

    def __init__(self):
        self.v = {}

    def get(self, r, y, s, i):
        return self.v.get((r, y, s, i))

    def set(self, r, y, s, i, x):
        if x is None or (not isinstance(x, str) and x == 0.0):
            self.v.pop((r, y, s, i), None)
        else:
            self.v[(r, y, s, i)] = x

    def keys_of(self, s=None, r=None, i=None):
        return [k for k in self.v if (s is None or k[2] == s) and (r is None or k[0] == r) and (i is None or k[3] == i)]


def _ms_members(d, agg):
    """The member states of an aggregate (MAP_RR)."""
    return [m for m in d["ms"] if m in d["members"].get(agg, set())]


def _table(d, name):
    t = d["tables"][d["tables"].table == name]
    return {(str(r), int(y)): float(v) for r, y, v in zip(t.region, t.year, t.value)}


def _rs_regions(P, d):
    """The regions of the run's RS (not the EU aggregates) that hold a record."""
    return {k[0] for k in P.v if k[0] not in d["aggregates"]}


def _settings(d) -> dict:
    """mtr_settings.csv: {item: value}."""
    s = d["settings"]
    return {str(i): float(v) for i, v in zip(s["item"], s.value)}


def _year_range(d):
    st = _settings(d)
    return range(int(st["first_year"]), int(st["last_year"]) + 1)


def _rules(P: _Series, d: dict, sim_year: int, base_year: int) -> dict:
    """mtr_until2013.gms's assignments other than one literal value: {line: the rule executing it}, each rule taking
    its labels, right-hand side and numbers from mtr_rules.csv (the statement's)."""
    years = _year_range(d)
    st = _settings(d)
    viii, viiia, iv = _table(d, "ANNEX_VIII"), _table(d, "ANNEX_VIIIa"), _table(d, "ANNEX_IV")
    saps_area = {r: v for (r, _), v in _table(d, "SAPS_AREAS").items()}
    # l. 167: Belgium's net ceiling is its two parts'
    for y in years:
        bl = iv.get(("BL200000", y), 0.0) + iv.get(("BL400000", y), 0.0)
        if bl:
            iv[("BL000000", y)] = bl
        else:
            iv.pop(("BL000000", y), None)
    # l. 232-235: the SAPS member states, Slovenia and Malta out (they have the single farm payment)
    runr = [m for m in d["ms"] if any(viiia.get((m, y)) for y in years) and m not in ("SI000000", "MT000000")]
    base = _base(d)
    aggs = d["aggregates"]

    def rs_keys(s, i=None, year=None):
        return [k for k in P.keys_of(s=s, i=i) if k[0] not in aggs and (year is None or k[1] == year)]

    def ceiling_from_viii_eu_west(lab, rhs, num):
        for m in _ms_members(d, lab[2]):
            for y in years:
                P.set(m, y, lab[0], lab[1], viii.get((m, y), 0.0))

    def ceiling_from_viii(lab, rhs, num):
        for y in years:
            P.set(lab[0], y, lab[1], lab[2], viii.get((lab[3], y), 0.0))

    def ceiling_from_viiia(lab, rhs, num):
        for y in years:
            P.set(lab[0], y, lab[1], lab[2], viiia.get((lab[3], y), 0.0))

    def net_ceiling(lab, rhs, num):
        for m in d["ms"]:
            if sum(_num(P.get(m, y, lab[0], lab[1])) for y in years):
                for y in years:
                    if iv.get((m, y)):
                        P.set(m, y, lab[0], lab[1], iv[(m, y)])

    def saps_ceiling(lab, rhs, num):
        for m in runr:
            for y in years:
                if viiia.get((m, y)):
                    P.set(m, y, lab[0], lab[1], viiia[(m, y)])

    def saps_net_ceiling(lab, rhs, num):
        for m in runr:
            for y in years:
                if nonzero(P.get(m, y, lab[2], lab[3])) and iv.get((m, y)):
                    P.set(m, y, lab[0], lab[1], iv[(m, y)])

    def fill_ceiling(lab, rhs, num):
        # the loop of l. 264-269 over the base year to %endofMTR%: a missing value from the year before
        for y in range(base_year, int(st["end_of_mtr"]) + 1):
            for m in d["ms"]:
                if not nonzero(P.get(m, y, lab[0], lab[1])):
                    P.set(m, y, lab[0], lab[1], P.get(m, y - 1, lab[4], lab[5]))

    def saps_level(lab, rhs, num):
        for m in runr:
            for y in years:
                if nonzero(P.get(m, y, lab[2], lab[3])):
                    P.set(m, y, lab[0], lab[1], saps_area.get(m, 0.0))

    def saps_level_from_uaar(lab, rhs, num):
        for m in runr:
            for y in years:
                if nonzero(P.get(m, y, lab[2], lab[3])) and not nonzero(P.get(m, y, lab[4], lab[5])):
                    P.set(m, y, lab[0], lab[1], base.get((m, lab[6], lab[7], lab[8]), 0.0))

    def saps_rate(lab, rhs, num):
        for m in runr:
            for y in years:
                if nonzero(P.get(m, y, lab[2], lab[3])):
                    P.set(m, y, lab[0], lab[1],
                          _num(P.get(m, y, lab[4], lab[5])) / _num(P.get(m, y, lab[6], lab[7])) * float(num[0]))

    def saps_type(lab, rhs, num):
        for m in runr:
            for y in years:
                if nonzero(P.get(m, y, lab[2], lab[3])):
                    P.set(m, y, lab[0], lab[1], rhs)

    def set_where_ceiling(lab, rhs, num):
        v = float(num[0]) if num else rhs
        for y in years:
            if nonzero(P.get(lab[3], y, lab[4], lab[5])):
                P.set(lab[0], y, lab[1], lab[2], v)

    def eps_where_no_level(lab, rhs, num):
        for m in _ms_members(d, lab[3]):
            if not nonzero(P.get(m, int(lab[4]), lab[5], lab[6])):
                P.set(m, int(lab[0]), lab[1], lab[2], EPS)

    def eps_in_year(lab, rhs, num):
        # the Health Check: each item the region has in some year EPS in the year (the member states, or EU025000)
        regions = [lab[0]] if len(lab) == 5 else d["ms"]
        y, s = (int(lab[1]), lab[2]) if len(lab) == 5 else (int(lab[0]), lab[1])
        for r in regions:
            for i in {k[3] for k in P.keys_of(s=s, r=r) if nonzero(P.v[k])}:
                P.set(r, y, s, i, EPS)

    def delete_year(lab, rhs, num):
        for k in rs_keys(lab[1], year=int(lab[0])):
            P.set(*k, 0.0)

    def set_in_regions(lab, rhs, num):
        for r in d["sets"].get("TRDWHE_REG", []):
            P.set(r, int(lab[0]), lab[1], lab[2], sum(float(x) for x in num))

    def set_from_year(lab, rhs, num):
        # from the year after lab[3] to CALYEA("Y"), the simulation year itself
        if sim_year > int(lab[3]):
            P.set(lab[0], sim_year, lab[1], lab[2], float(num[0]))

    def dcow_ceiling(lab, rhs, num):
        # the regions of the aggregate's member states (MAP_RR, the member state itself included) at the simulation
        # year: the aggregate's rate times the milk quota of the year
        rate = _num(P.get(lab[3], sim_year, lab[4], lab[5]))
        for m in _ms_members(d, lab[2]):
            for r in d["members"].get(m, set()) | {m}:
                if r not in aggs:
                    P.set(r, sim_year, lab[0], lab[1], rate * base.get((r, lab[6], lab[7], str(sim_year)), 0.0))

    def scale_year(lab, rhs, num):
        for k in rs_keys(lab[1], i=lab[2], year=int(lab[0])):
            if P.v[k] not in (EPS, NA):
                P.set(*k, float(P.v[k]) * float(num[0]))

    def add_to_item(lab, rhs, num):
        P.set(lab[0], int(lab[1]), lab[2], lab[3], _num(P.get(lab[4], int(lab[5]), lab[6], lab[7])) + float(num[0]))

    def item_from_other(lab, rhs, num):
        P.set(lab[0], int(lab[1]), lab[2], lab[3], _num(P.get(lab[4], int(lab[5]), lab[6], lab[7])) - float(num[0]))

    def eps_where_saps(lab, rhs, num):
        for k in rs_keys(lab[2], i=lab[3]):
            if nonzero(P.v[k]):
                P.set(k[0], k[1], lab[0], lab[1], EPS)

    def rdel(lab, rhs, num):
        """l. 726-742 delete the regions outside the run: none of the run's regions."""

    fn = {f.__name__: f for f in (
        ceiling_from_viii_eu_west, ceiling_from_viii, ceiling_from_viiia, net_ceiling, saps_ceiling,
        saps_net_ceiling, fill_ceiling, saps_level, saps_level_from_uaar, saps_rate, saps_type, set_where_ceiling,
        eps_where_no_level, eps_in_year, delete_year, set_in_regions, set_from_year, dcow_ceiling, scale_year,
        add_to_item, item_from_other, eps_where_saps, rdel)}
    out = {}
    for ln, name, lab, rhs, num in zip(d["rules"].line, d["rules"].rule, d["rules"].labels, d["rules"].rhs,
                                       d["rules"].numbers):
        if name not in fn:
            raise ValueError(f"mtr_rules.csv: rule {name} (l. {ln}) not in capri_mod/policy/mtr.py")
        lab = str(lab).split("|") if str(lab) else []
        num = str(num).split() if str(num) else []
        out[int(ln)] = (lambda f, a, b, c: (lambda: f(a, b, c)))(fn[name], lab, str(rhs), num)
    return out


def _units_of(d, ms_set):
    return [u for m in ms_set for u in d["members"].get(m, set()) if u != m]


def _base(d) -> dict:
    """{(region, activity, item, column): value} of mtr_base_data.csv."""
    if "_base" not in d:
        b = d["base"]
        d["_base"] = {(str(r), str(a), str(i), str(c)): float(v)
                      for r, a, i, c, v in zip(b.region, b.activity, b.item, b.column, b.value)}
    return d["_base"]


def mtr_series(sim_year: int, base_year: int, d: dict = None) -> _Series:
    """p_premDataE of the key's schemes after mtr_until2013.gms (step 1 of the module docstring)."""
    d = d or data()
    P = _Series()
    t = d["decl"]
    rules = _rules(P, d, sim_year, base_year)
    lines = sorted(set(int(x) for x in t.line) | set(rules))
    by_line = defaultdict(list)
    for ln, r, y, s, i, v, sp in zip(t.line, t.region, t.year, t.scheme, t.item, t.value, t.special):
        if sp == "NA" and int(ln) == 0:
            # sim_ini's NA records (agenda.gms l. 1225: DPSHGM's PGSHGM of 2002 in every region) are taken as absent:
            # CAPRI's 2030 reference has each member state's sheep premium at its last value before them (Greece,
            # Spain, Italy, Portugal exact), not at EU015000's 16.8 that reading NA as "missing" in policy.gms gives;
            # how CAPRI's run loses them is not traced (KNOWN_ISSUES K142)
            continue
        by_line[int(ln)].append((str(r), int(y), str(s), str(i), _value(v, sp)))
    for ln in lines:
        for r, y, s, i, v in by_line.get(ln, ()):
            P.set(r, y, s, i, v)
        if ln in rules:
            rules[ln]()
    return P


def _groups(d) -> set:
    return set(d["sets"].get("PSGROUP", []))


def declarations_of_year(P: _Series, sim_year: int, d: dict = None) -> dict:
    """{(region, scheme): {item: value}} of the simulation year (step 2): def_policy.gms's last value of each record up
    to the year, then calc_mtr_top.gms l. 94-119 and l. 159-186."""
    d = d or data()
    last = {}
    for (r, y, s, i), v in P.v.items():
        if y <= sim_year and ((r, s, i) not in last or y > last[(r, s, i)][0]):
            last[(r, s, i)] = (y, v)
    Y = defaultdict(dict)
    for (r, s, i), (_, v) in last.items():
        Y[(r, s)][i] = v
    groups = _groups(d)
    eu15, eu25, eu27 = (set(_ms_members(d, a)) for a in ("EU015000", "EU025000", "EU027000"))
    schemes = {s for (_, s) in Y}

    def fill(m, src, items):
        for s in schemes:
            for i, v in Y.get((src, s), {}).items():
                if i in items and not nonzero(Y.get((m, s), {}).get(i)):
                    Y[(m, s)][i] = v

    st = _settings(d)
    for m in d["ms"]:
        if m in eu15:
            fill(m, "EU015000", groups)
        if m in eu15 or (sim_year >= st["eu25_from"] and m in eu25):
            fill(m, "EU025000", groups)
        if m in eu15 or (sim_year >= st["eu27_from"] and m in eu27):
            fill(m, "EU025000", groups)          # l. 101-103: EU025000's, as CAPRI writes it
    for m in d["ms"]:
        for src in ("EU015000", "EU025000", "EU028000"):
            for s in schemes:
                x = Y.get((m, s), {})
                if not nonzero(x.get("APPTYPE")) and any(
                        g in groups and v not in (EPS, NA) and not isinstance(v, str) and v > 0 for g, v in x.items()):
                    a = Y.get((src, s), {}).get("APPTYPE")
                    if a is not None:
                        Y[(m, s)]["APPTYPE"] = a
    for s in schemes:
        for i, v in Y.get(("BL000000", s), {}).items():
            if i in groups and not nonzero(Y.get(("BL400000", s), {}).get(i)):
                Y[("BL400000", s)][i] = v

    # l. 159-186: the EU-10's and BUR's Agenda 2000 schemes scaled to the SAPS budget (DPMTR's ceiling)
    base = _base(d)
    eu10 = set(_ms_members(d, "EU010000")) | set(_ms_members(d, "BUR"))
    for m in eu10:
        c = Y.get((m, "DPMTR"), {}).get("CEILVAL")
        if c in (None, EPS, NA) or c <= 0:
            continue

        def g(s, i):
            v = Y.get((m, s), {}).get(i)
            return v if v == NA else _num(v)

        terms = [(g("DPGRCU", "CEILLEV"), base.get((m, "CERE", "HSTY", str(sim_year)), 0.0), g("DPGRCU", "PGGRCU")),
                 (g("DPSCOW", "CEILLEV"), g("DPSCOW", "PGSCOW")), (g("DPBULF", "CEILLEV"), g("DPBULF", "PGBULF")),
                 (g("DPSHGM", "CEILLEV"), g("DPSHGM", "PGSHGM")), (g("DPSL_ADCT", "CEILLEV"), g("DPSL_ADCT", "PGMEAT")),
                 (g("DPSL_CALV", "CEILLEV"), g("DPSL_CALV", "PGCALV")), (g("DPNE_MEAT", "CEILVAL"),)]
        if any(NA in x for x in terms):
            # GAMS: NA propagates through the budget and the factor to the scaled values (l. 159-186), which
            # policy.gms then reads as missing
            f = NA
        else:
            total = sum(float(np.prod(x)) if len(x) > 1 else x[0] for x in terms)
            if total < 0:
                raise ValueError(f"mtr: {m}'s Agenda 2000 budget is negative")
            if not total:
                continue
            f = c / (total * 0.001)
        for s in d["sets"].get("DPAgEu10", []):
            x = Y.get((m, s))
            if not x:
                continue
            if nonzero(x.get("CEILVAL")):
                x["CEILVAL"] = x["CEILVAL"] if x["CEILVAL"] in (EPS, NA) else (NA if f == NA else x["CEILVAL"] * f)
            else:
                for i, v in list(x.items()):
                    if i in groups and v not in (EPS, NA) and not isinstance(v, str) and v > 0:
                        x[i] = NA if f == NA else v * f
    return dict(Y)


def policy_inputs(Y: dict, schemes, d: dict = None):
    """policy.gms's and prmcut.gms's inputs from the year's declarations of the schemes: ({(region, scheme): {"rates":
    {group: value}, "APPTYPE": type}}, {(region, scheme): {"CEILLEV": .., "CEILVAL": ..}}); NA is missing
    (policy.gms l. 25)."""
    d = d or data()
    groups = _groups(d)
    decl, ceil = {}, {}
    for (r, s), x in Y.items():
        if s not in schemes:
            continue
        rates = {g.upper(): v for g, v in x.items() if g in groups and v != NA}
        if rates or x.get("APPTYPE") not in (None, NA):
            decl[(r, s)] = {"rates": rates}
            if x.get("APPTYPE") not in (None, NA, EPS):
                decl[(r, s)]["APPTYPE"] = x["APPTYPE"]
        c = {i: x[i] for i in ("CEILLEV", "CEILVAL") if i in x and x[i] != NA}
        if c:
            ceil[(r, s)] = c
    return decl, ceil


def _unit_data(d, units, ms_of, col_levels: dict):
    """levels, yields, historical yields and young animals' inputs of the units and their member states at the base
    year (calc_mtr_top.gms l. 194-201), the levels of the EU-10's and BUR's at TRD."""
    base = _base(d)
    eu10 = set(_ms_members(d, "EU010000")) | set(_ms_members(d, "BUR"))
    regions = set(units) | set(ms_of.values())
    lev, yl, hs, sl = {}, {}, {}, {}
    for (r, a, i, c), v in base.items():
        if r not in regions:
            continue
        m = ms_of.get(r, r)
        if i == "LEVL" and a != "UAAR" and c == ("TRD" if m in eu10 else "BAS") and r in units:
            lev[(r, a)] = v
        elif i == "YILD" and c == "BAS":
            yl[(r, a)] = v
        elif i == "SLGT" and c == "BAS":
            sl[(r, a)] = v
        elif i == "HSTY" and c == "Y":
            hs[(r, a)] = v
    return lev, yl, hs, sl


def _rescaled_modif(d, prmd, levels, weight):
    """prmcut.gms l. 275-281: the modification factors rescaled so that a scheme's value per unit is the weighted
    one."""
    m = d.get("_modif")
    if m is None:
        t = d["modif"]
        m = d["_modif"] = {(str(r), str(a), str(s)): float(v) for r, a, s, v in zip(t.region, t.activity, t.scheme,
                                                                                    t.value)}
    num, den = defaultdict(float), defaultdict(float)
    for (u, a, s), p in prmd.items():
        if not p or p == EPS:
            continue
        L = levels.get((u, a), 0.0)
        w = weight.get((u, a, s), 1.0)
        num[(u, s)] += p * L * (0.0 if w == EPS else w)
        den[(u, s)] += p * L * m.get((u, a, s), 0.0)
    out = {}
    for (u, a, s), p in prmd.items():
        f = m.get((u, a, s))
        if f and p and p != EPS and p * levels.get((u, a), 0.0) * f > 0 and den[(u, s)]:
            out[(u, a, s)] = f * num[(u, s)] / den[(u, s)]
    return out


def _pass(d, units, decl, ceil, levels, *, yields=None, hist=None, slaughter=None, lu=None, modif=True,
          weights=None):
    """policy.gms and prmcut.gms for one member state's units: (PRME {(unit, activity, scheme)}, weight)."""
    from capri_mod.policy.cap14_premiums import data as c14_data, entitlement_weights
    regions = PolicyRegions.from_codes(units)
    w1 = entitlement_weights() if weights is None else weights
    dp = declared_premiums(decl, c14_data()["groups"], regions, levels, entl_weight=w1, yields=yields,
                           hist_yields=hist, slaughter=slaughter, lu_units=lu)
    us = set(units)
    prmd = {k: v for k, v in dp["prmd"].items() if k[0] in us and v}
    weight = {k: dp["weight"][k] for k in prmd}
    ms = regions.member_states
    nuts1 = {r: [u for u in units if u in regions.members.get(r, [])] for r in regions.nuts1
             if r not in ms and r not in us and any(u in regions.members.get(r, []) for u in units)}
    c = {k: v for k, v in ceil.items() if k[0] in us or k[0] in ms or k[0] in nuts1}
    mf = _rescaled_modif(d, prmd, levels, weight) if modif else {}
    res = premiums(levels, prmd, weight, c, CeilingRegions(member_states={m: [u for u in units if u in
                                                                              regions.members.get(m, [])] for m in ms},
                                                          nuts1=nuts1), modif=mf)
    return res["prme"], weight


def base_payments(Y: dict, units, d: dict = None) -> dict:
    """{(unit, scheme): million EUR} of PSDPAY_MTR_EL at the base year's data (step 3; aggreg_ppepay.gms l. 61)."""
    d = d or data()
    from capri_mod.data.definitions import capri_ms
    mtr_el = set(d["sets"]["PSDPAY_MTR_EL"])
    decl, ceil = policy_inputs(Y, mtr_el, d)
    lu = {str(a): float(v) for a, v in zip(d["lu"].activity, d["lu"].value)}
    by_ms = defaultdict(list)
    for u in units:
        by_ms[capri_ms(u)].append(u)
    out = {}
    for m, us in by_ms.items():
        ms_of = {u: m for u in us}
        lev, yl, hs, sl = _unit_data(d, us, ms_of, None)
        prme, _ = _pass(d, us, decl, ceil, lev, yields=yl, hist=hs, slaughter=sl, lu=lu)
        for (u, a, s), p in prme.items():
            if s in mtr_el and p and p != EPS:
                out[(u, s)] = out.get((u, s), 0.0) + p * lev.get((u, a), 0.0) * 0.001
    return out


def coupling(sim_year: int, d: dict = None) -> dict:
    """{(scheme, member state): p_couplPercent} of the simulation year (mtr_until2013.gms l. 974-991): the table's
    cells, 100 up to the last full year (2005), filled forward from the table's year (2006) to %endofMTR% (2020) where a cell is missing, 100 for the EU-11's
    and BUR's SAPS; only the simulation year kept, EPS read as 0. A simulation year after %endofMTR% keeps only what
    the table writes for it."""
    d = d or data()
    c = d["coupling"]
    E = {(str(s), int(y), str(m)): (EPS if int(e) else float(v)) for s, y, m, v, e in zip(c.scheme, c.year, c.ms,
                                                                                       c.pct, c.eps)}
    p = dict(E)
    st = _settings(d)
    first, end = int(st["coupling_from"]), int(st["end_of_mtr"])
    if sim_year <= st["coupled_until"]:
        return {(s, m): 100.0 for (s, _, m) in E}
    ms = set(d["ms"])
    schemes = {s for (s, _, _) in E}
    for k in [k for k in p if k[1] == first and k[2] not in ms]:
        del p[k]
    eu11 = set(_ms_members(d, "EU011000"))
    bur = set(_ms_members(d, "BUR"))
    for y in range(first, end + 1):
        for s in schemes:
            for m in ms:
                if not nonzero(p.get((s, y, m))) and nonzero(p.get((s, y - 1, m))):
                    p[(s, y, m)] = p[(s, y - 1, m)]
        for m in eu11 | bur:
            p[("DPSAPS", y, m)] = 100.0
    return {(s, m): (0.0 if v == EPS else v) for (s, y, m), v in p.items() if y == sim_year and v != 0.0}


def dd_targets(sim_year: int, units, d: dict = None) -> dict:
    """{(region, scheme, target): %} of the simulation year for the member states and units (mtr_until2013.gms
    l. 1554-1581, calc_mtr_top.gms l. 47-68)."""
    d = d or data()
    t = d["targets"]
    E = {}
    for r, y, s, g, v, e in zip(t.region, t.year, t.scheme, t.target, t.pct, t.eps):
        E[(str(r), int(y), str(s), str(g))] = EPS if int(e) else float(v)
    mtr_el = d["sets"]["PSDPAY_MTR_EL"]
    targets = d["sets"]["DDTarget"]
    ms = set(d["ms"])
    keys = {(r, s, g) for (r, _, s, g) in E if r in ms and s in mtr_el}
    st = _settings(d)
    for y in range(int(st["targets_from"]), max(int(st["end_of_mtr"]), sim_year) + 1):
        for (r, s, g) in keys:
            if not nonzero(E.get((r, y, s, g))) and nonzero(E.get((r, y - 1, s, g))):
                E[(r, y, s, g)] = E[(r, y - 1, s, g)]
    T = {(r, s, g): v for (r, y, s, g), v in E.items() if y == sim_year and r in ms and s in mtr_el
         and v != EPS and v > 0}
    for _, r, s, g, v, y0 in d["target_rules"].sort_values("line").itertuples(index=False):
        if sim_year < int(y0):
            continue
        for sc in (mtr_el if s == "ALL" else [s]):
            for tg in (targets if g == "ALL" else [g]):
                if float(v):
                    T[(str(r), sc, tg)] = float(v)
                else:
                    T.pop((str(r), sc, tg), None)

    def inherit(regions, src):
        for r in regions:
            for s in mtr_el:
                if not any(T.get((r, s, g)) for g in targets):
                    for g in targets:
                        if T.get((src, s, g)):
                            T[(r, s, g)] = T[(src, s, g)]

    inherit(_ms_members(d, "EU011000"), "EU011000")
    inherit([m for m in ("RO000000", "BG000000")], "BUR")
    inherit(_ms_members(d, "EU_WEST"), "EU_WEST")
    from capri_mod.data.definitions import capri_ms
    for u in units:
        m = capri_ms(u)
        for s in mtr_el:
            if not any(T.get((u, s, g)) for g in targets):
                for g in targets:
                    if T.get((m, s, g)):
                        T[(u, s, g)] = T[(m, s, g)]
    return {k: v for k, v in T.items() if k[0] in ms or k[0] in set(units)}


def modulation_total(d: dict = None) -> dict:
    """{(group, region): %} p_percAffByModulation's total (mtr_until2013.gms l. 832-833): the classes' shares x
    Prem_Mod."""
    d = d or data()
    share = dict(zip(d["classes"]["class"], d["classes"].share.astype(float)))
    out = defaultdict(float)
    for g, c, r, v in zip(d["modulation"].group, d["modulation"]["class"], d["modulation"].region,
                          d["modulation"].pct):
        out[(str(g), str(r))] += float(v) * share.get(str(c), 0.0)
    return dict(out)


def decoupled_budgets(pay: dict, Y: dict, sim_year: int, units, d: dict = None) -> dict:
    """{(unit, target): million EUR} p_DDPartialBudget (step 4): pay {(unit, scheme): base-year payments}."""
    d = d or data()
    from capri_mod.data.definitions import capri_ms
    mtr_el = d["sets"]["PSDPAY_MTR_EL"]
    psgg = defaultdict(list)
    for x in d["sets"]["PSGG_TO_P"]:
        g, s = x.split("|")
        psgg[s].append(g)
    tot = modulation_total(d)
    cp = coupling(sim_year, d)
    T = dd_targets(sim_year, units, d)
    by_ms = defaultdict(list)
    for u in units:
        by_ms[capri_ms(u)].append(u)
    out = defaultdict(float)
    for m, us in by_ms.items():
        prme = defaultdict(float)
        for (u, s), v in pay.items():
            if u in us:
                prme[s] += v
        modu = {s: prme[s] * sum(tot.get((g, m), 0.0) for g in psgg.get(s, [])) * 0.01 for s in mtr_el}
        p_tot = sum(prme[s] for s in mtr_el)
        m_tot = sum(modu.values())
        c = Y.get((m, "DPMTR"), {}).get("CEILVAL")
        c = 0.0 if c in (None, EPS, NA) else float(c)
        cut = 0.0
        if c and p_tot and m_tot:
            cut = ((p_tot - m_tot) - c) / m_tot
        modu = {s: v * max(0.0, cut + 1) for s, v in modu.items()}
        m_tot = sum(modu.values())
        cut = c / p_tot - 1 if (c and p_tot and not m_tot) else 0.0
        for u in us:
            for g in d["sets"]["DDTarget"]:
                b = 0.0
                for s in mtr_el:
                    v = pay.get((u, s), 0.0)
                    if v <= 0 or not prme[s]:
                        continue
                    b += (v * (prme[s] - modu[s]) / prme[s] * (1 - cp.get((s, m), 0.0) / 100) * (1 + cut)
                          * T.get((u, s, g), 0.0) / 100)
                if b > 0:
                    out[(u, g)] = b
    return dict(out)


def decoupled_declarations(budget: dict, Y: dict, units, d: dict = None, ntslvl: int = 2):
    """The decoupled schemes' declarations and ceilings of the year (step 5): ({(region, scheme): {"rates": ..,
    "APPTYPE": "perLevl"}}, {(region, scheme): {"CEILLEV": .., "CEILVAL": ..}})."""
    d = d or data()
    from capri_mod.data.definitions import capri_ms
    from capri_mod.policy.cap14_premiums import data as c14_data
    groups = c14_data()["groups"]
    base = _base(d)
    ref = set(groups.get("PGREF", []))
    land = (set(groups.get("PGARAB", [])) | set(groups.get("PGGRAS", []))) & d["mcact"]

    def lev(r, acts):
        return sum(base.get((r, a, "LEVL", "BAS"), 0.0) for a in acts)

    decl, ceil = {}, {}
    for u in units:
        c = budget.get((u, "DDFRMS"), 0.0)
        if c:
            L = lev(u, ref)
            ceil[(u, "DPFRMS")] = {"CEILVAL": c}
            if L:
                decl[(u, "DPFRMS")] = {"rates": {"PGFRM": c * 1000 / L}, "APPTYPE": "perLevl"}
                ceil[(u, "DPFRMS")]["CEILLEV"] = L
        c = budget.get((u, "DDFRMF"), 0.0)
        if c:
            L = lev(u, land)
            ceil[(u, "DPFRMF")] = {"CEILVAL": c}
            if L:
                decl[(u, "DPFRMF")] = {"rates": {"PGARAB": c * 1000 / L, "PGGRAS": c * 1000 / L},
                                       "APPTYPE": "perLevl"}
    nuts = d["nuts"]
    level = {str(r): float(v) for r, v in zip(nuts.sort_values("line").region, nuts.sort_values("line").level)}
    by_ms = defaultdict(list)
    for u in units:
        by_ms[capri_ms(u)].append(u)
    grass = ("GRAI", "GRAE")
    for m, us in by_ms.items():
        c = Y.get((m, "DPMTR"), {}).get("CEILVAL")
        if c in (None, EPS, NA) or not c:
            continue
        lv = min(level.get(m, 0.0), ntslvl)
        if lv == 0:
            regions = {m: us}
        elif lv == 1:
            regions = defaultdict(list)
            for u in us:
                for r in d["members"]:
                    if r != m and r != u and u in d["members"][r] and r in _srnuts1(d):
                        regions[r].append(u)
        else:
            raise ValueError(f"mtr: {m}'s flat rate at NUTS level {lv} (farm types) is not ported")
        for r, rus in regions.items():
            b = {g: sum(budget.get((u, g), 0.0) for u in rus) for g in ("DDRARA", "DDRARE", "DDRGRA")}
            if lv == 0:
                L, G = lev(m, land), lev(m, grass)
            else:
                L, G = sum(lev(u, land) for u in rus), sum(lev(u, grass) for u in rus)
            rates = {}
            if L and L - G:
                rates["PGARAB"] = b["DDRARA"] * 1000 / (L - G) + b["DDRARE"] * 1000 / L
            if G:
                rates["PGGRAS"] = b["DDRGRA"] * 1000 / G + (b["DDRARE"] * 1000 / L if L else 0.0)
            val = sum(b.values())
            cl = {}
            if any(rates.values()):
                cl["CEILLEV"] = L
            if val:
                cl["CEILVAL"] = val
            if cl:
                ceil[(r, "DPREG")] = cl
                decl[(r, "DPREG")] = {"rates": rates, "APPTYPE": "perLevl"}
    return decl, ceil


def _srnuts1(d):
    if "_srnuts1" not in d:
        inp = _inputs.current()
        d["_srnuts1"] = {str(c) for c in inp.csv("capri/SRNUTS1.csv", "codes", keep_default_na=False).code}
    return d["_srnuts1"]


def mtr_key(units, levels: dict, sim_year: int, base_year: int, d: dict = None, detail: bool = False):
    """{unit: million EUR} the BPS's historical key (step 6, implement_bps.gms l. 147-150): sum over DPFRMS, DPFRMF and
    DPREG of PRME x Entl / 1000 at the simulation year's levels {(unit, activity): level}. DPSAPS, the fourth scheme
    of PSDPAY_MTR, is the SAPS member states' (no BPS) and not ported."""
    d = d or data()
    from capri_mod.data.definitions import capri_ms
    P = mtr_series(sim_year, base_year, d)
    Y = declarations_of_year(P, sim_year, d)
    pay = base_payments(Y, units, d)
    budget = decoupled_budgets(pay, Y, sim_year, units, d)
    decl, ceil = decoupled_declarations(budget, Y, units, d)
    by_ms = defaultdict(list)
    for u in units:
        by_ms[capri_ms(u)].append(u)
    key = defaultdict(float)
    for m, us in by_ms.items():
        lev = {k: v for k, v in levels.items() if k[0] in us}
        dm = {k: v for k, v in decl.items() if k[0] in us or k[0] == m or k[0] in _srnuts1(d)}
        if not dm:
            continue
        prme, w = _pass(d, us, dm, ceil, lev, modif=False)
        for (u, a, s), p in prme.items():
            if s in ("DPFRMS", "DPFRMF", "DPREG") and p and p != EPS:
                key[u] += p * lev.get((u, a), 0.0) * (w.get((u, a, s), 1.0)) / 1000.0
    if detail:
        return dict(key), {"series": P, "year": Y, "pay": pay, "budget": budget, "decl": decl, "ceil": ceil}
    return dict(key)
