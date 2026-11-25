#!/usr/bin/env python3
"""Check CAPRI's baseline feed chain run on the port's own year data, against CAPRI's 2030 reference start
(sim_ini_21730): the S4 plan's closing check (claude/s4_feed_projection_plan_2026-11-24.md section 5) and the hand-over
plan's (claude/handover_plan_2026-11-25.md section 5).

The chain is capri_mod/feed/chain.py's feed_chain, all ported, for one member state, on CAPRI's inputs
(tools/lib/feed_chain_inputs.py: CAPREG's base year, technology shares, housing days and corrections, CAPRI's
trends_1730):
1. the year's data (load_base_data_and_trends.gms, create_sim_ini_gdx.gms l. 311-369);
2. the baseline calibration run: the requirement call at "Y", def_requirements.gms, the baseline feed calibration
   (fedtrm_prep, fedtrm_prior_pw, fedtrm_cal_pw: m_hpdFeed solved with IPOPT; fedtrm_fin's corrections);
3. the simulation's start: def_requirements.gms again, baseline/adjust.gms with the calibration's corrections and feed
   input coefficients, the shares and the days (create_sim_ini_gdx.gms l. 421-461).

Compared with sim_ini_21730 in the member state's regional units: the feed input coefficients v_feedInpCoeff (the
calibration's, which adjust.gms sets as the start), within --rtol and within 1%; and the simulation's start:
p_animReq, p_animExcrProtCorrFact at "Y", p_minFeedShare, p_maxFeedShare, p_animProdDays and DATA's "DAYS" at "Y" (the
member state too for the days), as tools/check/check_sim_ini_requirements_2030.py compares them. CAPRI's results serve
as the check only; none is an input. --others simini reads the other member states' "BAS" from sim_ini_21730 (as the
check did before the chain's driver); --others none leaves them out.

    python3 tools/check/check_feed_chain_2030.py --ms DK [--rtol 1e-4] [--show 20] [--raw DIR] [--others none]
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "check")]

import check_fedtrm_cal_2030 as fc  # noqa: E402  (the coefficients' comparison)
import check_manure_output_2030 as man  # noqa: E402  (CAPRI's animal activities)
import check_requirements_2030 as req  # noqa: E402  (sim_ini's folder, the comparison of a symbol)
import check_sim_ini_requirements_2030 as sim  # noqa: E402  (sim_ini's symbols)
import check_year_data_2030 as yd  # noqa: E402  (sim_ini's DATA)
from capri_mod.feed import chain  # noqa: E402
from capri_mod.projection.equations import load_base_data_and_trends as ly  # noqa: E402
from feed_chain_inputs import chain_inputs  # noqa: E402


def start_stats(res: chain.ChainResult) -> dict:
    """The simulation's start against sim_ini_21730: {(symbol, item): [(rel, key, port, CAPRI)]}."""
    st, a, si = res.st, res.a, res.si
    ru, ms = set(res.d.RU), set(si.MS)
    animals = set(man.ANIMALS)
    stats = defaultdict(list)
    req.SKIP.clear()

    def keep(k, units):
        return k[0] in units and k[1] in animals

    ref = {k: v for k, v in sim._sym("p_animReq", req.SIMINI, 4).items() if keep(k, ru)}
    req._compare("p_animReq", {k: v for k, v in st.p_animReq.items() if keep(k, ru)}, ref, stats)
    ref = {k[:3]: v for k, v in sim._sym("p_animExcrProtCorrFact", req.SIMINI, 4).items() if k[3] == "Y" and keep(k, ru)}
    req._compare("p_animExcrProtCorrFact", {k: v for k, v in a.p_animExcrProtCorrFact_Y.items() if keep(k, ru)}, ref,
                 stats, None)
    for name in ("p_minFeedShare", "p_maxFeedShare"):
        ref = {k: v for k, v in sim._sym(name, req.SIMINI, 4).items() if keep(k, ru)}
        req._compare(name, {k: v for k, v in getattr(st, name).items() if keep(k, ru)}, ref, stats)
    ref = {k: v for k, v in sim._sym("p_animProdDays", req.SIMINI, 3).items() if keep(k, ru | ms)}
    req._compare("p_animProdDays", {k: v for k, v in st.p_animProdDays.items() if keep(k, ru | ms)}, ref, stats, None)
    Ds = yd.read_simini(ru | ms, ("Y",))
    ref = {(r, c): v for (t, c, w), dd in Ds.c.items() if w == "DAYS" for r, v in dd.items()
           if keep((r, c), ru | ms) and Ds.get(r, c, "LEVL", "Y")}
    req._compare("DATA DAYS Y", {k: v for k, v in si.DATA_DAYS_Y.items() if keep(k, ru | ms)}, ref, stats, None)
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", required=True, help="the member state's two letters (DK, DE, ...)")
    ap.add_argument("--rtol", type=float, default=1e-4)
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--raw", type=Path, default=None)
    ap.add_argument("--others", choices=("simini", "none"), default="none",
                    help="the other member states' BAS: sim_ini_21730's, or none")
    a = ap.parse_args(argv)
    t0 = time.time()
    S = ly.YearSets.from_codes()
    _, mine = chain.regions_of(a.ms, S)
    others = yd.read_simini((mine | set(S.MSALL)) - mine, ("BAS",)) if a.others == "simini" else ly.Data()
    ci = chain_inputs(a.ms, a.raw, others)
    print(f"{a.ms}: the inputs, {time.time() - t0:.0f} s")
    res = chain.feed_chain(ci)
    for ragg, r in res.log:
        print(f"  {ragg:10s} solve {r['solves']}: {r['status']}, objective {r['objective']:.10g}, "
              f"{r['iterations']} iterations")
    s = res.cal
    ref = pd.read_csv(req.SIMINI / "v_feedInpCoeff.csv.gz", dtype={"d0": str, "d1": str, "d2": str, "d3": str})
    tt = fc.compare(s, ref)
    within = (tt.rel.abs() < a.rtol).mean() if len(tt) else 1.0
    print(f"{a.ms}: {len(s.RU)} units, {time.time() - t0:.0f} s; feed input coefficients {len(tt)}, median |rel| "
          f"{tt.rel.abs().median():.2e}, max {tt.rel.abs().max():.2e}, within {a.rtol:g} {within:.3f}, within 1% "
          f"{(tt.rel.abs() < 0.01).mean():.3f}; the port's coefficients CAPRI has not: {len(tt.attrs['extra'])}")
    if a.show:
        print(tt.reindex(tt.rel.abs().sort_values(ascending=False).index).head(a.show).to_string(index=False))
    starts = {k: v for k, v in res.a.v_feedInpCoeff_L.items() if k[0] in set(s.RU)}
    same = all(starts.get(k, 0.0) == v for k, v in s.v_feedInpCoeff.L.items() if k[0] in set(s.RU))
    print(f"the simulation's start: feed input coefficients the calibration's: {same}")
    for (name, item), xs in sorted(start_stats(res).items()):
        xs.sort(key=lambda x: -x[0])
        n_bad = sum(1 for x in xs if x[0] > a.rtol)
        within1 = sum(1 for x in xs if x[0] <= 0.01) / len(xs)
        print(f"  {name:22s} {str(item):22s} cells {len(xs):6d}  above rtol {n_bad:6d}  within 1% {within1:.3f}  "
              f"max rel {xs[0][0]:.2e} {xs[0][1]}")
        for rel, k, m, v in xs[:a.show]:
            if rel > a.rtol:
                print(f"      {k} port {m:.10g} CAPRI {v:.10g} rel {rel:.2e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
