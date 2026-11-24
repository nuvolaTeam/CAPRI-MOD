r"""CAPRI's estimation model of the baseline feed calibration (feed/fedtrm_mod_pw.gms; CAPRI star 3.0, feed version
"_pw"): m_hpdFeed, the highest posterior density estimator of the feed input coefficients and the energy and protein
requirements of one set of regional units at given herds and feed quantities, and the a priori standard deviations
of the requirements.

The model (MODEL m_hpdFeed, l. 294-300) maximises hpdFeed_ subject to CAPRI's rows FEDUSE_, FEDUSEA_, FEDUSES_,
FEDAGGR_, REQSE_, NutContFeed_ and FeedAggrShare_ (capri_mod/supply/equations/supply_model/feeding.py), over CAPRI's
variables v_feedInpCoeff (the feeds and the feed aggregates), v_animReq, v_NutContFeed, v_FeedAggrShare,
v_feedQuantReg and v_lossQuant (GamsVar below: their levels and bounds, set by the driver, capri_mod/feed/equations/
fedtrm_cal_pw.py); v_actLevl is fixed. As GAMS's holdfixed = 1 (fedtrm_cal_pw.gms l. 534) a fixed variable enters as
a constant, and a row left without variables is checked, not solved.

Departures from CAPRI:
- The solver is IPOPT (CasADi) where CAPRI uses CONOPT (no CONOPT licence): the same optimum where it is unique; on
  a flat objective the two can stop at different points of nearly equal objective (claude/feed_calibration_port_plan_
  2026-11-24.md, S3b). Measured over CAPRI's 34 member states and non-EU countries with a calibration (25 November
  2026, tools/check/check_fedtrm_cal_2030.py): every feed input coefficient within 1% of sim_ini_21730's; within 1e-4
  in at least 95% of the cells in 29 of them, and in 69% (PT), 76% (TUR), 83% (BG), 91% (ES) and 95% (CZ) in the
  others. The model is not convex: from CAPRI's own solution as the start, the port reaches a slightly higher
  objective than from the priors (PT000000 -5.21824 against -5.21868), so the priors' start ends at a slightly worse
  local optimum there (KNOWN_ISSUES K206). IPOPT's options: IPOPT_OPTIONS; "acceptable_iter" 0 switches off IPOPT's stop at an
  "acceptable level", which had ended a solve early. A solve counts as infeasible as CONOPT's numinfes > 0 does: when
  a row is violated at the solution beyond FEAS_TOL, after dividing it by max(1, its largest Jacobian entry) (the scale
  CONOPT's tolerance applies to).
- CST_ (l. 104-108), the feed cost, is left out with its variable v_feedCost: it enters no other row nor the objective,
  its only effect would be the bounds of v_feedCost (0.001 to 1000 times its expected value, fedtrm_cal_pw.gms
  l. 378-381) on the ration's cost, and its unit values and expected costs (UVAG, TOOU, PRME, FEED of baseline/
  fedtrm_prep.gms l. 94-134) are not ported. Its effect is to be measured as nil on CAPRI's solutions (the S3b
  check's feed cost ratio, with CAPRI's expected cost since 25 November 2026).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set
from capri_mod.supply.equations.supply_model import feeding as fe

INF = float("inf")
#: IPOPT's options for m_hpdFeed: CAPRI's ITERLIM (fedtrm_cal_pw.gms l. 532: 10000 iterations; CONOPT's iterations
#: are not IPOPT's), IPOPT's tolerance, and no stop at IPOPT's "acceptable level"
IPOPT_OPTIONS = {"ipopt.print_level": 0, "print_time": False, "ipopt.max_iter": 10000, "ipopt.tol": 1e-10,
                 "ipopt.acceptable_iter": 0}
#: a row's violation at the solution, over max(1, its largest Jacobian entry), above which the solve is infeasible
FEAS_TOL = 1e-7


@dataclass
class GamsVar:
    """A GAMS variable's attributes for its keys: L (level), LO and UP (bounds); an absent key is at the declaration's
    default (a POSITIVE VARIABLE: lo 0, up +inf; a free one: -inf, +inf; level 0). fx is GAMS's .FX."""
    lo0: float = 0.0
    up0: float = INF
    L: dict = field(default_factory=dict)
    LO: dict = field(default_factory=dict)
    UP: dict = field(default_factory=dict)

    def l(self, k) -> float:  # noqa: E743
        return self.L.get(k, 0.0)

    def lo(self, k) -> float:
        return self.LO.get(k, self.lo0)

    def up(self, k) -> float:
        return self.UP.get(k, self.up0)

    def fx(self, k, v: float) -> None:
        self.LO[k] = self.UP[k] = self.L[k] = v

    def fixed(self, k) -> bool:
        return self.lo(k) == self.up(k)


def free_var() -> GamsVar:
    """A free GAMS variable (VARIABLES without POSITIVE: v_NutContFeed, v_FeedAggrShare)."""
    return GamsVar(lo0=-INF, up0=INF)


def p_aprDistAnimReq_StdDev(st) -> None:
    r"""The a priori standard deviations of the requirements: by animal (the higher, the larger the correction), and by
    requirement (the lower, the slower the correction).

    CAPRI's GAMS (feed/fedtrm_mod_pw.gms l. 67-86):

            p_aprDistAnimReq("ALL",MAACT,"T","ALL","StdDev"  %addtimedim_ast%)             = 0.2;
            p_aprDistAnimReq("ALL","DCOL","T","ALL","StdDev" %addtimedim_ast%)            = 0.25;
        *
            p_aprDistAnimReq("ALL",BULF,"T","ALL","StdDev" %addtimedim_ast%)              = 0.25;
            p_aprDistAnimReq("ALL",HEIF,"T","ALL","StdDev" %addtimedim_ast%)              = 0.25;
        *
            p_aprDistAnimReq("ALL","CAMR","T","ALL","StdDev" %addtimedim_ast%)            = 0.3;
            p_aprDistAnimReq("ALL","CAFR","T","ALL","StdDev" %addtimedim_ast%)            = 0.3;
            p_aprDistAnimReq("ALL","HEIR","T","ALL","StdDev" %addtimedim_ast%)            = 0.3;
            p_aprDistAnimReq("ALL","SCOW","T","ALL","StdDev" %addtimedim_ast%)            = 0.3;
        *
            p_aprDistAnimReq("ALL","SHGM","T","ALL","StdDev" %addtimedim_ast%)            = 0.3;
            p_aprDistAnimReq("ALL","SHGF","T","ALL","StdDev" %addtimedim_ast%)            = 0.3;
        *
        *   *** relative weight for deviation from requirements defined by requirement functions for different
        *       requirements ( the lower the number, the slower the correction)
        *
            p_aprDistAnimReq("ALL","ALL","T",REQM,  "StdDev" %addtimedim_ast%)  = 0.1;
            p_aprDistAnimReq("ALL","ALL","T","ENNE","StdDev" %addtimedim_ast%)  = 0.01;
            p_aprDistAnimReq("ALL","ALL","T","CRPR","StdDev" %addtimedim_ast%)  = 0.1;

    Departures from CAPRI: none."""
    d = st.p_aprDistAnimReq
    for a in st.MAACT:
        d[("ALL", a, "T", "ALL", "StdDev")] = 0.2
    d[("ALL", "DCOL", "T", "ALL", "StdDev")] = 0.25
    for a in capri_set("BULF") + capri_set("HEIF"):
        d[("ALL", a, "T", "ALL", "StdDev")] = 0.25
    for a in ("CAMR", "CAFR", "HEIR", "SCOW"):
        d[("ALL", a, "T", "ALL", "StdDev")] = 0.3
    for a in ("SHGM", "SHGF"):
        d[("ALL", a, "T", "ALL", "StdDev")] = 0.3
    for q in st.REQM:
        d[("ALL", "ALL", "T", q, "StdDev")] = 0.1
    d[("ALL", "ALL", "T", "ENNE", "StdDev")] = 0.01
    d[("ALL", "ALL", "T", "CRPR", "StdDev")] = 0.1


def ncpcm(x, y, Z):
    r"""GAMS's intrinsic ncpcm(x, y, Z), Chen and Mangasarian's smoothed min(x, y) of width Z: x - Z ln(1 + exp((x - y)
    / Z)) (GAMS's NLPEC manual, equation 11, the function NCPCM), written as x - Z softplus((x - y) / Z) with the
    softplus in its overflow-free form (the same function; GAMS's intrinsic is evaluated stably too)."""
    import casadi as ca
    z = (x - y) / Z
    return x - Z * ca.if_else(z > 0, z + ca.log1p(ca.exp(-z)), ca.log1p(ca.exp(z)))


class HpdFeedModel:
    """m_hpdFeed for the units RUNR and their aggregate RUNAGG on FedtrmState st (its GamsVar variables and
    parameters): the variables (a CasADi symbol for each variable not fixed, the fixed value otherwise), the rows and
    the objective. CAPRI's R_RAGG(RUNR, MSACT) is st.MS for every unit."""

    def __init__(self, st, RUNR, RUNAGG):
        import casadi as ca
        self.ca, self.st, self.RUNR, self.RUNAGG = ca, st, tuple(RUNR), tuple(RUNAGG)
        self.X, self.x0, self.lbx, self.ubx, self.names = [], [], [], [], []
        self.G, self.gnames, self.const_rows = [], [], []
        self._sym = {}

    def var(self, fam: str, key):
        """The variable fam(key) of the model: its symbol, or its value where fixed (holdfixed)."""
        k = (fam, key)
        if k in self._sym:
            return self._sym[k]
        gv = getattr(self.st, fam)
        lo, up = gv.lo(key), gv.up(key)
        if lo == up:
            self._sym[k] = lo
            return lo
        s = self.ca.SX.sym(f"{fam}[{','.join(map(str, key))}]")
        self.X.append(s)
        self.x0.append(min(max(gv.l(key), lo), up))
        self.lbx.append(lo)
        self.ubx.append(up)
        self.names.append(k)
        self._sym[k] = s
        return s

    def lev(self, r, a, t) -> float:
        """v_actLevl(r, a, t), fixed by the driver (fedtrm_cal_pw.gms l. 260)."""
        return self.st.v_actLevl_L.get((r, a, t), 0.0)

    def content(self, item, f) -> float:
        """SUM(R_RAGG(RUNR, MSACT), DATA(MSACT, item, FEED, "Y")): the member state's content of the feed."""
        return float(self.st.DATA.get((self.st.MS, item, f), 0.0) or 0.0)

    def row(self, name, expr) -> None:
        """A row = 0; one without variables (all fixed) is kept aside with its residual."""
        if isinstance(expr, (int, float)) or self.ca.SX(expr).is_constant():
            self.const_rows.append((name, float(expr)))
        else:
            self.G.append(expr)
            self.gnames.append(name)



def feed_rows(m: HpdFeedModel) -> None:
    """m_hpdFeed's rows (l. 294-299; CST_ left out, see the module docstring), each by its function in
    capri_mod/supply/equations/supply_model/feeding.py, on CAPRI's domains:
    REQSE_ $ (p_animReq $ p_technFact LEVL), NutContFeed_ $ (p_NutContFeed MIN or MAX or MEAN), FeedAggrShare_ $
    p_animReq DRMA, FEDAGGR_ $ p_technFact LEVL, FEDUSE_ $ (v_feedQuantReg.LO ne .UP), FEDUSES_ $ (p_feedQuant >
    1e-6), FEDUSEA_ $ (p_maxFeedShare of the aggregate $ more than one unit $ (not FODDI or FSTR)). Of NutContFeed_
    only the rows of an animal with the requirement (p_animReq) are written: elsewhere v_NutContFeed enters the
    objective with weight 0 (its weights carry the requirement) and no other row, so the row would only define it."""
    st = m.st
    aggr = {g: [f for (f, g2) in st.Feed_FeedAggr if g2 == g] for g in st.FeedAggr}
    fic = lambda r, a, t, j: m.var("v_feedInpCoeff", (r, a, t, j))  # noqa: E731
    for r in m.RUNR:
        for a in st.MAACT:
            for t in st.A:
                has_tf = bool(st.p_technFact.get((r, a, "LEVL", t), 0.0))
                for q in st.REQMSE:
                    if st.p_animReq.get((r, a, t, q), 0.0) and has_tf:
                        ration = sum(fic(r, a, t, f) * m.content(q, f) for f in st.FEED
                                     if st.p_maxFeedShare.get((r, a, t, f), 0.0))
                        m.row(("REQSE_", r, a, t, q), fe.REQSE_trim(m.var("v_animReq", (r, a, t, q)),
                                                                  st.p_animProdDays.get((r, a, t), 0.0), ration))
                    if not st.p_animReq.get((r, a, t, q), 0.0):
                        continue
                    for g in st.FeedAggr:
                        if any(st.p_NutContFeed.get((r, a, t, q, g, s), 0.0) for s in ("MIN", "MAX", "MEAN")):
                            nut = sum(fic(r, a, t, f) * m.content(q, f) for f in aggr[g])
                            drma = sum(fic(r, a, t, f) * m.content("DRMA", f) for f in aggr[g])
                            m.row(("NutContFeed_", r, a, t, q, g),
                                  fe.NutContFeed_(m.var("v_NutContFeed", (r, a, t, q, g)), nut, drma))
                if st.p_animReq.get((r, a, t, "DRMA"), 0.0):
                    for g in st.FeedAggr:
                        m.row(("FeedAggrShare_", r, a, t, g),
                              fe.FeedAggrShare_(fic(r, a, t, g), fic(r, a, t, "FeedTotal"),
                                                m.var("v_FeedAggrShare", (r, a, t, g))))
                if has_tf:
                    for g in st.FeedAggr:
                        drma = sum(fic(r, a, t, f) * m.content("DRMA", f) for f in aggr[g])
                        m.row(("FEDAGGR_", r, a, t, g), fe.FEDAGGR_(fic(r, a, t, g), drma))
    for r in m.RUNR:
        for f in st.FEED:
            if st.v_feedQuantReg.lo((r, f)) != st.v_feedQuantReg.up((r, f)):
                use = sum(fic(r, a, t, f) * m.lev(r, a, t) for a in st.MAACT for t in st.A
                          if st.p_maxFeedShare.get((r, a, t, f), 0.0))
                m.row(("FEDUSE_", r, f),
                      fe.FEDUSE_row(use, m.var("v_lossQuant", (r, "STRA")) if f == "FSTR" else 0.0,
                                    m.var("v_lossQuant", (r, "COMF")) if f == "FCOM" else 0.0,
                                    m.var("v_feedQuantReg", (r, f))))
            if st.p_feedQuant.get((r, f), 0.0) > 1.E-6:
                m.row(("FEDUSES_", r, f), fe.FEDUSES_(m.var("v_feedQuantReg", (r, f)), st.p_feedQuant[(r, f)]))
    if len(m.RUNR) != 1:
        for ra in m.RUNAGG:
            for a in st.MAACT:
                for t in st.A:
                    for f in st.FEED:
                        if not st.p_maxFeedShare.get((ra, a, t, f), 0.0) or (f in st.FODDI and f != "FSTR"):
                            continue
                        use = sum(fic(r, a, t, f) * m.lev(r, a, t) for r in m.RUNR
                                  if st.p_maxFeedShare.get((r, a, t, f), 0.0))
                        m.row(("FEDUSEA_", ra, a, t, f), fe.FEDUSEA_(use, fic(ra, a, t, f), m.lev(ra, a, t)))


def hpdFeed_(m: HpdFeedModel):
    r"""hpdFeed_ (l. 132-291), the objective v_hpdFeed: minus the weighted squared deviations from the priors, over the
    sum of their weights (a constant: the herds are fixed). Returns (numerator, denominator); m_hpdFeed maximises
    numerator / denominator.

    CAPRI's GAMS (feed/fedtrm_mod_pw.gms l. 128-291):

        *       ---------------- objective function ------------------------------------------------------------------------------------
        *
        *                        Highest Posterior Density: find minimal deviations from expected mean weighted with a priori variance
        *
            hpdFeed_..
        *
               v_hpdFeed


                         =E=

        *
        *
        *         ---- All relative deviations per animal are weighted with the "importance" of that animal type for the total sector.
        *              Otherwise the solver may try to fix any balancing needs with modifications on 1-2 'large' activities
        *              because this is 'cheaper' in terms of the penalties than fiddling around with all activities

        *
        *         ---- deviation of requirements from mean of a priori expectation
        *
                   (
                    - 1E5 * SUM( (RUNR,MAACT,A,REQMSE %addtimedim%) $ p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%),
                                  SQR( (v_animReq(RUNR,MAACT,A,REQMSE %addtimedim%) - p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%))
                                     /  p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%))
        *              weighting:
                               * [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01)*p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%)*p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)

        *         ---- deviation of sub regional total feed intake from sub regional average (dry intake equal across regions)
        *

                    - 1E4 * SUM( (RUNAGG,RUNR,MAACT,A %addtimedim%) $ p_AnimReq(RUNR,MAACT,A,"ENNE" %addtimedim%),
                                  SQR( (v_feedInpCoeff(RUNR,MAACT,A,"FeedTotal" %addtimedim%)-v_feedInpCoeff(RUNAGG,MAACT,A,"FeedTotalSubRegionAvg" %addtimedim%))
                                     / (v_feedInpCoeff(RUNAGG,MAACT,A,"FeedTotalSubRegionAvg" %addtimedim%) + 1E-3)))

        *         ---- deviation of regional feed intake from aggregate intake for non-ruminants
        *              (non-ruminants do not depend on regional fodder production, should be similar across regions))
        *
                    - 1E4 * SUM( (RUNAGG,RUNR,MNRUMI,A,FEED %addtimedim%) $ p_maxFeedShare(RUNR,MNRUMI,A,Feed %addtimedim%),
                                  SQR( (v_feedInpCoeff(RUNR,MNRUMI,A,FEED %addtimedim%) - v_feedInpCoeff(RUNAGG,MNRUMI,A,FEED %addtimedim%))
                                     / (v_feedInpCoeff(RUNAGG,MNRUMI,A,FEED %addtimedim%) + 1E-4)))

        *
        *         ---- deviation of nutrition content from expected feeding practices (typical energy/protein density for aggregates)
        *
                     - 1E2 * SUM( (RUNR,MAACT,A,REQMSE,FeedAggr %addtimedim%) $ p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MEAN" %addtimedim%),
                                   SQR( (p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MEAN" %addtimedim%)-v_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr %addtimedim%))
                                      / (p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MEAN" %addtimedim%)))
        *              weighting:
                                 * [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01)*p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%)*p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)


        *         ---- nutrient content in feed: high penalty for the part of the estimates over or under the lower/upper limits
        *
                    - 1E3 * SUM( (RUNR,MAACT,A,REQMSE,FeedAggr %addtimedim%) $ ( p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MAX" %addtimedim%)
                                                                  $ p_aprDistAnimReq(RUNR,MAACT,A,"ENNE","MEAN" %addtimedim%)),
                                  SQR( (-ncpcm(-v_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr %addtimedim%),
                                               -p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MAX" %addtimedim%),
                                               max(.01,.05*p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MAX" %addtimedim%)))
                                        -p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MAX" %addtimedim%))
                                      / MAX(.1,ABS(p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MAX" %addtimedim%))))
        *              weighting:
                                * [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01)*p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%)*p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
        *
                     - 1E3 * SUM( (RUNR,MAACT,A,REQMSE,FeedAggr %addtimedim%) $ ( p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MIN" %addtimedim%)
                                                                   $ p_aprDistAnimReq(RUNR,MAACT,A,"ENNE","MEAN" %addtimedim%)),
                                  SQR( ( ncpcm( v_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr %addtimedim%),
                                                p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MIN" %addtimedim%),
                                                max(.01,.05*p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MIN"%addtimedim%)))
                                        -p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MIN"%addtimedim%))
                                     / MAX(.1,ABS(p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MIN"%addtimedim%))))
        *              weighting:
                                * [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01)*p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%)*p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
        *
        *
        *         ---- shares of feed aggregates: high penalty for the part of the estimates over or under the lower/upper limits
        *

                    - 1E4 * SUM( (RUNR,MAACT,A,FeedAggr %addtimedim%) $ ( p_maxFeedShare(RUNR,MAACT,A,FeedAggr %addtimedim%)
                                                           $ p_aprDistAnimReq(RUNR,MAACT,A,"ENNE","MEAN" %addtimedim%)),
                                  SQR( (-ncpcm(-v_FeedAggrShare(RUNR,MAACT,A,FeedAggr %addtimedim%),
                                               -p_maxFeedShare(RUNR,MAACT,A,FeedAggr %addtimedim%),
                                               max(.02,.05*p_maxFeedShare(RUNR,MAACT,A,FeedAggr %addtimedim%)))
                                        -p_maxFeedShare(RUNR,MAACT,A,FeedAggr %addtimedim%))
                                     / MAX(.1,ABS(p_maxFeedShare(RUNR,MAACT,A,FeedAggr %addtimedim%))))
        *              weighting:
                                * [  max(SUM(R_RAGG(RUNR,MSACT),p_feedInpCoeffDRMA(MSACT,maact,A,FeedAggr,"Adjusted" %addtimedim%)),.1)
                                   * (v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01)*p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
        *
                    - 1E4 * SUM( (RUNR,MAACT,A,FeedAggr %addtimedim%) $ ( p_minFeedShare(RUNR,MAACT,A,FeedAggr%addtimedim%)
                                                           $ p_aprDistAnimReq(RUNR,MAACT,A,"ENNE","MEAN" %addtimedim%)),
                                  SQR( ( ncpcm( v_FeedAggrShare(RUNR,MAACT,A,FeedAggr %addtimedim%),
                                                p_minFeedShare(RUNR,MAACT,A,FeedAggr%addtimedim%),
                                                max(.02,.05*p_minFeedShare(RUNR,MAACT,A,FeedAggr%addtimedim%)))
                                        -p_minFeedShare(RUNR,MAACT,A,FeedAggr%addtimedim%))
                                     / MAX(.1,ABS(p_minFeedShare(RUNR,MAACT,A,FeedAggr%addtimedim%))))
        *              weighting:
                                * [  max(SUM(R_RAGG(RUNR,MSACT),p_feedInpCoeffDRMA(MSACT,maact,A,FeedAggr,"Adjusted" %addtimedim%)),.1)
                                   * (v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01) *  p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
        *
        *         ---- penalty for deviation from expected feed input
        *
                    - 1E2 * SUM( (RUNR,MAACT,A,FEED%addtimedim%) $ (p_feedInpCoeff(RUNR,MAACT,A,FEED,"STDE" %addtimedim%) $ p_maxFeedShare(RUNR,MAACT,A,Feed %addtimedim%)),
                                 SQR( (v_feedInpCoeff(RUNR,MAACT,A,FEED%addtimedim%) - p_feedInpCoeff(RUNR,MAACT,A,FEED,"Mean"%addtimedim%))
                                    /  p_feedInpCoeff(RUNR,MAACT,A,FEED,"STDE"%addtimedim%))
        *              weighting:
                               * [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01) *  p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)


        *         ---- high penalty for the part of the estimates over or under the lower/upper limits
        *
                    - 1E4 * SUM( (RUNR,MAACT,A,Feed%addtimedim%) $ (p_FeedInpCoeff(RUNR,MAACT,A,Feed,"UppLim"%addtimedim%)),
                                  SQR((-ncpcm(-v_FeedInpCoeff(RUNR,MAACT,A,Feed %addtimedim%),
                                       -p_FeedInpCoeff(RUNR,MAACT,A,Feed,"UppLim"%addtimedim%),
                                        max(2,0.02*p_FeedInpCoeff(RUNR,MAACT,A,Feed,"UppLim"%addtimedim%)))
                                       -p_FeedInpCoeff(RUNR,MAACT,A,Feed,"UppLim"%addtimedim%))
                                    / MAX(.1,ABS(p_FeedInpCoeff(RUNR,MAACT,A,Feed,"UppLim"%addtimedim%))))
        *              weighting:
                                * [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01) * p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
        *
                     - 1E5  * SUM( (RUNR,MAACT,A,Feed%addtimedim%) $ ( p_FeedInpCoeff(RUNR,MAACT,A,Feed,"LowLim"%addtimedim%)
                                                         $ p_aprDistAnimReq(RUNR,MAACT,A,"ENNE","MEAN" %addtimedim%)),
                                    SQR( ( ncpcm(v_FeedInpCoeff(RUNR,MAACT,A,Feed %addtimedim%),
                                           p_FeedInpCoeff(RUNR,MAACT,A,Feed,"LowLim"%addtimedim%),
                                           max(2,0.05*p_FeedInpCoeff(RUNR,MAACT,A,Feed,"LowLim"%addtimedim%)))
                                          -p_FeedInpCoeff(RUNR,MAACT,A,Feed,"LowLim"%addtimedim%))
                                        / MAX(.1,ABS(p_FeedInpCoeff(RUNR,MAACT,A,Feed,"LowLim"%addtimedim%))))
        *              weighting:
                                  * [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01) * p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
        *
                    )
        *
        *         ---- weighting of objective function
        *
                 /
                   ( 1E5 * SUM( (RUNR,MAACT,A,REQMSE %addtimedim%) $ p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%),
                                [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01)*p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%)*p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
                    +1E4 * SUM( (RUNAGG,RUNR,MAACT,A %addtimedim%) $ p_AnimReq(RUNR,MAACT,A,"ENNE"%addtimedim%),1)
                    +1E4 * SUM( (RUNAGG,RUNR,MNRUMI,A,FEED %addtimedim%) $ p_maxFeedShare(RUNR,MNRUMI,A,Feed %addtimedim%),1)
                    +1E2 * SUM( (RUNR,MAACT,A,REQMSE,FeedAggr %addtimedim%) $ p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MEAN" %addtimedim%),
                                 [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01)*p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%)*p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
                    +1E3 * SUM( (RUNR,MAACT,A,REQMSE,FeedAggr %addtimedim%) $ ( p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MAX" %addtimedim%)
                                                                 $ p_aprDistAnimReq(RUNR,MAACT,A,"ENNE","MEAN" %addtimedim%)),
                                 [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01)*p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%)*p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
                    +1E3 * SUM( (RUNR,MAACT,A,REQMSE,FeedAggr %addtimedim%) $ ( p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MIN" %addtimedim%)
                                                                 $ p_aprDistAnimReq(RUNR,MAACT,A,"ENNE","MEAN" %addtimedim%)),
                                 [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01)*p_AnimReq(RUNR,MAACT,A,REQMSE %addtimedim%)*p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
                    +1E4 * SUM( (RUNR,MAACT,A,FeedAggr%addtimedim%) $ ( p_maxFeedShare(RUNR,MAACT,A,FeedAggr %addtimedim%)
                                                          $ p_aprDistAnimReq(RUNR,MAACT,A,"ENNE","MEAN" %addtimedim%)),
                                 [ max(SUM(R_RAGG(RUNR,MSACT),p_feedInpCoeffDRMA(MSACT,maact,A,FeedAggr,"Adjusted" %addtimedim%)),.1)
                                 * (v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01) *  p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
                    +1E4 * SUM( (RUNR,MAACT,A,FeedAggr%addtimedim%) $ ( p_minFeedShare(RUNR,MAACT,A,FeedAggr%addtimedim%)
                                                          $ p_aprDistAnimReq(RUNR,MAACT,A,"ENNE","MEAN" %addtimedim%)),
                                 [ max(SUM(R_RAGG(RUNR,MSACT),p_feedInpCoeffDRMA(MSACT,maact,A,FeedAggr,"Adjusted" %addtimedim%)),.1)
                                 * (v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01) *  p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
                    +1E2 * SUM( (RUNR,MAACT,A,FEED%addtimedim%) $ ( p_feedInpCoeff(RUNR,MAACT,A,FEED,"STDE"%addtimedim%)
                                                      $ p_maxFeedShare(RUNR,MAACT,A,Feed %addtimedim%)),
                                 [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01) *  p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
                    +1E4 * SUM( (RUNR,MAACT,A,Feed%addtimedim%) $ (p_FeedInpCoeff(RUNR,MAACT,A,Feed,"UppLim"%addtimedim%)),
                                 [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01) * p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
                    +1E5 * SUM( (RUNR,MAACT,A,Feed%addtimedim%) $ ( p_FeedInpCoeff(RUNR,MAACT,A,Feed,"LowLim"%addtimedim%)
                                                      $ p_aprDistAnimReq(RUNR,MAACT,A,"ENNE","MEAN" %addtimedim%)),
                                 [(v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%)+.01) * p_animProdDays(RUNR,MAACT,A %addtimedim%)]**.1)
                    )
                 ;

    Departures from CAPRI: none (the sums' domains as CAPRI's: a term whose condition holds but whose variables are
    all fixed is a constant, kept)."""
    st, sq = m.st, (lambda e: e * e)
    fic = lambda r, a, t, j: m.var("v_feedInpCoeff", (r, a, t, j))  # noqa: E731
    acts = [(r, a, t) for r in m.RUNR for a in st.MAACT for t in st.A]
    req = lambda r, a, t, q: st.p_animReq.get((r, a, t, q), 0.0)  # noqa: E731
    days = lambda r, a, t: st.p_animProdDays.get((r, a, t), 0.0)  # noqa: E731
    mean_enne = lambda r, a, t: st.p_aprDistAnimReq.get((r, a, t, "ENNE", "Mean"), 0.0)  # noqa: E731
    nutc = lambda r, a, t, q, g, s: st.p_NutContFeed.get((r, a, t, q, g, s), 0.0)  # noqa: E731
    pfc = lambda r, a, t, f, s: st.p_feedInpCoeff.get((r, a, t, f, s), 0.0)  # noqa: E731
    w_req = lambda r, a, t, q: ((m.lev(r, a, t) + .01) * req(r, a, t, q) * days(r, a, t)) ** .1  # noqa: E731
    w_fic = lambda r, a, t: ((m.lev(r, a, t) + .01) * days(r, a, t)) ** .1  # noqa: E731

    def w_shr(r, a, t, g):
        adj = st.p_feedInpCoeffDRMA.get((st.MS, a, t, g, "Adjusted"), 0.0)
        return (max(adj, .1) * (m.lev(r, a, t) + .01) * days(r, a, t)) ** .1

    num, den = 0.0, 0.0
    # 1. the requirements' deviations from the requirement functions'
    for (r, a, t) in acts:
        for q in st.REQMSE:
            if req(r, a, t, q):
                num += -1E5 * sq((m.var("v_animReq", (r, a, t, q)) - req(r, a, t, q)) / req(r, a, t, q)) * w_req(r, a, t, q)
                den += 1E5 * w_req(r, a, t, q)
    # 2. the units' total intake from the units' average
    for ra in m.RUNAGG:
        for (r, a, t) in acts:
            if req(r, a, t, "ENNE"):
                avg = fic(ra, a, t, "FeedTotalSubRegionAvg")
                num += -1E4 * sq((fic(r, a, t, "FeedTotal") - avg) / (avg + 1E-3))
                den += 1E4
    # 3. the non-ruminants' coefficients from the aggregate's
    for ra in m.RUNAGG:
        for (r, a, t) in acts:
            if a not in st.MNRUMI:
                continue
            for f in st.FEED:
                if st.p_maxFeedShare.get((r, a, t, f), 0.0):
                    num += -1E4 * sq((fic(r, a, t, f) - fic(ra, a, t, f)) / (fic(ra, a, t, f) + 1E-4))
                    den += 1E4
    # 4.-6. the aggregates' nutrient densities: from the expected, and beyond their limits
    for (r, a, t) in acts:
        for q in st.REQMSE:
            for g in st.FeedAggr:
                mn, mx, mi = nutc(r, a, t, q, g, "MEAN"), nutc(r, a, t, q, g, "MAX"), nutc(r, a, t, q, g, "MIN")
                if not (mn or mx or mi):
                    continue
                w = w_req(r, a, t, q)
                v = m.var("v_NutContFeed", (r, a, t, q, g)) if req(r, a, t, q) else None
                if mn:
                    if v is not None:
                        num += -1E2 * sq((mn - v) / mn) * w
                    den += 1E2 * w
                if mx and mean_enne(r, a, t):
                    if v is not None:
                        num += -1E3 * sq((-ncpcm(-v, -mx, max(.01, .05 * mx)) - mx) / max(.1, abs(mx))) * w
                    den += 1E3 * w
                if mi and mean_enne(r, a, t):
                    if v is not None:
                        num += -1E3 * sq((ncpcm(v, mi, max(.01, .05 * mi)) - mi) / max(.1, abs(mi))) * w
                    den += 1E3 * w
    # 7.-8. the aggregates' shares beyond their maximum and minimum
    for (r, a, t) in acts:
        if not mean_enne(r, a, t):
            continue
        for g in st.FeedAggr:
            mx, mi = st.p_maxFeedShare.get((r, a, t, g), 0.0), st.p_minFeedShare.get((r, a, t, g), 0.0)
            if mx:
                sh = m.var("v_FeedAggrShare", (r, a, t, g))
                num += -1E4 * sq((-ncpcm(-sh, -mx, max(.02, .05 * mx)) - mx) / max(.1, abs(mx))) * w_shr(r, a, t, g)
                den += 1E4 * w_shr(r, a, t, g)
            if mi:
                sh = m.var("v_FeedAggrShare", (r, a, t, g))
                num += -1E4 * sq((ncpcm(sh, mi, max(.02, .05 * mi)) - mi) / max(.1, abs(mi))) * w_shr(r, a, t, g)
                den += 1E4 * w_shr(r, a, t, g)
    # 9.-11. the coefficients from their prior mean, and beyond their soft limits
    for (r, a, t) in acts:
        for f in st.FEED:
            sd = pfc(r, a, t, f, "STDE")
            if sd and st.p_maxFeedShare.get((r, a, t, f), 0.0):
                num += -1E2 * sq((fic(r, a, t, f) - pfc(r, a, t, f, "Mean")) / sd) * w_fic(r, a, t)
                den += 1E2 * w_fic(r, a, t)
            u = pfc(r, a, t, f, "UppLim")
            if u:
                num += -1E4 * sq((-ncpcm(-fic(r, a, t, f), -u, max(2, 0.02 * u)) - u) / max(.1, abs(u))) * w_fic(r, a, t)
                den += 1E4 * w_fic(r, a, t)
            lo = pfc(r, a, t, f, "LowLim")
            if lo and mean_enne(r, a, t):
                num += -1E5 * sq((ncpcm(fic(r, a, t, f), lo, max(2, 0.05 * lo)) - lo) / max(.1, abs(lo))) * w_fic(r, a, t)
                den += 1E5 * w_fic(r, a, t)
    return num, den


def m_hpdFeed(st, RUNR, RUNAGG) -> HpdFeedModel:
    r"""MODEL m_hpdFeed (l. 294-300) and its attributes for the units RUNR and their aggregate RUNAGG: the rows
    (feed_rows) and the objective (hpdFeed_), CST_ left out (the module docstring).

    CAPRI's GAMS (feed/fedtrm_mod_pw.gms l. 294-319):

          MODEL  m_hpdFeed   /
                             CST_,
                             FEDUSE_,FEDUSEA_,FEDUSES_, FEDAGGR_,
                             REQSE_,
                             NutContFeed_,
                             FeedAggrShare_,
                             hpdFeed_/;




        * use CONOPT3 options file to increase # of iterations etc.

          OPTION LIMROW=0;
          OPTION LIMCOL=0;
        *
          m_hpdFeed.SYSOUT    = 0;
          m_hpdFeed.SOLPRINT  = 2;
          m_hpdFeed.OPTFILE   = 1;
        *                                      *** not more then sixty minutes
          m_hpdFeed.RESLIM    = 30 * 60 * 100/%procSpeedRelative%;
          m_hpdFeed.ITERLIM   = 1000000.;
          m_hpdFeed.WORKSPACE = 60;
          m_hpdFeed.HOLDFIXED = 1.;
          m_hpdFeed.SCALEOPT  = 0.;
          m_hpdFeed.SOLVELINK = 2;

    Departures from CAPRI: CST_ (the module docstring). The attributes are CONOPT's: HOLDFIXED = 1 is kept (a fixed
    variable enters as a constant, HpdFeedModel.var), the iteration limit is the driver's 10000
    (fedtrm_cal_pw.gms l. 532, IPOPT_OPTIONS), and the rest (SYSOUT, SOLPRINT, OPTFILE, RESLIM, WORKSPACE, SCALEOPT,
    SOLVELINK) have no counterpart with IPOPT."""
    m = HpdFeedModel(st, RUNR, RUNAGG)
    feed_rows(m)
    m.num, m.den = hpdFeed_(m)
    return m


def solve_m_hpdFeed(m: HpdFeedModel) -> dict:
    """SOLVE m_hpdFeed MAXIMISING v_hpdFeed USING NLP, with IPOPT: the solution's levels written to the GamsVar
    variables; returns {"feasible", "status", "objective", "iterations", "max_violation"} (the module docstring for
    the feasibility)."""
    ca = m.ca
    x = ca.vertcat(*m.X)
    g = ca.vertcat(*m.G) if m.G else ca.SX(0, 1)
    f = -m.num / m.den if m.den else -m.num
    solver = ca.nlpsol("m_hpdFeed", "ipopt", {"x": x, "f": f, "g": g}, IPOPT_OPTIONS)
    res = solver(x0=m.x0, lbx=m.lbx, ubx=m.ubx, lbg=0.0, ubg=0.0)
    xs = [float(v) for v in res["x"].full().ravel()]
    for (fam, key), v in zip(m.names, xs):
        getattr(m.st, fam).L[key] = v
    stats = solver.stats()
    viol = 0.0
    if m.G:
        gv, J = ca.Function("g", [x], [g, ca.jacobian(g, x)])(xs)
        Jc = J.sparse().tocsr()
        Jc.data = abs(Jc.data)
        scale = [max(1.0, float(v)) for v in Jc.max(axis=1).toarray().ravel()]
        viol = max(abs(v) / s for v, s in zip(gv.full().ravel(), scale))
    for _, c in m.const_rows:
        viol = max(viol, abs(c))
    return {"feasible": viol <= FEAS_TOL and math.isfinite(float(res["f"])), "status": stats.get("return_status"),
            "objective": -float(res["f"]), "iterations": stats.get("iter_count"), "max_violation": viol}
