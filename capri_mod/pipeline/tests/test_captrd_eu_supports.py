"""CAPTRD's supports after the first estimation (stage 2f, define_eu_supports.gms; eu_supports.py), in the order of the
ex-ante loop, on the supports as define_stats_and_supports.gms leaves them (test_captrd_expert_support.py's assembled
chain) and CAPTRD's stored Solve1 results (step2) and Solve2 results of the earlier years (step3, for the
extrapolation beyond %lst_dgagri%); compared with CAPTRD's final support, TrustLevl, wVarErr and DGAgri1 of the member
states in the ex-ante years without data (2020-2070; 2018 is a nowcast year whose supports are COCO's).

Results on 11 November 2026 (positions equal / compared; "later": rewritten after this stage, as in
test_support1_equal_captrds; "2c": rows whose EU parts' DGAgri1 already differ from CAPTRD's as stage 2c leaves them,
EU014000's INDM, FEDM, PRCM and DOMM of WHEP, DWHE, RYEM, OCER, RAPO, MAIZ, HFCS and CERE, which no later stage
rewrites there, from p_data that CAPTRD's stored P_Data no longer holds; "fossil": UVAG of DISL, GASL, open since
support1):
  support    434,701 of 455,713; later 18,417, 2c 2,149, fossil 40, other 406
  TrustLevl  107,619 of 107,958; later 234, fossil 20, other 85
  wVarErr    105,922 of 107,647 (where a trust level is set); later 367, 2c 999, fossil 40, other 319
  DGAgri1     26,017 of  28,151; later 390, 2c 1,077, fossil 290, other 377
The other positions: the members of EU013000 for DOMM of BEEF, SGMT, MOLA and PLMO and INDM of MOLA and PLMO (their
DGAgri1 off by one factor per aggregate, so the aggregate's DGAgri1, which CAPTRD's stored results do not keep for
EU013000 (the reporting re-aggregates it), is the likely source), with the trade positions that follow; the trust
levels of NECR.LEVL where CAPTRD's Expert is an explicit zero (EPS, a nonzero for GAMS's conditions; the port keeps no
zero records), of INHA.LEVL of UK000000 and NO000000 after 2040 and of OILS.LEVL of CY000000 after 2040. The NO000000
and TUR trust levels left open by test_captrd_expert_support.py are equal.
"""
from __future__ import annotations

import copy

import pandas as pd
import pytest

from capri_mod.pipeline.captrd import eu_supports as EU
from capri_mod.pipeline.captrd import final_supports as F
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.captrd import timesets as TS
from capri_mod.pipeline.tests.test_captrd_expert_support import assembled, REQST, K  # noqa: F401
from capri_mod.pipeline.tests.test_captrd_national_supports import (  # noqa: F401
    state, dgagri, aglink_p, scaled, result, need, _ref, G, DAT)
from capri_mod.pipeline.tests.test_captrd_macro import population  # noqa: F401

#: baseline/aglink2023dgAgri_mappings.gms l. 36-37 (rmAggSup), l. 41-44 (EUparts); captrd.gms l. 655 (CurEuropAgg)
AGLINK_RMAGGSUP = ["EU013000", "EU014000"]
EUPARTS = ["EU014000", "EU013000"]
CUR_EUROP_AGG = ["EU014000", "EU013000", "EU27yr19"]
#: sets_captrd.gms l. 466
AACT_365 = ["DCOW", "DCOL", "DCOH", "SCOW", "SOWS", "SHGM", "HENS"]
#: baseline/load_aglink2023dgAgri.gms l. 19
PRIC = ["UVAG"]
#: captrd.gms l. 166
PHASE_IN = 2025
#: the rows whose EU parts' DGAgri1 differ from CAPTRD's after stage 2c (test_eu_supports_equal_captrds)
ROWS_2C = ["WHEP", "DWHE", "RYEM", "OCER", "RAPO", "MAIZ", "HFCS", "CERE"]


def _kv4(df):
    return {(r, c, w, int(t)): v for r, c, w, t, v in zip(df.region, df.col, df.row, df.t, df.value) if v}


@pytest.fixture(scope="module")
def after(assembled, scaled):  # noqa: F811
    E0, TL0, sup0, X, s, nobs, ex = assembled
    rd = lambda n: pd.read_csv(P.SETS_DIR / f"{n}.csv", keep_default_na=False)    # noqa: E731
    one = lambda n: rd(n).d0.tolist()                                            # noqa: E731
    two = lambda n: list(zip(rd(n).d0, rd(n).d1))                                # noqa: E731
    gl = pd.read_csv(P.SETS_DIR / "globiom" / "euallagg.csv").d0.tolist()
    simg = lambda n: pd.read_csv(G / f"{n}.csv", keep_default_na=False)          # noqa: E731
    rto = simg("R_T_OAGG")
    cols1, rows1 = EU.est_sets(s.s_colsest, s.s_rowsest)
    S = EU.Sets(ms=list(X.ms), rmaggsup=sorted(set(one("rmaggsup")) | set(AGLINK_RMAGGSUP)),
                ms_to_agg=[(b, a) for a, b in X.map_rr if a in set(gl)], euparts=EUPARTS, cur_europ_agg=CUR_EUROP_AGG,
                s_colsest=cols1, s_rowsest=rows1, mrkbalee=one("mrkbalee"),
                dompos=one("dompos"), pric=PRIC, pact_to_y=list(X.pact_to_y), pact_to_io=two("pact_to_io"),
                maact=list(s.maact), mcact=one("mcact"), cact=list(s.cact), grpc=one("grpc"), grpr=one("grpr"),
                cropc_to_g=[(b, a) for a, b in two("cropc_to_g")], rows_to_g=[(b, a) for a, b in two("rows_to_g")],
                aact_365=AACT_365, meas=rto[rto.d0 == "MEAS"].d1.tolist(), tradeest=one("tradeest"),
                secod=simg("SECOD").d0.tolist(), prcd=two("prcd"), dcow=["DCOL", "DCOH"], biof=ex["FS"])
    T0 = TS.build(1984, 2070, X.exante, 2017, X.lst_dgagri, uaar_years_any=range(1984, 2019),
                  uaar_years_all=range(1995, 2019), expostt_extra=[2019])
    Y = EU.Years(lst_dgagri=X.lst_dgagri, lst_exante=max(X.exante), phase_in=PHASE_IN, fst_exante=T0.fst_exante,
                 sec_exante=T0.sec_exante, lst_expostt=X.lst_expostt, before=dict(T0.before), bas_year=X.base_year,
                 bast_year=X.bast_year, bast_ord=T0.bast, fst_for_biof=min(X.exante))
    msset, yrs = set(X.ms), set(X.exante)
    ref = lambda n: {k: v for k, v in _kv4(_ref(n)[lambda d: d.t.str.isdigit()]).items()   # noqa: E731
                     if k[0] in msset and k[3] in yrs}
    # wVarErr as define_stats_and_supports.gms leaves it for the expert positions (l. 646-650) and the domestic use
    # components (l. 655-663); the trend positions' (l. 327-329, from the statistics' error variance) are not rebuilt
    # here, so wVarErr is compared where a trust level is set (stage 2f's l. 883-886 and the expert positions')
    d1 = X.dgagri1
    W = F.wvarerr(E0, TL0)
    F.domm_wvarerr(W, sup0, [d1, E0, ex["longrun1"]], ms=X.ms, s_colsest=s.s_colsest, s_rowsest=s.s_rowsest,
                   exante=X.exante, dompos=one("dompos"))
    # CAPTRD's stored Step2 and Step3 of the member states as the estimation left them: the reporting's DOMM is the sum
    # of the domestic use positions, the estimation's is kept in DEMD (aggreg_and_report.gms l. 293-294); Step2 and
    # Step3 are stored only where the series has observations or a support (define_eu_supports.gms l. 43-45,
    # captrd.gms l. 1121-1125), the reporting's product groups elsewhere
    def est(name):
        R = ref(name)
        out = {k: v for k, v in R.items() if k[1] not in ("DOMM", "DEMD")}
        out.update({(r, "DOMM", w, t): v for (r, c, w, t), v in R.items() if c == "DEMD"})
        return {k: v for k, v in out.items() if k[:3] in nobs or sup0.get(k)}
    Pp = EU.Pos(step2=est("step2"), step3=est("step3"), dgagri={(r, c, w, int(t)): v for (r, c, w, t), v in dict(scaled[1]).items() if str(t).isdigit() and v},
                dgagri1=dict(d1), support=dict(sup0), support1=dict(sup0), expert=dict(E0), trust=dict(TL0),
                wvar=W, longrun=dict(ex["longrun"]), longrun1=dict(ex["longrun1"]), quts=X.pdata)
    pa, ll, ul = copy.deepcopy(ex["prd_adj"]), copy.deepcopy(ex["low_lim"]), copy.deepcopy(ex["upp_lim"])
    for y in sorted(X.exante):
        EU.eu_supports(Pp, y, S, Y, bast=X.bast, basm=X.basm, bas=X.bas, nobs=nobs, prd_adj=pa, low_lim=ll,
                       upp_lim=ul)
    return Pp, X, s, ref


def _compare(mine, ref, keep, tol=1e-6):
    rows = [(*k, mine.get(k, 0.0), ref.get(k, 0.0)) for k in set(mine) | set(ref) if keep(k)]
    m = pd.DataFrame(rows, columns=K + ["mine", "ref"])
    m["ok"] = (m.mine - m.ref).abs() <= tol * m.ref.abs().clip(lower=1e-6)
    return m


@pytest.mark.slow
@need
def test_eu_supports_equal_captrds(after):
    Pp, X, s, ref = after
    cols, rows = map(set, EU.est_sets(s.s_colsest, s.s_rowsest))
    oagg = ["CERE", "OILS", "INDU", "VEGE", "FRUI", "FORA", "MEAS"]
    keep = lambda k: k[1] in cols and k[2] in rows                                       # noqa: E731
    tlk = {k for k, v in Pp.trust.items() if v}
    for name, mine in (("support", Pp.support), ("TrustLevl", Pp.trust), ("wVarErr", Pp.wvar), ("DGAgri1", Pp.dgagri1)):
        kp = (lambda k: keep(k) and k in tlk) if name == "wVarErr" else keep
        yrs = set(X.exantet)               # 2018 (ExAnteD, a nowcast year): its supports are COCO's, not rebuilt here
        m = _compare({k: v for k, v in mine.items() if k[0] in set(X.ms) and k[3] in yrs},
                     {k: v for k, v in ref(name).items() if k[3] in yrs}, kp)
        later = m.row.isin(["YILD", "HFCS"] + sorted(REQST)) | (m.col.isin(["UVAG", "INHA", "UVAD", "CSSP"])
                                                                 & m.row.isin(oagg))
        # the rows whose EU parts' DGAgri1 differ from CAPTRD's already as scale_DG_AGRI_baseline.gms leaves them
        # (EU014000, which no later stage rewrites: INDM, FEDM, PRCM and DOMM of these rows), from p_data that CAPTRD's
        # stored P_Data no longer holds (test_captrd_scale_dgagri.py)
        from2c = m.row.isin(ROWS_2C)
        fossil = m.col.eq("UVAG") & m.row.isin(["DISL", "GASL"])
        print(name, "2c rows:", int((~m.ok & ~later & from2c).sum()), "fossil UVAG:",
              int((~m.ok & ~later & ~from2c & fossil).sum()))
        bad = m[~m.ok & ~later & ~from2c & ~fossil]
        print(f"{name}: {len(m)}, equal {int(m.ok.sum())}, later stage {int((~m.ok & later).sum())}, other {len(bad)}")
        print(bad.assign(pos=bad.col + "." + bad.row).groupby("pos").size().sort_values(ascending=False).head(25)
              .to_string())
        print(bad.head(20).to_string())
        lim, share = {"support": (420, .95), "TrustLevl": (90, .99), "wVarErr": (330, .98), "DGAgri1": (390, .92)}[name]
        assert int(m.ok.sum()) > share * len(m) and len(bad) <= lim
