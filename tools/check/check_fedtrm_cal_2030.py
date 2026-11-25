"""Check the port of CAPRI's baseline feed calibration (capri_mod/feed/equations: fedtrm_prep.py, fedtrm_prior_pw.py,
fedtrm_mod_pw.py with m_hpdFeed, fedtrm_cal_pw.py's driver; CAPRI's baseline/fedtrm_prep.gms, feed/fedtrm_prior_pw.gms,
feed/fedtrm_mod_pw.gms, feed/fedtrm_cal_pw.gms) against CAPRI's solution for 2030: sim_ini_21730's v_feedInpCoeff
levels of the regional units (baseline/adjust.gms l. 51 sets them to the calibration's).

The inputs are CAPRI's as the calibration reads them: the requirements before the calibration the port's
(capri_mod/feed/equations/def_requirements.py on sim_ini_21730's inputs, as tools/check/check_sim_ini_requirements_2030.py),
the data sim_ini_21730's DATA ("Y", CAPTRD's "TRD", "BAS") of the member state's regions, the crops' technology shares
sim_ini_21730's p_technFact. CAPRI's results are only compared with, never fed in. AL has no calibration file and is
left out (tools/check/check_sim_ini_requirements_2030.py covered_units).

Prints, per member state, each solve (the aggregate, IPOPT's status, the feasibility, the objective), the comparison
of the feed input coefficients (cells, median and largest relative difference, the share within 1e-4 and 1%), the
calibration's corrections from the port's own solution (baseline/fedtrm_fin.gms l. 47-48, fedtrm_fin.py) against
CAPRI's fedtrm_21730<CC>defaulta, and the omitted feed cost row's ratio to its expected value; --show lists the worst
cells; --record writes the DATA cells the chain reads (S4's scoping). Exit status 1 if a member state's share of cells within --rtol is below --share.
The calibration is an NLP solved for each member state (Germany's levels take some minutes): --ms runs a subset.

    python tools/check/check_fedtrm_cal_2030.py [--ms DK000000 DE000000] [--rtol 1e-4] [--share 0.95] [--show 5]
"""
from __future__ import annotations

import argparse
import copy
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "check")]

import check_requirements_2030 as req  # noqa: E402  (sim_ini_21730's folder)
import check_sim_ini_requirements_2030 as sim  # noqa: E402  (def_requirements' inputs)
from capri_mod.data.definitions import capri_pairs, capri_set  # noqa: E402
from capri_mod.feed.equations import def_requirements as dr  # noqa: E402
from capri_mod.feed.equations import fedtrm_cal_pw as cal  # noqa: E402
from capri_mod.feed.equations import fedtrm_fin as fin  # noqa: E402
from capri_mod.feed.equations import fedtrm_prep as fp  # noqa: E402
from capri_mod.feed.equations import fedtrm_prior_pw as pp  # noqa: E402


class Recorder(dict):
    """A DATA dictionary that records the cells read (get, [], in), for --record: which positions of CAPRI's data the
    feed chain reads (the S4 scoping, claude/s4_feed_projection_plan_2026-11-24.md). A plain copy (dict(...)) does not
    record."""

    def __init__(self, data, tag, seen):
        super().__init__(data)
        self.tag, self.seen = tag, seen

    def _note(self, k):
        if isinstance(k, tuple) and len(k) == 3:
            self.seen.add((self.tag, k[1], k[2]))

    def get(self, k, default=None):
        self._note(k)
        return super().get(k, default)

    def __getitem__(self, k):
        self._note(k)
        return super().__getitem__(k)

    def __contains__(self, k):
        self._note(k)
        return super().__contains__(k)


def _regions(ms: str, mr) -> set:
    return {ms} | {b for a, b in mr if a == ms}


def _data(units: set) -> dict:
    """sim_ini_21730's DATA rows of the regions, {(region, column, row, year): value} at "Y", "TRD" and "BAS"."""
    out = {}
    for ch in pd.read_csv(req.SIMINI / "DATA.csv.gz", chunksize=400_000, float_precision="round_trip",
                          dtype={"d0": str, "d1": str, "d2": str, "d3": str}):
        ch = ch[ch.d0.isin(units) & ch.d3.isin(("Y", "TRD", "BAS"))]
        out.update({(r, c, i, y): float(v) for r, c, i, y, v in zip(ch.d0, ch.d1, ch.d2, ch.d3, ch.value)})
    return out


def _technFact_crops(units: set, maact: set) -> dict:
    """sim_ini_21730's p_technFact(region, activity, "LEVL", A) of the activities other than the animals."""
    t = pd.read_csv(req.SIMINI / "p_technFact.csv.gz", dtype={"d0": str, "d1": str, "d2": str, "d3": str})
    t = t[t.d0.isin(units) & (t.d2 == "LEVL") & ~t.d1.isin(maact)]
    return {(r, a, "LEVL", x): float(v) for r, a, x, v in zip(t.d0, t.d1, t.d3, t.value)}


def state(ms: str, st, D: dict, RU_all: set, mr) -> fp.FedtrmState:
    """FedtrmState of the member state on CAPRI's inputs (the module docstring)."""
    regs = _regions(ms, mr)
    DATA = {(r, c, i): v for (r, c, i, y), v in D.items() if y == "Y"}
    TRD = {(r, c, i): v for (r, c, i, y), v in D.items() if y == "TRD"}
    BAS = {(r, c, i): v for (r, c, i, y), v in D.items() if y == "BAS"}
    tf = {k: v for k, v in st.p_technFact.items() if k[0] in regs and k[2] == "LEVL"}
    tf.update(_technFact_crops(regs, set(st.MAACT)))
    srn1, srn2 = set(capri_set("SRNUTS1")), set(capri_set("SRNUTS2"))
    act = {}
    for r in regs:
        for a in capri_set("MPACT"):
            for t in capri_set("A"):
                v = DATA.get((r, a, "LEVL"), 0.0) * tf.get((r, a, "LEVL", t), 0.0)
                if v:
                    act[(r, a, t)] = v
    s = fp.FedtrmState(MS=ms, RU=tuple(sorted(r for r in regs if r in RU_all)),
                       SRNUTS1=tuple(sorted(r for r in regs if r in srn1)),
                       MAP_RR=frozenset((a, b) for a, b in mr if a in regs and b in regs), DATA=copy.deepcopy(DATA),
                       DATA_TRD=TRD, DATA_BAS=BAS, v_actLevl_L=act, p_technFact=tf,
                       p_animReq={k: v for k, v in st.p_animReq.items() if k[0] in regs},
                       p_animProdDays={k: v for k, v in st.p_animProdDays.items() if k[0] in regs},
                       p_minFeedShare={k: v for k, v in st.p_minFeedShare.items() if k[0] in regs},
                       p_maxFeedShare={k: v for k, v in st.p_maxFeedShare.items() if k[0] in regs})
    s.SRNUTS2 = tuple(sorted(r for r in regs if r in srn2))
    s.p_NutContFeed = {(k[0], k[1], k[2], k[3], k[4], k[5].upper()): v for k, v in st.p_NutContFeed.items()
                       if k[0] in regs}
    s.p_exoDemand = {(r, "DEMD", o): (TRD.get((r, "INDM", o), 0.0) or DATA.get((r, "INDM", o), 0.0))
                     for r in regs for o in capri_set("FODDO")
                     if TRD.get((r, "INDM", o), 0.0) or DATA.get((r, "INDM", o), 0.0)}
    return s


def compare(s: fp.FedtrmState, ref: pd.DataFrame) -> pd.DataFrame:
    """The port's feed input coefficients of the regional units against sim_ini_21730's."""
    ref = ref[ref.d0.isin(set(s.RU))]
    fic = s.v_feedInpCoeff.L
    rows = [(r, a, t, f, lv, fic.get((r, a, t, f), 0.0)) for r, a, t, f, lv in zip(ref.d0, ref.d1, ref.d2, ref.d3, ref.level)
            if f in set(s.FEED)]
    tt = pd.DataFrame(rows, columns=["region", "activity", "A", "feed", "capri", "port"])
    tt["rel"] = (tt.port - tt.capri) / tt.capri.abs().clip(lower=1e-9)
    refk = set(zip(tt.region, tt.activity, tt.A, tt.feed))
    extra = [(k, v) for k, v in fic.items() if k[0] in set(s.RU) and k[3] in set(s.FEED) and v > 1e-6
             and k not in refk]
    tt.attrs["extra"] = extra
    return tt


def feed_cost_ratio(s: fp.FedtrmState, D: dict) -> tuple:
    """CST_'s feed cost of the port's solution, SUM(FEED, v_feedInpCoeff x UVAG) / 1000 (feed/fedtrm_mod_pw.gms
    l. 104-108; UVAG sim_ini_21730's "Y"), over CAPRI's expected value p_aprDistFeedCost "Mean" (fedtrm_cal_pw.gms
    l. 360-372, on sim_ini_21730's "Y"): the smallest and largest ratio over the units' animals. CAPRI bounds the cost
    within 0.001 to 1000 times the expected (l. 378-381); CST_ is left out of the port, so a range well inside these
    bounds measures the row as not binding."""
    # CAPRI's expected feed cost, p_aprDistFeedCost "Mean" (fedtrm_cal_pw.gms l. 360-372): the higher of the member
    # state's feed cost per head scaled by the unit's revenue over the member state's, and a third of the unit's revenue
    # and premium; the member state's feed cost where the unit has no revenue. FEED and TOOU as baseline/fedtrm_prep.gms
    # l. 120 and 122 compute them: the year's coefficients at the year's unit values. (Until 25 November 2026 only the
    # second branch was used, which overstated the ratio where an animal's revenue is small: Denmark's largest, 4,589.)
    pio = capri_pairs("PACT_TO_IO")
    outs = {}
    for a, o in capri_pairs("PACT_TO_O"):
        outs.setdefault(a, []).append(o)
    feeds = set(s.FEED)

    def val(r, a, items):
        return sum(D.get((r, a, i, "Y"), 0.0) * D.get((r, "UVAG", i, "Y"), 0.0) for i in items) * 0.001

    ms = s.MS
    lo, hi = None, None
    for r in s.RU:
        for a in s.MAACT:
            feed_ms = val(ms, a, [i for (aa, i) in pio if aa == a and i in feeds])
            toou_ms, toou_r = val(ms, a, outs.get(a, ())), val(r, a, outs.get(a, ()))
            for t in s.A:
                if not s.v_actLevl_L.get((r, a, t), 0.0):
                    continue
                cost = sum(s.v_feedInpCoeff.l((r, a, t, f)) * D.get((r, "UVAG", f, "Y"), 0.0) for f in s.FEED) / 1000.
                if toou_r > 0 and toou_ms:
                    exp = max(feed_ms * toou_r / toou_ms, (toou_r + D.get((r, a, "PRME", "Y"), 0.0)) / 3)
                else:
                    exp = feed_ms
                if exp > 0 and cost > 0:
                    x = cost / exp
                    lo, hi = (x if lo is None else min(lo, x)), (x if hi is None else max(hi, x))
    return lo, hi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", nargs="*", default=None)
    ap.add_argument("--rtol", type=float, default=1e-4)
    ap.add_argument("--share", type=float, default=0.95)
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--raw", type=Path, default=None)
    ap.add_argument("--record", type=Path, default=None,
                    help="write the (position, column, row) cells of DATA the chain reads to this CSV")
    o = ap.parse_args()
    st, d, extra, fedtrm, fed_where, _ = sim.def_requirements_inputs(o.raw)
    seen: set = set()
    if o.record:
        st.DATA = Recorder(st.DATA, "Y", seen)
        st.DATA_BAS = Recorder(st.DATA_BAS, "BAS", seen)
        d.DATA_BAS = st.DATA_BAS
        d.DATA_TRD = Recorder(d.DATA_TRD, "TRD", seen)
    dr.def_requirements(st, d)
    mr = capri_pairs("MAP_RR")
    mss = o.ms or sorted({st.R_RAGG_MS.get(r, r) for r in fed_where})
    regs = {ms: _regions(ms, mr) for ms in mss}
    D = _data(set().union(*regs.values()))
    ref = pd.read_csv(req.SIMINI / "v_feedInpCoeff.csv.gz", dtype={"d0": str, "d1": str, "d2": str, "d3": str})
    pd.set_option("display.width", 200)
    bad = []
    for ms in mss:
        t0 = time.time()
        Dm = {k: v for k, v in D.items() if k[0] in regs[ms]}
        s = state(ms, st, Dm, set(d.RU), mr)
        if o.record:
            s.DATA = Recorder(s.DATA, "Y", seen)
            s.DATA_TRD = Recorder(s.DATA_TRD, "TRD", seen)
            s.DATA_BAS = Recorder(s.DATA_BAS, "BAS", seen)
        fp.fedtrm_prep(s)
        pp.fedtrm_prior_pw(s)
        log = []
        try:
            cal.fedtrm_cal_pw(s, log)
        except RuntimeError as e:
            print(f"{ms}: {e}")
            bad.append(ms)
            continue
        for ragg, res in log:
            print(f"  {ragg:10s} solve {res['solves']}: {res['status']}, feasible {res['feasible']}, objective "
                  f"{res['objective']:.10g}, {res['variables']} variables, {res['rows']} rows, {res['iterations']} "
                  f"iterations")
        tt = compare(s, ref)
        within = (tt.rel.abs() < o.rtol).mean() if len(tt) else 1.0
        print(f"{ms}: {len(s.RU)} units, {time.time() - t0:.0f} s; cells {len(tt)}, median |rel| "
              f"{tt.rel.abs().median():.2e}, max {tt.rel.abs().max():.2e}, within {o.rtol:g} {within:.3f}, within 1% "
              f"{(tt.rel.abs() < 0.01).mean():.3f}; the port's coefficients CAPRI has not: {len(tt.attrs['extra'])}")
        corr = fin.p_animReqCorrFac(s.RU, s.MAACT, s.p_animReq, s.v_animReq.L)
        ref_c = {k: v for k, v in fedtrm.items() if k[0] in set(s.RU) and k[1] in set(s.MAACT)}
        rel = sorted((abs(corr.get(k, 0.0) - v) / max(abs(v), 1e-12), k) for k, v in ref_c.items())
        if rel:
            print(f"  the corrections p_animReqCorrFac against fedtrm_21730{ms[:2]}defaulta: cells {len(rel)}, median "
                  f"{rel[len(rel) // 2][0]:.2e}, max {rel[-1][0]:.2e} {rel[-1][1]}, within 1e-4 "
                  f"{sum(x < 1e-4 for x, _ in rel) / len(rel):.3f}")
        lo, hi = feed_cost_ratio(s, Dm)
        print(f"  the feed cost over (TOOU + PRME) / 3, smallest and largest: {lo} {hi} (CST_'s bounds 0.001, 1000)")
        if o.show:
            print(tt.reindex(tt.rel.abs().sort_values(ascending=False).index).head(o.show).to_string(index=False))
        if within < o.share:
            bad.append(ms)
    print(f"member states below {o.share:g} of cells within {o.rtol:g}: {len(bad)} ({', '.join(bad)})")
    if o.record:
        pd.DataFrame(sorted(seen), columns=["position", "column", "row"]).to_csv(o.record, index=False)
        print(f"wrote {o.record}: {len(seen)} (position, column, row) cells read")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
