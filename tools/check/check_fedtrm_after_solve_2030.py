"""Check the port of the statements after CAPRI's feed calibration solve and of its corrections
(capri_mod/feed/equations/fedtrm_cal_pw.py after_solve: feed/fedtrm_cal_pw.gms l. 762-812; fedtrm_fin.py:
baseline/fedtrm_fin.gms l. 47-52) against CAPRI's baseline calibration results for 2030 (fedtrm_21730<CC>defaulta,
p_animReqCorrFac, in the raw dataset nuvolaTeam/capri-mod-raw) and sim_ini_21730.

The calibration's solution is taken from CAPRI (its feed input coefficients, sim_ini_21730's v_feedInpCoeff levels,
which baseline/adjust.gms l. 51 sets to the calibration's, mefed_<...>.gdx); the requirements before the calibration are
the port's (capri_mod/feed/equations/def_requirements.py on sim_ini_21730's inputs, as
tools/check/check_sim_ini_requirements_2030.py); the feeds' contents sim_ini_21730's DATA(MS, requirement, feed, "Y").
A coefficient that is not 0 has a maximum share (CAPRI fixes the others at 0, fedtrm_cal_pw.gms l. 252, 431, 501), so
the rows' $ p_maxFeedShare is taken as the coefficient's own. Compared: the corrections in CAPRI's regional units, every
requirement and feed row; the calibrated energy and protein requirements and the manure's protein factor with
sim_ini_21730's. The rows of the member states and NUTS 1 regions with regions are left out (the port computes the
regional units' rows); AL has no calibration file.

Prints, per symbol and item, the cells compared and the largest relative difference; --show lists the worst cells.
Exit status 1 if a cell differs by more than --rtol.

    python tools/check/check_fedtrm_after_solve_2030.py [--rtol 1e-6] [--show 5] [--raw DIR]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "check")]

import check_manure_output_2030 as man  # noqa: E402  (the sets)
import check_requirements_2030 as req  # noqa: E402  (the comparison)
import check_sim_ini_requirements_2030 as sim  # noqa: E402  (def_requirements' inputs)
from capri_mod.feed.equations import def_requirements as dr  # noqa: E402
from capri_mod.feed.equations import fedtrm_cal_pw as cal  # noqa: E402
from capri_mod.feed.equations import fedtrm_fin as fin  # noqa: E402
from capri_mod.feed.equations import req_or_man_fnc_req as rq  # noqa: E402


def _contents(ms: set) -> dict:
    """sim_ini_21730's DATA(MS, requirement, feed, "Y") of the requirements the statements read."""
    items = set(cal.REQMSE) | set(cal.REQMSN)
    out = {}
    for ch in pd.read_csv(req.SIMINI / "DATA.csv.gz", chunksize=400_000, float_precision="round_trip",
                          dtype={"d0": str, "d1": str, "d2": str, "d3": str}):
        ch = ch[ch.d0.isin(ms) & ch.d1.isin(items) & ch.d2.isin(rq.FEED) & (ch.d3 == "Y")]
        out.update({(m, i, f): float(v) for m, i, f, v in zip(ch.d0, ch.d1, ch.d2, ch.value)})
    return out


def run(raw: Path | None = None):
    st, d, extra, fedtrm, fed_where, _ = sim.def_requirements_inputs(raw)
    dr.def_requirements(st, d)
    ms = tuple(man._set("MS"))
    covered, left = sim.covered_units(st, ms, d.RU, fed_where)
    runr = tuple(r for r in d.RU if r in covered)
    fic = {k: v for k, v in sim._sym("v_feedInpCoeff", req.SIMINI, 4, "level").items() if k[0] in set(runr)}
    c = cal.CalState(RUNR=runr, MAACT=st.MAACT, p_animReq=st.p_animReq, v_feedInpCoeff_L=fic,
                     p_animProdDays=st.p_animProdDays, p_maxFeedShare={k: 1.0 for k, v in fic.items() if v},
                     DATA_content=_contents(set(ms)), R_RAGG_MS=st.R_RAGG_MS,
                     DATA_LEVL={(r, a): v for (r, a, i), v in st.DATA.items() if i == "LEVL"})
    cal.v_animReq_start(c)
    cal.after_solve(c)
    corr = fin.p_animReqCorrFac(runr, st.MAACT, c.p_animReq, c.v_animReq_L)
    prot = dict(d.p_animExcrProtCorrFact_Y)
    fin.p_animExcrProtCorrFact_calibrated(runr, st.MAACT, st.p_technFact, prot, corr)
    return st, c, corr, prot, fedtrm, set(runr), left


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtol", type=float, default=1e-6)
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--raw", type=Path, default=None)
    o = ap.parse_args()
    st, c, corr, prot, fedtrm, runr, left = run(o.raw)
    animals = set(man.ANIMALS)
    stats = defaultdict(list)

    def keep(k):
        return k[0] in runr and k[1] in animals

    req.SKIP.clear()
    req._compare("p_animReqCorrFac", {k: v for k, v in corr.items() if keep(k)},
                 {k: v for k, v in fedtrm.items() if keep(k)}, stats)
    ref = {k: v for k, v in sim._sym("p_animReq", req.SIMINI, 4).items() if keep(k) and k[3] in cal.REQMSE}
    req._compare("p_animReq calibrated", {k: v for k, v in c.p_animReq.items() if keep(k) and k[3] in cal.REQMSE},
                 ref, stats)
    ref = {k[:3]: v for k, v in sim._sym("p_animExcrProtCorrFact", req.SIMINI, 4).items() if k[3] == "Y" and keep(k)}
    req._compare("p_animExcrProtCorrFact", {k: v for k, v in prot.items() if keep(k)}, ref, stats, None)
    print(f"regional units compared: {len(runr)}; left out (no calibration file): {len(left)} ({', '.join(left)})")
    bad = 0
    for (sym, item), xs in sorted(stats.items()):
        xs.sort(key=lambda x: -x[0])
        n_bad = sum(1 for x in xs if x[0] > o.rtol)
        bad += n_bad
        print(f"{sym:22s} {str(item):22s} cells {len(xs):6d}  above rtol {n_bad:6d}  max rel {xs[0][0]:.2e} {xs[0][1]}")
        for rel, k, m, v in xs[:o.show]:
            if rel > o.rtol:
                print(f"      {k} port {m:.10g} CAPRI {v:.10g} rel {rel:.2e}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
