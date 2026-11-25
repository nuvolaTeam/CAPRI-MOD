#!/usr/bin/env python3
"""Check CAPRI's baseline feed chain run on the port's own year data, against CAPRI's 2030 reference start
(sim_ini_21730): the S4 plan's closing check (claude/s4_feed_projection_plan_2026-11-24.md section 5).

The chain, all ported, for one member state:
1. the year's data (capri_mod/projection/equations/load_base_data_and_trends.py): the base year rebuilt from CAPREG's
   results (capri_sources/reference/capreg_base/17/<CC>.csv.gz, read as the CAPTRD port reads it), CAPRI's trends
   (trends_1730), then create_sim_ini_gdx.gms l. 311-369 (create_sim_ini_gdx_data.py);
2. the requirement call at "Y" (feed/req_or_man_fnc.gms, req_or_man_fnc_req.py) on that data, with CAPREG's 2017
   technology shares and housing days (its results, capri_sources/dat_parquet/capreg_tseries/<CC>_17: p_technFact,
   p_rcEmissions) and CAPREG's corrections (reqrel_17<CC>, the raw dataset);
3. def_requirements.gms (def_requirements.py);
4. the baseline feed calibration (fedtrm_prep, fedtrm_prior_pw, fedtrm_cal_pw: m_hpdFeed solved with IPOPT).

Compared with sim_ini_21730: the feed input coefficients v_feedInpCoeff of the regional units, and the share within
--rtol and within 1%. CAPRI's results serve as the check only; none is an input. The other member states' base years,
read for FROM_CAPTRD's domain, are sim_ini_21730's "BAS" (as tools/check/check_year_data_2030.py --bas capreg).

    python3 tools/check/check_feed_chain_2030.py --ms DK [--rtol 1e-4] [--show 20] [--raw DIR]

Results (25 November 2026), the feed input coefficients against sim_ini_21730's:
- Denmark: 146 coefficients, median |rel| 2.3e-9, max 1.3e-5, all within 1e-4;
- Germany (34 units): 4,391 coefficients, median 7.8e-8, max 1.3e-3 (SHGF's grass in DEA5), 99.3% within 1e-4, all
  within 1%. On sim_ini's own "Y" (check_fedtrm_cal_2030.py --ms DE000000) the same estimation gives median 1.2e-7, max
  3.0e-3, 97.7% within 1e-4: differences of that size are there without the port of "Y" too, so they come from the
  estimation (solved with IPOPT; KNOWN_ISSUES K206 for the countries below 95%), not from the year's data.
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "check")]

import check_fedtrm_cal_2030 as fc  # noqa: E402  (the calibration's state and comparison)
import check_manure_output_2030 as man  # noqa: E402  (the sets and the literal tables)
import check_requirements_2030 as req  # noqa: E402  (the columns the requirement call reads)
import check_sim_ini_requirements_2030 as sim  # noqa: E402  (CAPREG's corrections from the raw set)
import check_year_data_2030 as yd  # noqa: E402  (the readers of sim_ini, the trends and CAPREG's base)
from capri_mod.data.definitions import capri_pairs  # noqa: E402
from capri_mod.feed.equations import def_requirements as dr  # noqa: E402
from capri_mod.feed.equations import fedtrm_cal_pw as cal  # noqa: E402
from capri_mod.feed.equations import fedtrm_prep as fp  # noqa: E402
from capri_mod.feed.equations import fedtrm_prior_pw as pp  # noqa: E402
from capri_mod.feed.equations import req_or_man_fnc_req as rq  # noqa: E402
from capri_mod.projection.equations import create_sim_ini_gdx_data as csd  # noqa: E402
from capri_mod.projection.equations import load_base_data_and_trends as ly  # noqa: E402
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)

CAPREG_RES = SOURCES / "dat_parquet" / "capreg_tseries"


def year_data(ms: str):
    """The member state's year data (step 1): (D, S, p_exoDemand)."""
    S = ly.YearSets.from_codes()
    mine = {r for r in S.RS if r.startswith(ms)}
    loaded = mine | set(S.MSALL)
    S = dataclasses.replace(S, RS=S.RS & loaded, RU=S.RU & loaded, MS=S.MS & loaded)
    own = ly.Data()
    Sm = dataclasses.replace(S, RS=S.RS & mine, RU=S.RU & mine, MS=S.MS & mine)
    ly.base_year_data(own, yd.read_capreg(ms, mine), Sm)
    D = yd.read_simini(loaded - mine, ("BAS",))
    for (t, c, w), d in own.c.items():
        for r, v in d.items():
            D.set(r, c, w, t, v)
    ly.year_data(D, yd.read_trends(loaded), S)
    exo = csd.create_sim_ini_gdx_data(D, S)
    return D, S, mine, exo


def capreg_results(ms: str, name: str, regions: set) -> dict:
    """A symbol of CAPREG's 2017 results for the member state's regions, {(d1, ..., dn): value}."""
    t = pd.read_parquet(CAPREG_RES / f"{ms[:2]}_17" / f"{name}.parquet")
    t = t[t.d1.isin(regions)]
    keys = [c for c in t.columns if c.startswith("d")]
    return {tuple(row[:-1]): float(row[-1]) for row in t[keys + ["value"]].itertuples(index=False, name=None)}


def req_state(D: ly.Data, ms: str, regions: set) -> tuple:
    """The requirement call's state at "Y" from the year's data (as check_requirements_2030.state_2030 builds it from
    sim_ini, the year's data in place of sim_ini's): (state, DATA at "TRD" of the levels and gross production)."""
    aact, mcact = tuple(man._set("AACT")), tuple(man._set("MCACT"))
    cols = set(aact) | set(req.OTHER_COLS) | set(mcact)
    data, bas, trd, trd_days = {}, {}, {}, {}
    MS = frozenset(man._set("MS"))
    for (t, c, w), d in D.c.items():
        if c not in cols:
            continue
        for r, v in d.items():
            if r not in regions:
                continue
            if t == "Y":
                data[(r, c, w)] = v
            elif t == "BAS":
                bas[(r, c, w)] = v
            elif t == "TRD":
                if w == "DAYS" and r in MS:
                    trd_days[(r, c, w)] = v
                if w == "LEVL" or c == "GROF":
                    trd[(r, c, w)] = v
    data.update(trd_days)
    tf = {k: v for k, v in capreg_results(ms, "p_technFact", regions).items() if k[1] in aact}
    p_rc = capreg_results(ms, "p_rcEmissions", regions)
    rr = capri_pairs("R_RAGG")
    r_ms = {a: b for a, b in rr if b in MS}
    feed_q = {(m, f): v for (m, c, f), v in bas.items() if c == "GROF" and m in MS and f in rq.FEED}
    P = man.params()
    st = rq.ReqState(DATA=data, RS=tuple(r for r in man._set("RS") if r in regions), MS=MS, R_RAGG_MS=r_ms,
                     GRSACT=tuple(man._set("GRSACT")), RUMI=tuple(man._set("RUMI")), AACT=aact,
                     p_LUUnits=P["p_LUUnits"], p_technFact=tf, p_rcEmissions=p_rc, p_feedQuant=feed_q,
                     p_carcassShare=P["p_carcassShare"], p_startWgt=P["p_startWgt"], p_reqfcnlim=P["p_reqfcnlim"],
                     p_coeffEnergyForGrowth=P["p_coeffEnergyForGrowth"],
                     p_convFactEnergyUnitsToEnne=P["p_convFactEnergyUnitsToEnne"],
                     p_NutContFeedRef=P["p_NutContFeedRef"], p_pigsReqLowWgt=P["p_pigsReqLowWgt"],
                     p_pigsReqHighWgt=P["p_pigsReqHighWgt"], DATA_BAS=bas, MAACT=tuple(man._set("MAACT")),
                     MCACT=mcact, FEED_TO_O=frozenset(capri_pairs("FEED_TO_O")),
                     PACT_TO_O=frozenset(capri_pairs("PACT_TO_O")))
    return st, trd


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", required=True, help="the member state's two letters (DK, DE, ...)")
    ap.add_argument("--rtol", type=float, default=1e-4)
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--raw", type=Path, default=None)
    a = ap.parse_args(argv)
    t0 = time.time()
    D, S, mine, exo = year_data(a.ms)
    print(f"{a.ms}: the year's data, {len(mine)} units, {time.time() - t0:.0f} s")
    ms = next(r for r in mine if r in S.MS)
    st, trd = req_state(D, ms, mine)
    capreg, _ = sim._corr(sim._raw(a.raw), sim.REQREL)
    pt = capri_pairs("PACT_TO_Y")
    d = dr.DefReqInputs(RU=tuple(r for r in man._set("RU") if r in mine), MPACT=tuple(man._set("MPACT")),
                        PACT_TO_Y=frozenset(pt), DATA_BAS=st.DATA_BAS,
                        p_animReqCorrFac={k: v for k, v in capreg.items() if k[0] in mine}, SIMY=2030, BAS=2017,
                        FODDO=tuple(man._set("FODDO")), DATA_TRD=trd)
    dr.def_requirements(st, d)
    print(f"  the requirements: {len(st.p_animReq)} cells, {time.time() - t0:.0f} s")
    Dm = {(r, c, w, t): v for (t, c, w), dd in D.c.items() if t in ("Y", "TRD", "BAS") for r, v in dd.items()
          if r in mine}
    mr = capri_pairs("MAP_RR")
    # the activities' technology shares: CAPREG's results, in place of the calibration check's sim_ini reader
    tf = capreg_results(ms, "p_technFact", mine)
    fc._technFact_crops = lambda units, maact: {k: v for k, v in tf.items() if k[0] in units and k[2] == "LEVL"
                                                and k[1] not in maact}
    s = fc.state(ms, st, Dm, set(d.RU), mr)
    s.p_exoDemand = {k: v for k, v in exo.items() if k[0] in mine}
    fp.fedtrm_prep(s)
    pp.fedtrm_prior_pw(s)
    log = []
    cal.fedtrm_cal_pw(s, log)
    for ragg, res in log:
        print(f"  {ragg:10s} solve {res['solves']}: {res['status']}, objective {res['objective']:.10g}, "
              f"{res['iterations']} iterations")
    ref = pd.read_csv(req.SIMINI / "v_feedInpCoeff.csv.gz", dtype={"d0": str, "d1": str, "d2": str, "d3": str})
    tt = fc.compare(s, ref)
    within = (tt.rel.abs() < a.rtol).mean() if len(tt) else 1.0
    print(f"{a.ms}: {len(s.RU)} units, {time.time() - t0:.0f} s; feed input coefficients {len(tt)}, median |rel| "
          f"{tt.rel.abs().median():.2e}, max {tt.rel.abs().max():.2e}, within {a.rtol:g} {within:.3f}, within 1% "
          f"{(tt.rel.abs() < 0.01).mean():.3f}; the port's coefficients CAPRI has not: {len(tt.attrs['extra'])}")
    if a.show:
        print(tt.reindex(tt.rel.abs().sort_values(ascending=False).index).head(a.show).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
