"""CAPTRD's national expert supports (captrd/national_supports.gms, included by captrd/expert_support.gms l. 779;
CAPRI star 3.0), with the reference run's switches: %aglinkTightLink% off (the blocks .ti31, .nt1, .ti31a run),
%useAgriInfo% on (the $else.nt3 branch for Luxembourg), %lst_daitar% 2020 (captrd.gms l. 260).

In GAMS's order (line numbers of national_supports.gms):
  l. 28-45      the dairy absolutes (expertdairy_map) also as PercentChange against BASM; PRCM and DOMM.MILK take
                MAPR.MILK's change and trust
  l. 49-152     the national sources' columns and rows; NECP's herds (dat/baseline/necp_expert.gms) as p_natExpert
  l. 154-198    interpolation and extrapolation (coco/time_avg.gms, gap years), BASYRSM filled, the base mean
  l. 205-268    default supports: PercentChange against the base mean, trust 7.01 (6.01 for herds without
                disaggregate data); crop yields; young lambs
  l. 270-1513   the countries' own rules (AT, BL, BL4, DE, DK, EL, ES, FI, IR, IT, NL, PT, SE, UK, BG, CY, CS, BA,
                KO, EE, HR, LV, LT, MT, PL, RO, SI, SK, CZ, NO, TUR), with their expert bounds; CS000000's support
                of the dairy herds floored (written to the support)
  l. 1514-1565  the dairy supports of absDairyRunr back to Absolute after 2020, the others kept as PercentChange
  l. 1569-1572  without effect here: ScenShifterPos_COLS holds no p_ExpertSupprt position and 2015 is no
                p_ExpertSupprt year in use; 2020 is an ex-ante year

The state is p_ExpertSupprt (Absolute, PercentChange, TrustLevl) as the earlier sources leave it, changed in place,
and the expert bounds p_result(..., "expertLo"/"expertUp"). A statement whose right side reads the position it
assigns takes the values from before the statement, as GAMS does: each rule below collects its new values first.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

K4 = Tuple[str, str, str, int]
K3 = Tuple[str, str, str]

#: l. 205: the default trust level of the national sources
TRUST_NAT = 7.01
#: l. 231-234: crop activities whose yield supports follow a national GROF support
TRUST_YIELD = 3.01
#: l. 224-225: the tiny growth that keeps a zero change from emptying PercentChange
TINY = 1.e-6
#: l. 162-163: the years completed and used by the interpolation (2000 to %lastSimulationYear%)
NEED_FROM = 2000
#: %lst_daitar% (captrd.gms l. 260): the last year of DG AGRI's dairy targets
LST_DAITAR = 2020
#: the year after which most country rules apply ("ORDT(ExAnteT) GT ORDT("2020")")
AFTER = 2020
DAYS_PER_YEAR = 365.0


def _csv(path: Path) -> List[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


@dataclass
class Inputs:
    sets: Dict[str, List[Tuple[str, ...]]]
    necp: Dict[Tuple[str, str, int], float]            # p_fromNECP(region, xpCol, year)

    def one(self, name: str) -> List[str]:
        return [x[0] for x in self.sets[name]]


def read_inputs(sets_dir: Path, dat_dir: Path) -> Inputs:
    sets = {}
    for p in sorted((sets_dir / "national").glob("*.csv")):
        rows = _csv(p)
        cols = [c for c in rows[0] if c.startswith("d")]
        sets[p.stem] = [tuple(r[c].upper() for c in cols) for r in rows]
    necp = {(r["region"], r["xpcol"].upper(), int(r["year"])): float(r["value"])
            for r in _csv(dat_dir / "national_p_fromnecp.csv")}
    return Inputs(sets, necp)


@dataclass
class Expert:
    """p_ExpertSupprt: Absolute, PercentChange, TrustLevl per (region, col, row, year); a zero deletes."""
    ab: Dict[K4, float] = field(default_factory=dict)
    pc: Dict[K4, float] = field(default_factory=dict)
    tr: Dict[K4, float] = field(default_factory=dict)
    lo: Dict[K4, float] = field(default_factory=dict)       # p_result(..., "expertLo")
    up: Dict[K4, float] = field(default_factory=dict)       # p_result(..., "expertUp")

    @staticmethod
    def put(d: Dict[K4, float], k: K4, v: float) -> None:
        if v:
            d[k] = v
        else:
            d.pop(k, None)

    def apply(self, d: Dict[K4, float], new: Dict[K4, float]) -> None:
        """A GAMS assignment: the values computed on the state before it, then written."""
        for k, v in new.items():
            self.put(d, k, v)


@dataclass
class Context:
    """What the file reads besides p_ExpertSupprt."""
    ms: Sequence[str]                     # MS
    runr: Sequence[str]
    nuts0: Iterable[str]
    nuts0_and_2: Iterable[str]
    nt2est: Iterable[str]
    nt2: Iterable[str]                    # NT2 (alias of srnuts2): the NUTS 2 regions
    map_rr: Iterable[Tuple[str, str]]
    s_colsest: Iterable[str]
    s_rowsest: Iterable[str]
    cact: Iterable[str]
    maact: Iterable[str]
    oiyani: Iterable[str]
    pact_to_y: Iterable[Tuple[str, str]]
    p_t_actagg: Iterable[Tuple[str, str]]
    exante: Sequence[int]
    exantet: Sequence[int]
    expostt: Sequence[int]
    basyrsm: Sequence[int]
    base_year: int                        # %BaseYear%, OrdT("BAS")
    bast_year: int                        # OrdT("BAST") = Lst_exPostT - 1 (captrd.gms l. 764)
    lst_expost: int
    lst_expostt: int
    lst_exante: int
    lst_dgagri: int
    support: Dict[K4, float]              # P_Result(..., "Support") of the ex-ante years; CS000000's is rewritten
    basm: Dict[K3, float]                 # p_data / P_Result BASM (repeated over the years)
    bast: Dict[K3, float]                 # BAST
    bas: Dict[K3, float]                  # P_DATA(..., "BAS")
    pdata: Dict[K4, float]                # P_Result(..., year, "p_data") of the calendar years
    dgagri1: Dict[K4, float]              # P_Result(..., year, "DGAgri1")
    years: Sequence[int] = ()             # YEARS (%FirstYear% to %lastSimulationYear%)


MKP = ("GROF", "HCOM", "DOMM")                       # MrkKeyPos (sets_captrd.gms l. 310-312)
COWS_ACT = ("DCOL", "DCOH", "SCOW")                  # CowsAct (sets_captrd.gms l. 332)
HL = ("HERD", "LEVL")                                # herdLevl (sets_captrd.gms l. 486-487)


def _time_avg(dat: Dict[Tuple[str, str, str, int], float], fill: Sequence[int], info: Sequence[int]):
    """coco/time_avg.gms with 'gapyrs' and no output mode: p_AVGDAT for the years to fill without data (inverse squared
    distance + 1 weights within the observations; before_avg / after_avg outside them, evaluated at the year after the
    first and before the last observation, as coded: CALYEA - fstobs_avg - 1 and CALYEA - lstobs_avg + 1)."""
    by: Dict[Tuple[str, str, str], Dict[int, float]] = {}
    for (a, b, c, y), v in dat.items():
        if y in info and v:
            by.setdefault((a, b, c), {})[y] = v
    out = {}
    for k, obs in by.items():
        f, l = min(obs), max(obs)

        def avg(at):
            w = {y: 1.0 / ((abs(y - at)) ** 2 + 1.0) for y in obs}
            return sum(obs[y] * w[y] for y in obs) / sum(w.values())
        # GAMS: SQR(ABS(CALYEA(interpol_years) - fstobs_avg - 1)), i.e. the distance to fstobs + 1
        before = sum(obs[y] / ((abs(y - f - 1)) ** 2 + 1.0) for y in obs) / sum(
            1.0 / ((abs(y - f - 1)) ** 2 + 1.0) for y in obs)
        after = sum(obs[y] / ((abs(y - l + 1)) ** 2 + 1.0) for y in obs) / sum(
            1.0 / ((abs(y - l + 1)) ** 2 + 1.0) for y in obs)
        for y in fill:
            if obs.get(y) or dat.get((*k, y)):
                continue
            if f <= y <= l:
                out[(*k, y)] = avg(y)
            elif y < f:
                out[(*k, y)] = before
            else:
                out[(*k, y)] = after
    return out


def supports(S: Expert, I: Inputs, X: Context) -> Dict[Tuple[str, str, str, int], float]:
    """The file's changes to S (in place) and to X.support (CS000000); returns p_natExpert."""
    one = I.one
    runr, ms = list(X.runr), list(X.ms)
    exante, exantet = list(X.exante), list(X.exantet)
    s_cols, s_rows = set(X.s_colsest), set(X.s_rowsest)
    agg: Dict[str, Set[str]] = {}
    for a, g in X.p_t_actagg:
        agg.setdefault(g, set()).add(a)
    dcow = sorted(agg.get("DCOW", set()))

    def is_(col, g):
        return col in agg.get(g, set())
    emap = {(c, w) for c in dcow for w in ("LEVL", "HERD", "COMI")} | {
        (c, "COMI") for c in ("GROF", "DOMM", "EAAG", "PRCM", "EXPE")}       # expert_support.gms l. 433-436
    pty = set(X.pact_to_y)
    sup, basm, bast, bas = X.support, X.basm, X.bast, X.bas
    ab, pc, tr, lo, up = S.ab, S.pc, S.tr, S.lo, S.up
    put = S.put

    def g(d, *k):
        return d.get(k, 0.0)

    def sp(r, c, w, y):
        return sup.get((r, c, w, y), 0.0)

    def bm(r, c, w):
        return basm.get((r, c, w), 0.0)

    def bt(r, c, w):
        return bast.get((r, c, w), 0.0)

    def keys(d, r=None, pred: Optional[Callable] = None):
        return [k for k in list(d) if (r is None or k[0] == r) and (pred is None or pred(k))]

    # ---- l. 28-45: dairy absolutes also as PercentChange; PRCM, DOMM .MILK from MAPR
    S.apply(pc, {k: ab[k] / bm(*k[:3]) * 100. - 100. for k in keys(ab)
                 if k[0] in runr and k[3] in exantet and (k[1], k[2]) in emap and bm(*k[:3])})
    new = {}
    for (r, c, w, y) in keys(pc, pred=lambda k: k[1] == "MAPR" and k[2] == "MILK" and k[3] in exantet and k[0] in runr):
        for cc in ("PRCM", "DOMM"):
            new[(r, cc, "MILK", y)] = pc[(r, c, w, y)]
    S.apply(pc, new)
    S.apply(tr, {(r, cc, "MILK", y): g(tr, r, "MAPR", "MILK", y) for (r, cc, w, y) in new
                 if g(pc, r, cc, "MILK", y) and g(pc, r, "MAPR", "MILK", y)})

    # ---- l. 144-152: NECP's herds as p_natExpert(nuts0, xpCol, "LEV1", year), the columns that map to COLS
    x2c: Dict[str, List[str]] = {}
    for a, b in I.sets["expert_to_cols"]:
        x2c.setdefault(a, []).append(b)
    x2r: Dict[str, List[str]] = {}
    for a, b in I.sets["expert_to_rows"]:
        x2r.setdefault(a, []).append(b)
    nuts0 = set(X.nuts0)
    nat: Dict[Tuple[str, str, str, int], float] = {}
    for (r, xc, y), v in I.necp.items():
        if r in nuts0 and xc in x2c and v:
            nat[(r, xc, "LEV1", y)] = v

    # ---- l. 154-194: gap years filled (time_avg), BASYRSM from p_AVGDAT or p_data x factor
    need = [y for y in X.years if NEED_FROM <= y]
    msset = set(ms)
    sub = {k: v for k, v in nat.items() if k[0] in msset}
    avg = _time_avg(sub, need, need)
    bym = set(X.basyrsm)
    for k, v in avg.items():                                                   # l. 168-169
        if k[3] not in bym and not nat.get(k):
            nat[k] = v
    exp = list(X.expostt)
    trip = {k[:3] for k in nat if k[0] in msset}
    newn = {}
    for t3 in trip:                                                             # l. 171-176
        if (any(nat.get((*t3, y)) for y in exp if y <= X.base_year)
                and any(nat.get((*t3, y)) for y in exp if y > X.base_year)
                and any(nat.get((*t3, y)) for y in need if y > X.lst_expost)):
            for y in bym:
                if not nat.get((*t3, y)) and (*t3, y) in avg:
                    newn[(*t3, y)] = avg[(*t3, y)]
    nat.update(newn)

    def pd_(r, c, w, y):
        return X.pdata.get((r, c, w, y), 0.0)

    def mapped(r, xc, xr, y):
        return sum(pd_(r, c, w, y) for c in x2c.get(xc, []) for w in x2r.get(xr, []))
    newn = {}
    for t3 in trip:                                                             # l. 180-194
        r, xc, xr = t3
        a = any(nat.get((*t3, y)) for y in exp if y <= X.base_year)
        b = any(nat.get((*t3, y)) for y in exp if y > X.base_year)
        both = [y for y in exp if nat.get((*t3, y)) and mapped(r, xc, xr, y)]
        if (not (a and b)) and both and any(nat.get((*t3, y)) for y in need if y > X.lst_expost):
            num = sum(nat[(*t3, y)] for y in both)
            den = sum(mapped(r, xc, xr, y) for y in both)
            for y in bym:
                if not nat.get((*t3, y)) and den:
                    newn[(*t3, y)] = mapped(r, xc, xr, y) * num / den
    nat.update({k: v for k, v in newn.items() if v})
    msest = ms + ["ISR"]
    base = X.base_year
    for t3 in {k[:3] for k in nat if k[0] in set(msest)}:                      # l. 197-198
        if all(nat.get((*t3, y)) for y in bym):
            nat[(*t3, base)] = sum(nat[(*t3, y)] for y in bym) / len(bym)

    def n_(r, xc, xr, y):
        return nat.get((r, xc, xr, y), 0.0)

    # ---- l. 205-268: default supports
    c2x: Dict[str, List[str]] = {}
    for a, b in I.sets["expert_to_cols"]:
        c2x.setdefault(b, []).append(a)
    r2x: Dict[str, List[str]] = {}
    for a, b in I.sets["expert_to_rows"]:
        r2x.setdefault(b, []).append(a)
    pairs = lambda c, w: [(xc, xr) for xc in c2x.get(c, []) for xr in r2x.get(w, [])]   # noqa: E731
    cand = {(r, c, w) for (r, xc, xr, y) in nat for c in x2c.get(xc, []) for w in x2r.get(xr, [])
            if r in set(msest)}
    new = {}
    for (r, c, w) in cand:
        for y in exantet:
            if (sum(n_(r, xc, xr, y) * n_(r, xc, xr, base) for xc, xr in pairs(c, w))
                    and not (g(ab, r, c, w, y) or g(pc, r, c, w, y))):
                new[(r, c, w, y)] = TRUST_NAT
    S.apply(tr, new)
    for k in keys(tr, pred=lambda k: k[0] in set(msest) and k[1] in set(X.cact) and k[2] == "HERD"
                  and k[3] in exantet):
        put(tr, k, 0.0)
    new = {}
    for k in keys(tr, pred=lambda k: k[0] in set(msest) and k[3] in exantet and tr[k] == TRUST_NAT):
        r, c, w, y = k
        pp = [(xc, xr) for xc, xr in pairs(c, w) if n_(r, xc, xr, base) and n_(r, xc, xr, y)]
        den = sum(n_(r, xc, xr, base) for xc, xr in pp)
        if den:
            num = sum(n_(r, xc, xr, y) + TINY * n_(r, xc, xr, base) * (n_(r, xc, xr, base) == n_(r, xc, xr, y))
                      for xc, xr in pp)
            new[k] = num / den * 100. - 100.
        else:
            raise ZeroDivisionError(f"national_supports.gms l. 218: {k} has no base value")
    S.apply(pc, new)
    cact = set(X.cact)
    new = {(r, a, w, y): TRUST_YIELD for (r, c, w, y) in keys(tr) if r in msset and c == "GROF"
           and y in exantet and tr[(r, c, w, y)] == TRUST_NAT for a in cact if (a, w) in pty}     # l. 231-234
    S.apply(tr, new)
    S.apply(ab, {k: sp(*k) for k in keys(tr) if k[0] in msset and k[1] in cact and k[3] in exantet
                 and tr[k] == TRUST_YIELD})                                                     # l. 236-238
    new_pc, new_tr = {}, {}
    for r in ms:                                                                                # l. 244-253
        for y in exantet:
            if g(tr, r, "SHGM", "LEVL", y) == TRUST_NAT:
                for w in ("YLAM", "ILAM"):
                    new_pc[(r, "GROF", w, y)] = g(pc, r, "SHGM", "LEVL", y)
    S.apply(pc, new_pc)
    for (r, c, w, y) in new_pc:
        if g(pc, r, c, w, y):
            new_tr[(r, c, w, y)] = TRUST_NAT - 1
    S.apply(tr, new_tr)
    dis = set(one("xpdisagg"))
    new = {}
    for k in keys(pc, pred=lambda k: k[0] in msset and k[3] in exantet and k[2] in HL):          # l. 259-268
        r, c, w, y = k
        if g(tr, *k) == TRUST_NAT and not sum(n_(r, xd, "LEV1", y) for xd in c2x.get(c, []) if xd in dis):
            new[k] = TRUST_NAT - 1
    S.apply(tr, new)

    # ---- helpers for the country rules
    def blend(r, a, b, years, wfun=None):
        """the dairy 'AT formula': a x PercentChange + b x PercentChange(lst_daitar) after lst_daitar."""
        new = {}
        for k in keys(pc, r, lambda k: k[3] in years and k[3] > LST_DAITAR and (k[1], k[2]) in emap):
            _, c, w, y = k
            p0 = g(pc, r, c, w, LST_DAITAR)
            if p0:
                aa, bb = (a, b) if wfun is None else wfun(c, w)
                new[k] = pc[k] * aa + p0 * bb
        S.apply(pc, new)

    def nat_dcow(r, years, trust, xp="DCOW"):
        """DE, DK, ES, NL, EE, HR, LV, LT, RO: the dairy herds from the national source, cow milk from the absolute
        dairy yield on the new herd."""
        if n_(r, xp, "LEV1", base):
            S.apply(pc, {(r, c, w, y): n_(r, xp, "LEV1", y) / n_(r, xp, "LEV1", base) * 100 - 100
                         for c in dcow for w in HL for y in years if y > AFTER})
            S.apply(tr, {(r, c, w, y): trust for c in dcow for w in HL for y in years
                         if y > AFTER and g(pc, r, c, w, y)})
        cols = [c for (c, w) in emap if w == "COMI" and not is_(c, "DCOW")]
        new = {}
        for c in cols:
            for y in years:
                if y > AFTER:
                    new[(r, c, "COMI", y)] = ((100 + g(pc, r, "DCOH", "LEVL", y)) / 100
                                              * g(ab, r, "DCOH", "COMI", y) / bm(r, "DCOH", "COMI") * 100 - 100)
        S.apply(pc, new)
        S.apply(tr, {(r, c, "COMI", y): TRUST_NAT for c in cols for y in years if y > AFTER})

    def bounds(r, cs, ws, years, flo, fup, src="ab", base_=None):
        for c in cs:
            for w in ws:
                for y in years:
                    if src == "ab":
                        v = g(ab, r, c, w, y)
                    else:
                        p = g(pc, r, c, w, y)
                        v = (1 + p / 100) * (base_(r, c, w) if base_ else bm(r, c, w)) if p else 0.0
                    if v:
                        put(lo, (r, c, w, y), flo * v)
                        put(up, (r, c, w, y), fup * v)

    def trust_if(r, cs, ws, years, t, need="ab", only_new=False):
        d = ab if need == "ab" else pc
        S.apply(tr, {(r, c, w, y): t for c in cs for w in ws for y in years
                     if g(d, r, c, w, y) and not (only_new and g(tr, r, c, w, y))})

    after_t = [y for y in exantet if y > AFTER]
    after_a = [y for y in exante if y > AFTER]
    y2020t = [y for y in exantet if y == AFTER]
    maact = set(X.maact)
    shgt = sorted(agg.get("SHGT", set()))
    poul = sorted(agg.get("POUL", set()))

    # ---- l. 270-311 AT
    blend("AT000000", .5, .5, exantet)
    S.apply(ab, {("AT000000", "PIGF", w, y): sp("AT000000", "PIGF", w, y) for w in HL + ("DAYS",) for y in after_t
                 if sp("AT000000", "PIGF", w, y)})
    S.apply(ab, {("AT000000", "PIGF", "PORK", y): .1 * sp("AT000000", "PIGF", "PORK", y)
                 + .9 * bt("AT000000", "PIGF", "PORK") for y in after_t if sp("AT000000", "PIGF", "PORK", y)})
    trust_if("AT000000", ["PIGF"], HL, exantet, 9.01, only_new=True)
    trust_if("AT000000", ["PIGF"], ("PORK", "DAYS"), exantet, 9.01, only_new=True)
    # ---- l. 312-342 BL
    bounds("BL000000", dcow, ["COMI"], y2020t, .99, 1.01)
    trust_if("BL000000", dcow, ["COMI"], y2020t, 10.01)
    S.apply(ab, {("BL000000", "GROF", "PORK", y): sp("BL000000", "GROF", "PORK", y) for y in after_t
                 if sp("BL000000", "GROF", "PORK", y)})
    trust_if("BL000000", ["GROF"], ["PORK"], exantet, 8.01, only_new=True)
    # ---- l. 343-416 BL4 (Luxembourg; %useAgriInfo% on: $else.nt3)
    lu = "BL400000"
    blend(lu, None, None, exantet, wfun=lambda c, w: ((1 - .2), .8) if w in HL else (1.0, 0.0))
    S.apply(pc, {(lu, c, w, y): .01 for c in dcow for w in HL for y in after_t})
    S.apply(pc, {(lu, "GROF", "COMI", y): g(pc, lu, "DCOH", "COMI", y) + g(pc, lu, "DCOH", "LEVL", y)
                 for y in exantet if y > LST_DAITAR})
    S.apply(tr, {k: 10.01 for k in keys(pc, lu, lambda k: k[3] in exante)})
    bounds(lu, dcow, [w for (c, w) in emap if c == dcow[0]], exantet, .99, 1.01, src="pc")
    new_lo, new_up = {}, {}
    for (r, c, w, y), s in list(sup.items()):                                                     # l. 403-415
        if r == lu and c in maact and w == "LEVL" and y in exantet and s and bm(r, c, w):
            if not g(lo, r, c, w, y):
                new_lo[(r, c, w, y)] = .95 * max(s, .1 * bm(r, c, w))
    S.apply(lo, new_lo)
    for (r, c, w, y), s in list(sup.items()):
        if r == lu and c in maact and w == "LEVL" and y in exantet and s and bm(r, c, w):
            if not g(up, r, c, w, y):
                new_up[(r, c, w, y)] = 1.05 * max(s, g(lo, r, c, w, y))
    S.apply(up, new_up)
    # ---- l. 417-473 DE
    de = "DE000000"
    v19 = pd_(de, "INDM", "MAIF", X.lst_expostt)
    S.apply(ab, {(de, "INDM", "MAIF", y): v19 for y in exantet if y > X.lst_expostt and v19})
    trust_if(de, ["INDM"], ["MAIF"], exantet, 10.01)
    nt2 = [n for (p, n) in X.map_rr if p == de and n in set(X.nt2)]
    tot = sum(pd_(n, "INDM", "MAIF", X.lst_expost) for n in nt2)
    if tot:
        new = {}
        for n in [n for n in X.nt2est if (de, n) in set(X.map_rr)]:
            for y in exantet:
                if y > X.lst_expost:
                    new[(n, "INDM", "MAIF", y)] = ((pd_(de, "INDM", "MAIF", y) or g(ab, de, "INDM", "MAIF", y))
                                                   * pd_(n, "INDM", "MAIF", X.lst_expost) / tot)
        S.apply(ab, new)
        S.apply(tr, {k: 5.01 for k in new if g(ab, *k)})
    nat_dcow(de, exantet, TRUST_NAT)
    trust_if(de, ["SHGM"], HL, exantet, TRUST_NAT + 2, need="pc")
    # ---- l. 474-527 DK (the rest of its block is in $ontext)
    nat_dcow("DK000000", exante, TRUST_NAT)
    # ---- l. 528-593 EL
    el = "EL000000"
    S.apply(ab, {(el, c, "COMI", y): g(ab, el, c, "COMI", y) * .9 for c in dcow for y in exante if y == AFTER})
    blend(el, .7, .3, exante)
    late = [y for y in exante if y > 2030]
    S.apply(ab, {(el, "PIGF", "LEVL", y): max(sp(el, "PIGF", "LEVL", y), .2 * bt(el, "PIGF", "LEVL")) for y in late})
    S.apply(ab, {(el, "PIGF", "HERD", y): g(ab, el, "PIGF", "LEVL", y) * sp(el, "PIGF", "DAYS", y) / DAYS_PER_YEAR
                 for y in exante if g(ab, el, "PIGF", "LEVL", y) and sp(el, "PIGF", "DAYS", y)})

    def ramp(y):
        return 1. + (y - 2030) * (.1 - 1) / (X.lst_exante - 2030)
    S.apply(tr, {(el, "PIGF", w, y): ramp(y) for w in HL for y in late if g(ab, el, "PIGF", w, y)})
    S.apply(ab, {(el, "GROF", w, y): max(sp(el, "GROF", w, y), .2 * bt(el, "GROF", w)) for w in ("YPIG", "IPIG")
                 for y in exante if g(ab, el, "PIGF", "LEVL", y)})
    S.apply(tr, {(el, "GROF", w, y): ramp(y) for w in ("YPIG", "IPIG") for y in late if g(ab, el, "GROF", w, y)})
    S.apply(ab, {(el, "SHGM", "SGMI", y): sp(el, "SHGM", "SGMI", y) for y in after_t if sp(el, "SHGM", "SGMI", y)})
    trust_if(el, ["SHGM"], ["SGMI"], exantet, 9.01)
    # ---- l. 594-629 ES, FI
    nat_dcow("ES000000", exante, TRUST_NAT)
    trust_if("FI000000", ["PIGF"], HL, exantet, TRUST_NAT + 2, need="pc")
    # ---- l. 630-644 IR
    ir = "IR000000"
    S.apply(ab, {(ir, "GROF", "PORK", y): bt(ir, "GROF", "PORK") for y in after_t if bt(ir, "GROF", "PORK")})
    trust_if(ir, ["GROF"], ["PORK"], exantet, 3.01)
    trust_if(ir, poul, HL, exantet, TRUST_NAT + 2, need="pc")
    # ---- l. 645-738 IT
    it = "IT000000"
    if any(k[0] == it for k in nat):
        S.apply(pc, {(it, "GROF", w, y): g(pc, it, "PIGF", "LEVL", y) for w in ("PORK", "YPIG", "IPIG")
                     for y in exante})
        S.apply(tr, {(it, "GROF", w, y): 2.0 for w in ("PORK", "YPIG", "IPIG") for y in exante
                     if g(pc, it, "GROF", "PORK", y)})
    S.apply(ab, {(it, "PIGF", w, y): bt(it, "PIGF", w) * 1.0025 ** (y - X.bast_year) for w in HL for y in after_t
                 if bt(it, "PIGF", w)})
    trust_if(it, ["PIGF"], HL, exantet, 9.01)
    S.apply(ab, {(it, c, "PORK", y): bt(it, c, "PORK") for c in MKP for y in after_t if bt(it, c, "PORK")})
    trust_if(it, MKP, ["PORK"], exantet, 9.01)
    S.apply(ab, {(it, "SCOW", w, y): bm(it, "SCOW", w) * (1 - .015) ** (y - base) for w in HL for y in after_t
                 if bm(it, "SCOW", w)})
    trust_if(it, ["SCOW"], HL, exantet, 9.01)
    bounds(it, dcow, HL, exantet, .95, 1.05, src="pc")
    bounds(it, [c for c in MKP if (c, "COMI") in emap and True], ["COMI"], exantet, .9, 1.1, src="pc")
    rws = HL + ("COMI",)
    S.apply(pc, {(it, c, w, y): (g(pc, it, c, w, 2020) + g(pc, it, c, w, 2030)) / 2 * .99 for c in dcow for w in rws
                 for y in exantet if y == 2025 and g(pc, it, c, w, 2020) and g(pc, it, c, w, 2030)})
    bounds(it, dcow, rws, [y for y in exantet if y == 2025], .99, 1.01, src="pc")
    trust_if(it, dcow, rws, [y for y in exantet if y == 2025], 10.01)
    S.apply(ab, {(it, "VSET", "LEVL", y): sp(it, "VSET", "LEVL", y) for y in exante if y > 2010})
    trust_if(it, ["VSET"], ["LEVL"], exante, 2.01)
    # ---- l. 739-787 NL
    nl = "NL000000"
    nat_dcow(nl, exante, TRUST_NAT, xp="DCOW")
    S.apply(tr, {(nl, c, w, y): TRUST_NAT + 2 for c in dcow for w in HL for y in exante
                 if y > AFTER and g(pc, nl, c, w, y) and n_(nl, "DCOW", "LEV1", base)})
    S.apply(pc, {(nl, "PIGF", "DAYS", y): sp(nl, "PIGF", "DAYS", y) / bm(nl, "PIGF", "DAYS") * 100 - 100
                 for y in exante if y > 2010 and sp(nl, "PIGF", "DAYS", y) and bm(nl, "PIGF", "DAYS")})
    trust_if(nl, ["PIGF"], ["DAYS"], exante, 8.01, need="pc")
    bounds(nl, dcow, HL, y2020t, .99, 1.01)
    # ---- l. 788-849 PT
    pt = "PT000000"
    if any(k[0] == pt for k in nat):
        trust_if(pt, COWS_ACT, ["LEVL"], exante, 6.0, need="pc")
        S.apply(pc, {(pt, "PIGF", "PORK", y): ((1. - 0.002) ** (y - base)) * 100. - 100. for y in exante})
        S.apply(tr, {(pt, "PIGF", "PORK", y): 10.0 for y in exante})
        S.apply(pc, {(pt, "SOWS", "YPIG", y): min(sp(pt, "SOWS", "YPIG", y) / bm(pt, "SOWS", "YPIG"),
                                                  1. + 0.2 * (max(base + 1, y) - base) / (X.lst_exante - base))
                     * 100. - 100. for y in exante})
        S.apply(tr, {(pt, "SOWS", "YPIG", y): 2.0 for y in exante})
        S.apply(pc, {(pt, "GROF", w, y): g(pc, pt, "SOWS", "YPIG", y) for w in ("YPIG", "IPIG") for y in exante})
        new = {}
        for w in ("ICOW", "YCAM", "YCAF"):
            for y in exante:
                if sum(bm(pt, c, "LEVL") * bm(pt, c, w) for c in COWS_ACT):
                    new[(pt, "GROF", w, y)] = (sum(g(pc, pt, c, "LEVL", y) * bm(pt, c, "LEVL") for c in COWS_ACT)
                                               / sum(bm(pt, c, "LEVL") for c in COWS_ACT))
        S.apply(pc, new)
        for a, b in (("YCOW", "ICOW"), ("ICAM", "YCAM"), ("ICAF", "YCAF")):
            S.apply(pc, {(pt, "GROF", a, y): g(pc, pt, "GROF", b, y) for y in exante})
        trust_if(pt, ["GROF"], list(X.oiyani), exante, 3.0, need="pc")
    # ---- l. 850-863 SE
    se = "SE000000"
    S.apply(ab, {(se, "GROF", "PORK", y): bm(se, "GROF", "PORK") for y in after_t
                 if bm(se, "GROF", "PORK") and not g(ab, se, "GROF", "PORK", y)})
    trust_if(se, ["GROF"], ["PORK"], exantet, 8.01)
    # ---- l. 864-886 UK, BG
    blend("UK000000", .8, .2, exante)
    trust_if("BG000000", ["PIGF"], HL, exantet, TRUST_NAT + 1, need="pc")
    # ---- l. 887-945 CY
    cy = "CY000000"
    S.apply(pc, {(cy, c, w, y): g(ab, cy, c, w, y) / bm(cy, c, w) * 100 - 100
                 + (g(ab, cy, c, w, AFTER) / bm(cy, c, w) * 100 - 100) * .9
                 for c in dcow for w in HL for y in after_t if sp(cy, c, w, y) and bm(cy, c, w)})
    S.apply(ab, {(cy, c, w, y): 0.0 for c in dcow for w in HL for y in after_t if g(pc, cy, c, w, y)})
    trust_if(cy, dcow, HL, exantet, 8.01, need="pc")
    bounds(cy, dcow, HL, exantet, .95, 1.05, src="pc")
    new = {}
    for c in dcow:
        for y in exante:
            p0 = g(pc, cy, c, "COMI", LST_DAITAR)
            if g(pc, cy, c, "COMI", y) and p0 and y > LST_DAITAR:
                new[(cy, c, "COMI", y)] = g(pc, cy, c, "COMI", y) * .7 + p0 * .3
    S.apply(pc, new)
    S.apply(ab, {(cy, "GROF", "PORK", y): sp(cy, "GROF", "PORK", y) for y in after_t if sp(cy, "GROF", "PORK", y)})
    trust_if(cy, ["GROF"], ["PORK"], exantet, 8.01, only_new=True)
    # ---- l. 946-987 CS (Serbia): the dairy herds' support floored (as expert_support.gms l. 794-807), then dampened
    cs = "CS000000"
    span_b = X.lst_exante - base
    span_t = X.lst_exante - X.bast_year
    new = {}
    for c in dcow:
        for w in HL:
            b0, t0 = bas.get((cs, c, w), 0.0), bast.get((cs, c, w), 0.0)
            for y in exantet:
                s = sp(cs, c, w, y)
                if t0:
                    f1 = min(t0 * .9 ** (y - X.bast_year), b0 * .9 ** (y - base))
                    f2 = min(t0 * (1 - .8 * (y - X.bast_year) / span_t), b0 * (1 - .8 * (y - base) / span_b))
                else:
                    f1 = b0 * .9 ** (y - base)
                    f2 = b0 * (1 - .8 * (y - base) / span_b)
                new[(cs, c, w, y)] = max(s, f1, f2)
    for k, v in new.items():
        Expert.put(sup, k, v)
    S.apply(ab, {(cs, c, w, y): sp(cs, c, w, y) - (sp(cs, c, w, y) - bm(cs, c, w))
                 * .3 * ((max(2031, y) - 2030) / (X.lst_exante - 2030))
                 for (c, w) in emap for y in exantet if y > 2040 and sp(cs, c, w, y) and bm(cs, c, w)})
    S.apply(tr, {k: 9.01 for k in keys(ab, cs, lambda k: k[3] in exante and (k[1], k[2]) in emap)})
    # ---- l. 988-1014 BA, KO
    ba = "BA000000"
    S.apply(ab, {(ba, "POUF", w, y): sp(ba, "POUF", w, y) * (0.99 ** (y - X.bast_year)) * (y >= AFTER)
                 for w in HL for y in exantet})
    trust_if(ba, ["POUF"], HL, exantet, 8.01)
    ko = "KO000000"
    S.apply(ab, {(ko, "HENS", w, y): sp(ko, "HENS", w, y) for w in HL for y in exantet
                 if sp(ko, "HENS", w, y) and AFTER <= y <= 2030})
    trust_if(ko, ["HENS"], HL, exantet, 8.01)
    # ---- l. 1015-1089 EE
    ee = "EE000000"
    S.apply(ab, {(ee, c, "COMI", y): g(ab, ee, c, "COMI", y) * 1.05 for c in dcow for y in exante if y == AFTER})
    bounds(ee, dcow, ["COMI"], y2020t, .99, 1.01)
    trust_if(ee, dcow, ["COMI"], y2020t, 10.01)
    bounds(ee, dcow, HL, y2020t, .99, 1.01)
    nat_dcow(ee, exante, TRUST_NAT)

    def sgm(r, absolute=True):
        rows_ = ("SGMT", "SGMI")
        if absolute:
            S.apply(ab, {(r, c, w, y): bm(r, c, w) * (1 + g(pc, r, "SHGM", "LEVL", y) / 100)
                         for c in MKP for w in rows_ for y in after_a})
        else:
            S.apply(pc, {(r, c, w, y): g(pc, r, "SHGM", "LEVL", y) for c in MKP for w in rows_ for y in after_a})
        S.apply(tr, {(r, c, w, y): TRUST_NAT for c in MKP for w in rows_ for y in after_a})
    sgm(ee)
    # ---- l. 1090-1190 HR, LV, LT (the block headed HU, l. 1097-1122, assigns HR000000's positions, as
    #      coded)
    trust_if("HR000000", ["PIGF"], HL, exantet, TRUST_NAT + 1, need="pc")
    nat_dcow("HR000000", exante, TRUST_NAT)
    nat_dcow("LV000000", exante, TRUST_NAT)
    sgm("LV000000")
    nat_dcow("LT000000", exante, TRUST_NAT)
    # ---- l. 1191-1225 MT, PL
    mt = "MT000000"
    blend(mt, .2, .8, exante)
    S.apply(pc, {(mt, "GROF", "SGMT", y): sp(mt, "GROF", "SGMT", y) / bm(mt, "GROF", "SGMT") * 100 - 100
                 for y in exantet if sp(mt, "GROF", "SGMT", y) and bm(mt, "GROF", "SGMT")})
    trust_if(mt, ["GROF"], ["SGMT"], exantet, 7.01, need="pc")
    trust_if("PL000000", ["PIGF"], HL, exantet, TRUST_NAT + 1, need="pc")
    # ---- l. 1226-1266 RO
    ro = "RO000000"
    nat_dcow(ro, exante, TRUST_NAT, xp="CATT")
    trust_if(ro, ["PIGF"], HL, exantet, TRUST_NAT + 2, need="pc")
    if bm(ro, "MAIF", "LEVL"):
        S.apply(pc, {(ro, "MAIF", "LEVL", y): (bt(ro, "MAIF", "LEVL") / bm(ro, "MAIF", "LEVL") - 1.) * 100
                     for y in exantet})
    trust_if(ro, ["MAIF"], ["LEVL"], exantet, .5, need="pc")
    # ---- l. 1267-1326 SI
    si = "SI000000"
    sset = set(shgt) | {"POUF", "HENS"}
    S.apply(ab, {(si, c, w, y): sp(si, c, w, y) for (r, c, w, y) in list(sup) if r == si and c in sset and w in HL
                 and y in exantet and sp(si, c, w, y) and not g(ab, si, c, w, y) and bm(si, c, w)})
    trust_if(si, sorted(sset), HL, exantet, 9.01)
    bounds(si, shgt, HL, [y for y in exantet if y >= 2050], .99, 1.01)
    blend(si, .6, .4, exante)
    S.apply(ab, {(si, "SCOW", w, y): bt(si, "SCOW", w) for w in HL for y in after_t if bt(si, "SCOW", w)})
    trust_if(si, ["SCOW"], HL, exantet, 9.01)
    S.apply(ab, {(si, "GROF", "PORK", y): bm(si, "GROF", "PORK") for y in after_t
                 if bm(si, "GROF", "PORK") and not g(ab, si, "GROF", "PORK", y)})
    trust_if(si, ["GROF"], ["PORK"], exantet, 8.01)
    # ---- l. 1327-1375 SK
    sk = "SK000000"
    blend(sk, None, None, exante,
          wfun=lambda c, w: ((.6 + .3, .4 - .3) if (is_(c, "DCOW") and w == "COMI") else (.6, .4)))
    bounds(sk, dcow, HL, exantet, .95, 1.05, src="pc")
    bounds(sk, dcow, ["COMI"], y2020t, .99, 1.01)
    trust_if(sk, dcow, ["COMI"], y2020t, 10.01)
    sgm(sk, absolute=False)
    # ---- l. 1376-1416 CZ
    cz = "CZ000000"
    blend(cz, .3, .7, exante)
    S.apply(ab, {(cz, c, w, y): sp(cz, c, w, y) for (r, c, w, y) in list(sup) if r == cz and c in set(shgt)
                 and w in HL and y in exantet and sp(cz, c, w, y) and not g(ab, cz, c, w, y) and bm(cz, c, w)})
    trust_if(cz, shgt, HL, exantet, 10.01)
    bounds(cz, shgt, HL, [y for y in exantet if y == 2030], .99, 1.01)
    # ---- l. 1417-1468 NO
    no, L = "NO000000", X.lst_dgagri

    def d1(r, c, w, y):
        return X.dgagri1.get((r, c, w, y), 0.0)
    cols = [c for (c, w) in emap if w == "COMI" and not is_(c, "DCOW")]
    new = {}
    for c in cols:
        for y in after_t:
            v = d1(no, c, "COMI", y)
            if y > L and d1(no, c, "COMI", L):
                v += d1(no, c, "COMI", L) * ((d1(no, c, "COMI", L) / bm(no, c, "COMI"))
                                             ** ((y - L) / (L - base)))
            new[(no, c, "COMI", y)] = v
    S.apply(ab, new)
    S.apply(tr, {(no, c, "COMI", y): TRUST_NAT + 1 for (c, w) in emap if w == "COMI" for y in after_t
                 if g(ab, no, c, "COMI", y)})
    S.apply(ab, {(no, c, "COMI", y): sp(no, c, "COMI", y) for c in dcow for y in exantet if y >= AFTER})
    S.apply(tr, {(no, c, "COMI", y): TRUST_NAT - 2 for c in dcow for y in exantet})
    prows = ("PORK", "EGGS", "POUM")
    S.apply(ab, {(no, c, w, y): d1(no, c, w, y) + d1(no, c, w, L) * (y > L) for c in MKP for w in prows
                 for y in after_t})
    trust_if(no, MKP, prows, after_t, TRUST_NAT)
    S.apply(ab, {(no, c, w, y): sp(no, c, w, y) for (r, c, w, y) in list(sup) if r == no and c in set(shgt)
                 and w in HL and y in exantet and sp(no, c, w, y) and not g(ab, no, c, w, y) and bm(no, c, w)})
    trust_if(no, shgt, HL, exantet, TRUST_NAT)
    # ---- l. 1469-1513 TUR
    tu = "TUR"
    trows = ("POUM", "SGMT")
    S.apply(ab, {(tu, c, w, y): d1(tu, c, w, y) + (d1(tu, c, w, L) + (y - L) * (d1(tu, c, w, L) - bm(tu, c, w))
                                                 / (L - base)) * (y > L)
                 for c in MKP for w in trows for y in after_t})
    # l. 1481-1484: their trust level needs expertdairy_map(MrkKeyPos, rows), which holds no POUM or SGMT: none set
    S.apply(ab, {(tu, c, "POUM", y): sp(tu, c, "POUM", y) for c in poul for y in after_t})
    S.apply(tr, {(tu, c, "POUM", y): TRUST_NAT + 3 for c in poul for y in after_t})
    S.apply(ab, {(tu, c, w, y): sp(tu, c, w, y) for (r, c, w, y) in list(sup) if r == tu and c in set(shgt)
                 and w in HL and y in exantet and sp(tu, c, w, y) and not g(ab, tu, c, w, y) and bm(tu, c, w)})
    trust_if(tu, shgt, HL, exantet, TRUST_NAT)

    # ---- l. 1514-1565 (.ti31a): the dairy supports back to Absolute in absDairyRunr after 2020
    n02 = set(X.nuts0_and_2)
    absd = set(one("absdairyrunr"))
    inmap = lambda k: (k[1], k[2]) in emap and k[1] in s_cols and k[2] in s_rows  # noqa: E731
    S.apply(pc, {k: 0.0 for k in keys(ab, pred=lambda k: k[0] in n02 and k[3] in exantet and k[3] <= AFTER
                                       and inmap(k))})
    S.apply(ab, {k: (100 + pc[k]) / 100 * bm(*k[:3]) for k in keys(pc, pred=lambda k: k[0] in n02 and k[0] in absd
                                                                 and k[3] in exantet and k[3] > AFTER and inmap(k))})
    S.apply(pc, {k: 0.0 for k in keys(ab, pred=lambda k: k[0] in n02 and k[0] in absd and k[3] in exantet
                                       and k[3] > AFTER and inmap(k))})
    S.apply(ab, {k: 0.0 for k in keys(pc, pred=lambda k: k[0] in set(runr) and k[3] in exantet
                                       and (k[1], k[2]) in emap)})
    return nat
