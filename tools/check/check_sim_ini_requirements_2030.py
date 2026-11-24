"""Check the port of CAPRI's requirements at a simulation's start (capri_mod/feed/equations/create_sim_ini_gdx.py:
capmod/def_requirements.gms, baseline/adjust.gms and capmod/create_sim_ini_gdx.gms l. 421-461) against CAPRI's 2030
Green Deal reference run's start, sim_ini_21730.

The port runs on sim_ini_21730's inputs, as tools/check/check_requirements_2030.py's requirement call (DATA at "Y",
"BAS" and "TRD", p_technFact, MITERRA's housing days), with CAPREG's 2017 corrections (results/capreg/reqrel_17<CC>,
p_animReqCorrFac1: capmod/load_feed.gms l. 56-60) and the baseline calibration's corrections (results/baseline/
fedtrm_21730<CC>defaulta, p_animReqCorrFac: load_feed.gms l. 71-76) from the raw dataset nuvolaTeam/capri-mod-raw, and
the baseline's feed input coefficients (sim_ini_21730's v_feedInpCoeff levels, in place of CAPRI's mefed_<...>.gdx,
adjust.gms l. 36-43). Compared with sim_ini_21730: p_animReq, p_animExcrProtCorrFact at "Y", p_minFeedShare,
p_maxFeedShare, p_animProdDays and DATA's "DAYS" at "Y", in CAPRI's regional units (the member states too for the
days); the rows of the member states and NUTS 1 regions with regions are aggregates in CAPRI's file (supply/aggreg.gms)
and not compared. CAPRI's results serve as the check only: the baseline calibration's corrections are an input here
until the calibration is ported (claude/feed_calibration_port_plan_2026-11-24.md, S3). Countries without a calibration
file (AL) are left out and named.

Prints, per symbol and item, the cells compared and the largest relative difference; --show lists the worst cells.
Exit status 1 if a cell differs by more than --rtol.

    python tools/check/check_sim_ini_requirements_2030.py [--rtol 1e-6] [--show 5] [--raw DIR]
--raw: a local copy of the raw dataset's capri/ folder (else the files are downloaded from Hugging Face).
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "check")]

import check_manure_output_2030 as man  # noqa: E402  (the sets and the literal tables)
import check_requirements_2030 as req  # noqa: E402  (the requirement call's inputs)
from capri_mod.feed.equations import adjust as adj  # noqa: E402
from capri_mod.feed.equations import create_sim_ini_gdx as csi  # noqa: E402
from capri_mod.feed.equations import def_requirements as dr  # noqa: E402
from capri_mod.feed.equations import req_or_man_fnc_req as rq  # noqa: E402

REPO = "nuvolaTeam/capri-mod-raw"
REQREL = "results/capreg/reqrel_17*/p_animReqCorrFac1.parquet"
FEDTRM = "results/baseline/fedtrm_21730*defaulta/p_animReqCorrFac.parquet"


def _raw(raw: Path | None) -> Path:
    """The raw dataset's capri/ folder: the local copy, else a download of the two symbols' files."""
    if raw is not None:
        return raw
    from huggingface_hub import snapshot_download
    p = snapshot_download(REPO, repo_type="dataset", allow_patterns=[f"capri/{REQREL}", f"capri/{FEDTRM}"])
    return Path(p) / "capri"


def _corr(raw: Path, pattern: str) -> tuple[dict, dict]:
    """{(region, animal, A, item): value} of the symbol in every file matching pattern, and {region: file}."""
    out, where = {}, {}
    for f in sorted(raw.glob(pattern)):
        t = pd.read_parquet(f)
        for r, a, tt, i, v in zip(t.d1, t.d2, t.d3, t.d4, t.value):
            out[(r, a, tt, i)] = float(v)
            where.setdefault(r, f.parent.name)
    return out, where


def _sym(name: str, folder: Path, dims: int, value: str = "value") -> dict:
    t = req._csv(folder / f"{name}.csv.gz")
    keys = [f"d{k}" for k in range(dims)]
    return {tuple(row[:-1]): float(row[-1]) for row in t[keys + [value]].itertuples(index=False, name=None)}


def run(raw: Path | None = None):
    """The port on sim_ini_21730's inputs. Returns (st, d, a, s, covered regions, regions left out)."""
    extra: dict = {}
    st = req.state_2030(extra)
    ru = tuple(man._set("RU"))
    rawp = _raw(raw)
    capreg, _ = _corr(rawp, REQREL)
    fedtrm, fed_where = _corr(rawp, FEDTRM)
    pt = pd.read_csv(man.SETS / "PACT_TO_Y.csv", dtype=str, keep_default_na=False)
    trd = extra.get("TRD", {})
    d = dr.DefReqInputs(RU=ru, MPACT=tuple(man._set("MPACT")), PACT_TO_Y=frozenset(zip(pt.d0, pt.d1)),
                        DATA_BAS=st.DATA_BAS, p_animReqCorrFac=capreg, SIMY=2030, BAS=2017,
                        FODDO=tuple(man._set("FODDO")), DATA_TRD=trd)
    fic = _sym("v_feedInpCoeff", req.SIMINI, 4, "level")
    a = adj.AdjustInputs(RU=ru, p_animReqCorrFac1=fedtrm, p_animExcrProtCorrFact_Y={}, p_feedInpCoeffLoad=fic,
                         DATA_TRD=trd)
    mr = pd.read_csv(man.SETS / "Map_RR.csv", dtype=str, keep_default_na=False)
    ms = tuple(man._set("MS"))
    bas_grof = {(r, f): v for (r, c, f), v in st.DATA_BAS.items() if c == "GROF" and r in ms}
    s = csi.SimIniInputs(MS=ms, MAP_RR=frozenset(zip(mr.d0, mr.d1)), DATA_BAS_GROF=bas_grof)
    csi.create_sim_ini_gdx_feed(st, d, a, s)
    # the regional units of the member states with a calibration file (a unit without animals counts as covered)
    ms_cov = {st.R_RAGG_MS.get(r, r) for r in fed_where}
    covered = {r for r in set(ru) | set(ms) if r in fed_where or st.R_RAGG_MS.get(r, r) in ms_cov}
    left = sorted(r for r in ru if r not in covered)
    return st, d, a, s, covered, left, extra


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtol", type=float, default=1e-6)
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--raw", type=Path, default=None)
    o = ap.parse_args()
    st, d, a, s, covered, left, extra = run(o.raw)
    animals = set(man.ANIMALS)
    ru = set(d.RU)
    ms = set(s.MS)
    req.SKIP.clear()
    stats = defaultdict(list)

    def keep(k, units):
        return k[0] in units and k[0] in covered and k[1] in animals

    ref = {k: v for k, v in _sym("p_animReq", req.SIMINI, 4).items() if keep(k, ru)}
    req._compare("p_animReq", {k: v for k, v in st.p_animReq.items() if keep(k, ru)}, ref, stats)
    ref = {k[:3]: v for k, v in _sym("p_animExcrProtCorrFact", req.SIMINI, 4).items() if k[3] == "Y" and keep(k, ru)}
    req._compare("p_animExcrProtCorrFact", {k: v for k, v in a.p_animExcrProtCorrFact_Y.items() if keep(k, ru)}, ref,
                 stats, None)
    for sym in ("p_minFeedShare", "p_maxFeedShare"):
        ref = {k: v for k, v in _sym(sym, req.SIMINI, 4).items() if keep(k, ru)}
        req._compare(sym, {k: v for k, v in getattr(st, sym).items() if keep(k, ru)}, ref, stats)
    ref = {k: v for k, v in _sym("p_animProdDays", req.SIMINI, 3).items() if keep(k, ru | ms)}
    req._compare("p_animProdDays", {k: v for k, v in st.p_animProdDays.items() if keep(k, ru | ms)}, ref, stats, None)
    days_y = {(r, c): v for (r, c, i), v in st.DATA.items() if i == "DAYS"}
    days_y.update({(r, c): v for (r, c, i), v in extra.get("Y_DAYS_MS", {}).items()})
    ref = {k: v for k, v in days_y.items() if keep(k, ru | ms) and st.D(k[0], k[1], "LEVL")}
    req._compare("DATA DAYS Y", {k: v for k, v in s.DATA_DAYS_Y.items() if keep(k, ru | ms)}, ref, stats, None)
    print(f"regional units compared: {len(covered & ru)} of {len(ru)}; left out (no calibration file): "
          f"{len(left)} ({', '.join(left[:12])}{' ...' if len(left) > 12 else ''})")
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
