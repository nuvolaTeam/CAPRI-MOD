"""CAPTRD's estimation equations and objective evaluated at CAPTRD's own Step 2 points, for an exact before/after check
of a refactor of capri_mod/pipeline/captrd (a move must leave every value and every expression unchanged).

Dumped, from CAPTRD's reference run (capri_sources/reference/captrd_results/1770: step2, the data, P_Data, COCO, the
supports, Lo, up, BASM, wVarErr):
- ms_res: estimate_ms.residuals (m_trendMS) at every member state's point of every year, as hex floats, and each
  residual's CasADi expression as text at four points;
- ms_obj: estimate_ms.objective (SSQS_) at the same points, and its expressions at four points;
- nt2_obj: estimate_nuts2.objective with AT, DK and NL standing in as one member state's regions, three years;
- stcm: both objectives again with STCM data added for the young animals (the reference points have none, so the
  STCM pull is otherwise not reached);
- nt2_res: estimate_nuts2.residuals (m_trendNT2) with AT, DE, DK and NL as the regions (the member state's observed
  positions the union of theirs, its fixed values a weighted sum), six years, with and without EX_FEED, and the
  expressions at two years. The inputs are synthetic; every block of m_trendNT2 is reached.

The values are read in the order the code evaluates them, so the hash seed does not matter (the estimation sorts its
sets). About a minute and 2 GB.
    PYTHONPATH=CHECKOUT python tools/check/captrd_parity_dump.py OUT.pkl      # run in each checkout (git worktree)
    python tools/check/captrd_parity_dump.py --compare REF.pkl NEW.pkl
"""
import argparse
import dataclasses
import pickle
import sys
from collections import Counter

MS_SYM = (("DK000000", "2030"), ("ES000000", "2050"), ("PL000000", "2018"), ("FR000000", "2070"))
NT2_OBJ_REGIONS, NT2_OBJ_YEARS = ("AT000000", "DK000000", "NL000000"), ("2018", "2030", "2050")
NT2_RES_REGIONS = ("AT000000", "DE000000", "DK000000", "NL000000")
NT2_RES_YEARS, NT2_RES_SYM = ("2018", "2020", "2030", "2040", "2050", "2070"), ("2018", "2030")


def dump(path):
    import casadi as ca
    from capri_mod.csvio import read_csv
    from capri_mod.external_paths import REFERENCE
    from capri_mod.pipeline.captrd import estimate_bounds as EB
    from capri_mod.pipeline.captrd import estimate_ms as E
    from capri_mod.pipeline.captrd import estimate_nuts2 as N
    from capri_mod.pipeline.captrd import prepare as _P

    res_dir = REFERENCE / "captrd_results" / "1770"
    S = E.read_sets()
    data_all = read_csv(res_dir / "data.csv.gz", dtype={"t": str}, keep_default_na=False)
    tabs_all = {n: read_csv(res_dir / f"{n}.csv.gz", dtype={"t": str}, keep_default_na=False)
                for n in ("step2", "P_Data", "COCO", "support", "Lo", "up", "BASM", "wVarErr")}
    regions = sorted(r for r in set(tabs_all["step2"].region) if r.endswith("000000") and not r.startswith(("EU", "A_")))
    years = sorted(set(tabs_all["step2"].t))
    pts = {}                                   # (ms, year) -> (Point, wVarErr, {activity: LEVL BASM})
    for ms in regions:
        d = data_all[data_all.region == ms]
        data = {t: dict(zip(zip(g.col, g.row), g.value.astype(float))) for t, g in d.groupby("t")}
        nobs = {k for k, v in data.get("nObs", {}).items() if v}
        tabs = {}
        for n, t_ in tabs_all.items():
            t_ = t_[t_.region == ms]
            tabs[n] = {t: dict(zip(zip(g.col, g.row), g.value.astype(float))) for t, g in t_.groupby("t")}
        for y in years:
            if y not in tabs["step2"]:
                continue
            basm = dict(data.get("BASM", {}))
            basm.update(tabs["BASM"].get(y, {}))
            kw = dict(nobs=nobs, bas=data.get("BAS", {}), basm=basm, const=data.get("Const", {}),
                      slope=data.get("Slope", {}), pdata=tabs["P_Data"].get(y, {}), coco=set(tabs["COCO"].get(y, {})),
                      support=tabs["support"].get(y, {}), lo=tabs["Lo"].get(y, {}), up=tabs["up"].get(y, {}),
                      year=int(y), exante_d=int(y) <= 2019)
            st = tabs["step2"][y]
            p = E.Point(V=E.from_stored(E.Point(V=st, **kw), S, st), **kw)
            pts[(ms, y)] = (p, tabs["wVarErr"].get(y, {}), {a: v for (a, w), v in basm.items() if w == "LEVL"})

    def sym1():
        syms = {}
        return lambda c, w: syms.setdefault((c, w), ca.SX.sym(f"{c}|{w}"))

    def sym2():
        syms = {}
        return lambda r, c, w: syms.setdefault((r, c, w), ca.SX.sym(f"{r}|{c}|{w}"))

    out = {"ms_res": {"num": {}, "sym": {}}}
    for key, (p, wv, bl) in pts.items():
        out["ms_res"]["num"][key] = [(a, b, c, float(r).hex()) for a, b, c, r in E.residuals(p, S)]
        if key in MS_SYM:
            out["ms_res"]["sym"][key] = [(a, b, c, str(r)) for a, b, c, r in E.residuals(p, S, var=sym1())]

    def objectives(pp, sym_keys, nt2_years):
        o = {"ms": {}, "ms_sym": {}, "nt2": {}, "nt2_sym": {}}
        for key, (p, wv, bl) in pp.items():
            lo_, up_ = dict(p.lo), dict(p.up)
            f = E.objective(p, S, lambda c, w, p=p: p.V.get((c, w), 0.0), wv, lo_, up_, exante_t=not p.exante_d)
            o["ms"][key] = float(f).hex()
            if key in sym_keys:
                o["ms_sym"][key] = str(E.objective(p, S, sym1(), wv, lo_, up_, exante_t=not p.exante_d))
        for y in nt2_years:
            trio = {ms: pp[(ms, y)] for ms in NT2_OBJ_REGIONS}
            points = {ms: t[0] for ms, t in trio.items()}
            wvar = {ms: t[1] for ms, t in trio.items()}
            bl = {ms: t[2] for ms, t in trio.items()}
            o["nt2"][y] = float(N.objective(points, S, lambda r, c, w: points[r].V.get((c, w), 0.0), wvar, bl)).hex()
            o["nt2_sym"][y] = str(N.objective(points, S, sym2(), wvar, bl))
        return o

    out["obj"] = objectives(pts, MS_SYM, NT2_OBJ_YEARS)
    stcm_pts = {k: (dataclasses.replace(p, nobs=set(p.nobs) | {("STCM", o) for o in S.oyani}), wv, bl)
                for k, (p, wv, bl) in pts.items()}
    out["stcm"] = objectives(stcm_pts, (("DK000000", "2030"), ("PL000000", "2018")), ("2018", "2030"))

    B = EB.read_bound_sets()
    rd = lambda n: set(read_csv(_P.SETS_DIR / f"{n}.csv", keep_default_na=False, dtype=str).d0)   # noqa: E731
    rset, sal = rd("rset"), rd("splitactslo")
    out["nt2_res"] = {"num": {}, "sym": {}}
    for y in NT2_RES_YEARS:
        points = {ms: pts[(ms, y)][0] for ms in NT2_RES_REGIONS}
        ms_nobs = set().union(*(p.nobs for p in points.values()))
        ms_V = {}
        for i, ms in enumerate(NT2_RES_REGIONS):
            for k, v in sorted(points[ms].V.items()):
                ms_V[k] = ms_V.get(k, 0.0) + v * (1.0 + 0.01 * i)
        ex_feed = sorted((a, f) for a, f in ms_nobs if a in S.mpact and f in S.feed)[:3]
        for tag, exf in (("", ()), ("exf", ex_feed)):
            res = N.residuals(points, ms_nobs, ms_V, S, B.foddi, rset, sal, ex_feed=exf)
            out["nt2_res"]["num"][(y, tag)] = [(a, b, c, float(r).hex()) for a, b, c, r in res]
        if y in NT2_RES_SYM:
            res = N.residuals(points, ms_nobs, ms_V, S, B.foddi, rset, sal, var=sym2())
            out["nt2_res"]["sym"][y] = [(a, b, c, str(r)) for a, b, c, r in res]
    with open(path, "wb") as fh:
        pickle.dump(out, fh)
    nt2_blocks = Counter(x[0] for x in out["nt2_res"]["num"][("2030", "")] if x[0] not in N.SHARED_BLOCKS)
    print(f"{len(pts)} points: {sum(len(v) for v in out['ms_res']['num'].values())} m_trendMS residuals, "
          f"{sum(len(v) for v in out['ms_res']['sym'].values())} expressions; {len(out['obj']['ms'])} objectives; "
          f"m_trendNT2 {sum(len(v) for v in out['nt2_res']['num'].values())} residuals, its own blocks at 2030 "
          f"{dict(nt2_blocks)} -> {path}")


def compare(a, b):
    with open(a, "rb") as fa, open(b, "rb") as fb:
        A, B = pickle.load(fa), pickle.load(fb)
    bad = 0
    for sec in sorted(set(A) | set(B)):
        for part in sorted(set(A.get(sec, {})) | set(B.get(sec, {}))):
            x, y = A.get(sec, {}).get(part), B.get(sec, {}).get(part)
            if x == y:
                print(f"{sec}.{part}: identical ({len(x or {})} entries)")
                continue
            bad += 1
            keys = sorted(set(x or {}) | set(y or {}), key=str)
            diff = [k for k in keys if (x or {}).get(k) != (y or {}).get(k)]
            print(f"{sec}.{part}: {len(diff)} of {len(keys)} entries differ, e.g. {diff[:3]}")
    print("IDENTICAL" if not bad else f"DIFFERENT in {bad} parts")
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", nargs="?")
    ap.add_argument("--compare", nargs=2, metavar=("REF", "NEW"))
    a = ap.parse_args()
    if a.compare:
        sys.exit(compare(*a.compare))
    if not a.out:
        ap.error("OUT.pkl or --compare REF NEW")
    dump(a.out)
