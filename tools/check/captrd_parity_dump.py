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
- bounds: estimate_bounds.bounds at every member state and year (both readings of ARTIF's bound) and at the NUTS 2
  regions of four member states, the BoundData synthetic where the reference lacks a statistic (bounds_cases);
- nt2_res: estimate_nuts2.residuals (m_trendNT2) with AT, DE, DK and NL as the regions (the member state's observed
  positions the union of theirs, its fixed values a weighted sum), six years, with and without EX_FEED, and the
  expressions at two years. The inputs are synthetic; every block of m_trendNT2 is reached.

The values are read in the order the code evaluates them, so the hash seed does not matter (the estimation sorts its
sets). About two minutes and 2 GB.
    PYTHONPATH=CHECKOUT python tools/check/captrd_parity_dump.py OUT.pkl      # run in each checkout (git worktree)
    PYTHONPATH=CHECKOUT python tools/check/captrd_parity_dump.py OUT.pkl --parts policy   # one block's part only
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


#: --parts: the parts to dump (None: all): estimation, bounds, nuts2, ms_retries, step3_copies, labour, policy,
#: clean_tiny, and
#: the light ones (no reference data read, or one or two tables): step1, scale_dgagri
PARTS = None
LIGHT = {"step1", "scale_dgagri", "final_supports"}


def step1_cases():
    """step1.run (estimate_trends.gms, define_stats_and_supports.gms l. 47-179, prep_data_for_estimation.gms l. 209-246)
    on 3,000 synthetic series over the ex-post years 1984-2017 (a fixed seed: every count of observations from 0 to 34,
    missing values as NaN and as zeros), evaluated at 1984-2070, with both readings of the short series' grid and of the
    zeros. SHA-256 of every array of the result."""
    import hashlib
    import numpy as np
    from capri_mod.pipeline.captrd import step1 as S1
    rng = np.random.default_rng(20261124)
    S, years = 3000, list(range(1984, 2018))
    T = len(years)
    t = np.arange(1, T + 1) / 10.0
    x = rng.lognormal(3.0, 1.0, (S, 1)) * (1.0 + rng.normal(0.02, 0.05, (S, 1)) * t[None, :] * 10) \
        * rng.lognormal(0.0, 0.1, (S, T))
    keep = rng.random((S, T)) < (np.arange(S) % (T + 1) / T)[:, None]      # every count of observations
    x = np.where(keep, x, np.nan)
    x[rng.random((S, T)) < 0.03] = 0.0
    out = {}
    for coded in (False, True):
        for zm in (False, True):
            r = S1.run(x, years, list(range(1984, 2071)), first_year=1984, as_coded=coded, zeros_as_missing=zm)
            arrs = [r.pre.nobs, r.pre.nw, r.pre.wave, r.pre.wvar, r.fit.a, r.fit.b, r.fit.c, r.fit.wess, r.fit.k_opt,
                    r.wvarerr, r.wr2, r.step1]
            out[(coded, zm)] = [hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest() for a in arrs]
    return out


def scale_dgagri_cases():
    """scale_dgagri.scale (scale_DG_AGRI_baseline.gms) on CAPTRD's stored P_Data as p_data (the member states; the
    population after 2018 left out, as its test) and the stored DGAgri as the Aglink stage's outlook, with the test's
    sets and time sets. SHA-256 of the exact DGAgri1, DGAgri and p_data it returns."""
    import pandas as pd
    from capri_mod.external_paths import REFERENCE
    from capri_mod.pipeline.captrd import prepare as P
    from capri_mod.pipeline.captrd import scale_dgagri as SD
    from capri_mod.pipeline.captrd import timesets as TS
    R, G = REFERENCE / "captrd_results" / "1770", REFERENCE / "sets" / "simini_21730"
    s = P.read_sets()
    sd = lambda n: pd.read_csv(P.SETS_DIR / f"{n}.csv", keep_default_na=False, dtype=str).d0   # noqa: E731
    pdata = pd.read_csv(R / "P_Data.csv.gz", dtype={"t": str})
    pdata = pdata[pdata.region.isin(set(s.ms))]
    yr = pd.to_numeric(pdata.t, errors="coerce")
    pdata = pdata[~((pdata.col == "INHA") & (pdata.row == "LEVL") & (yr > 2018))]
    dg = pd.read_csv(R / "DGAgri.csv.gz", dtype={"t": str})
    resy = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070]
    T = TS.build(1984, 2070, resy, 2017, TS.lst_dgagri_for("aglink2023dgAgri"), uaar_years_any=range(1984, 2019),
                 uaar_years_all=range(1995, 2019), expostt_extra=[2019])
    rto = pd.read_csv(G / "R_T_OAGG.csv", keep_default_na=False, dtype=str)
    D1, D, Pd = SD.scale(pdata, dg, ms=s.ms, ragg=["EU014000", "EU013000"], top=["EU27yr19"], west=["EU014000"],
                         map_rr=s.map_rr, pact=pd.read_csv(G / "PACT.csv", keep_default_na=False, dtype=str).d0,
                         pact_to_y=s.pact_to_y, cols_est=s.s_colsest, rows_est=s.s_rowsest, mrkbalee=sd("mrkbalee"),
                         dompos=sd("dompos"), fuels=sd("fuels"), meas=rto[rto.d0 == "MEAS"].d1,
                         basyrst=T.basyrst, exante=T.exante, years_cur=T.years_cur, years=range(1984, 2071))
    dig = lambda q: _digest(sorted((k, float(v).hex()) for k, v in q.items()))      # noqa: E731
    return {"DGAgri1": dig(D1), "DGAgri": dig(D), "p_data": dig(Pd)}


def final_supports_cases():
    """final_supports.biof_adjust (adjust_to_biof_supports.gms, every ex-ante year in turn, its parameters kept between
    the calls) then final_supports.adjust_trade (adjust_trade_supports.gms) on seeded random supports, experts, BASM,
    BAST, BAS, nObs and quotas over CAPTRD's sets, for five member states and three densities of zeros (negative trade
    included): a move must leave any input's result unchanged, and the zeros reach the statements' conditions. SHA-256 of
    the exact supports, experts and parameters after each."""
    import random
    import pandas as pd
    from capri_mod.pipeline.captrd import final_supports as F
    from capri_mod.pipeline.captrd import prepare as P
    rd = lambda n: pd.read_csv(P.SETS_DIR / f"{n}.csv", keep_default_na=False, dtype=str)   # noqa: E731
    one = lambda n: rd(n).d0.tolist()                                                       # noqa: E731
    two = lambda n: list(zip(rd(n).d0, rd(n).d1))                                           # noqa: E731
    FS = F.Sets(biostock=one("biostock"), biostock_oilp=one("biostockoilp"), oseeds=one("oseeds"), seco=one("seco"),
                grcu=one("grcu"), cropo=one("cropo"), prcd=two("prcd"), sed_to_oil=two("sed_to_oil"),
                oil_to_cak=two("oil_to_cak"), bio_prcd=two("bio_prcd"), pact_to_y=two("pact_to_y"),
                shift_sugb=one("shiftsugbpos"), dompos=one("dompos"), mcact=one("mcact"), s_colsest=one("s_colsest"),
                s_rowsest=one("s_rowsest"))
    ms = ["AT000000", "DE000000", "FR000000", "IT000000", "PL000000"]
    exante = list(range(2019, 2031))
    rows = sorted(set(FS.biostock) | set(FS.oseeds) | set(FS.seco) | set(FS.cropo) | {"SUGB", "SUGA", "MAIZ"})
    cols = sorted({"GROF", "MAPR", "IMPT", "EXPT", "DOMM", "BIOF", "PRCM", "INDM", "NTRD", "LOSM"} | set(FS.dompos)
                  | set(FS.shift_sugb))
    acts = sorted(set(FS.grcu) | {"SUGB"})
    out = {}
    for seed, z in ((1, 0.2), (2, 0.5), (3, 0.8)):
        rng = random.Random(seed)
        val = lambda lo=0.1, hi=1000.0: 0.0 if rng.random() < z else rng.uniform(lo, hi)   # noqa: E731
        FS.proc_yields = {x: rng.uniform(0.2, 0.8) for x in rows}
        R, E, basm, bast, bas, quts = {}, {}, {}, {}, {}, {}
        for r in ms:
            for w in rows:
                for c in cols:
                    lo = -50.0 if c in ("IMPT", "EXPT") else 0.1
                    basm[(r, c, w)], bast[(r, c, w)], bas[(r, c, w)] = val(lo), val(lo), val(lo)
                    for y in exante:
                        R[(r, c, w, y)] = val(lo)
                        if rng.random() < 0.3:
                            E[(r, c, w, y)] = val(lo)
            for a in acts:
                for y in exante:
                    R[(r, a, "LEVL", y)] = val()
            for y in exante:
                quts[(r, "QUTS", "SUGA", y)] = val()
                R[(r, "PRCY", "SUGA", y)] = val(0.05, 0.3)
        R = {k: v for k, v in R.items() if v}
        E = {k: v for k, v in E.items() if v}
        nobs = {(r, c, w) for r in ms for c in cols for w in rows if rng.random() > z}
        pa, ll, ul = {}, {}, {}
        for y in exante:
            F.biof_adjust(R, E, y=y, ms=ms, S=FS, basm=basm, bast=bast, bas=bas, nobs=nobs, quts=quts, prcy=R,
                          lst_dgagri=2017, fst_exante=exante[0], bas_year=2017, bast_year=2018, prd_adj=pa, low_lim=ll,
                          upp_lim=ul)
        dig = lambda q: _digest(sorted((k, float(v).hex()) for k, v in q.items()))      # noqa: E731
        out[(seed, "biof")] = [dig(R), dig(E), dig(pa), dig(ll), dig(ul)]
        F.adjust_trade(R, E, ms=ms, s_rowsest=FS.s_rowsest, exante=exante, basm=basm, dompos=FS.dompos)
        out[(seed, "trade")] = [dig(R), dig(E)]
    return out


LIGHT_CASES = {"step1": step1_cases, "scale_dgagri": scale_dgagri_cases, "final_supports": final_supports_cases}


def want(part):
    return PARTS is None or part in PARTS


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
    if PARTS is not None and "estimation" not in PARTS:        # --parts without the estimation's: those parts only
        out = {}
        if PARTS - LIGHT:
            out["bounds"] = bounds_cases(E, EB, S, data_all, read_csv, res_dir, _P)
        for name, fn in LIGHT_CASES.items():
            if name in PARTS:
                out[name] = fn()
        with open(path, "wb") as fh:
            pickle.dump(out, fh)
        print(f"parts {sorted(PARTS)}: {dict((k, len(v)) for k, v in out.get('bounds', out).items())} -> {path}")
        return
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
    out["bounds"] = bounds_cases(E, EB, S, data_all, read_csv, res_dir, _P)
    for name, fn in LIGHT_CASES.items():
        out[name] = fn()
    with open(path, "wb") as fh:
        pickle.dump(out, fh)
    nt2_blocks = Counter(x[0] for x in out["nt2_res"]["num"][("2030", "")] if x[0] not in N.SHARED_BLOCKS)
    print(f"{len(pts)} points: {sum(len(v) for v in out['ms_res']['num'].values())} m_trendMS residuals, "
          f"{sum(len(v) for v in out['ms_res']['sym'].values())} expressions; {len(out['obj']['ms'])} objectives; "
          f"m_trendNT2 {sum(len(v) for v in out['nt2_res']['num'].values())} residuals, its own blocks at 2030 "
          f"{dict(nt2_blocks)}; bounds at {len(out['bounds']['ms'])} member-state and {len(out['bounds']['regions'])} "
          f"regional cases, {sum(len(a) + len(b) for a, b in out['bounds']['ms'].values())} member-state bounds -> {path}")


BOUND_YEARS = (2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070)      # the reference run's RESY
BOUND_REGIONS_OF = ("AT000000", "DE000000", "ES000000", "IR000000")             # NUTS 2 regions' bounds (region_of)
BOUND_REGION_YEARS = (2018, 2030, 2050)
ORD = dict(ord_bas=2017, ord_bast=2018, lst_exante=2070, fst_exante=2018, lst_expostt=2019, lst_dgagri=2040)
WBA7 = {"AL000000", "MK000000", "CS000000", "MO000000", "HR000000", "BA000000", "KO000000"}


#: the extra cases' data, (col, row, statistic): negative OCRO and OANI bases, data for POUF, INTP and the quota of
#: sugar beet, the COMI losses' BAST absent, no land left beside grassland in one country
EXTRA_STATES = ("BG000000", "DK000000", "PL000000")
EXTRA_DATA = {("GROF", "OCRO", "BASM"): -5.0, ("GROF", "OANI", "BASM"): -3.0, ("OCRO", "OCRO", "BASM"): -2.0,
              ("GROF", "POUF", "nObs"): 1.0, ("INTP", "WHEA", "nObs"): 1.0, ("INTP", "BARL", "nObs"): 1.0,
              ("QUTS", "SUGB", "BASM"): 100.0, ("LOSF", "COMI", "BAST"): 0.0, ("FEDM", "COMI", "BAST"): 0.0,
              ("LOSF", "COMI", "BASM"): 3.0, ("FEDM", "COMI", "BASM"): 2.0, ("PRCM", "COMI", "nObs"): 1.0,
              ("OANI", "OANI", "BASM"): -1.0, ("OANI", "OANI", "nObs"): 1.0}
EXTRA_DATA_OF = {"PL000000": {("UAAR", "LEVL", "BASM"): 0.0}}
EXTRA_RES_NOT_OF = {"BG000000": {("p_data", "QUTA", "COMI"), ("p_data", "QUTB", "COMI")}}   # BG: comi_bounds' fallback
EXTRA_RES = {("p_data", "QUTA", "COMI"): 500.0, ("p_data", "QUTB", "COMI"): 40.0, ("p_data", "QUTS", "SUGB"): 90.0,
             ("Support", "INTP", "WHEA"): -12.0, ("Support", "INTP", "BARL"): 7.0}


def bounds_cases(E, EB, S, data_all, read_csv, res_dir, _P):
    """estimate_bounds.bounds (estimate_ms.gms l. 53-151, fix_est.gms, comi_bounds.gms, biofuel_bounds.gms) at every
    member state and year of the reference run, with both readings of ARTIF's bound (FIX-7), and at the NUTS 2 regions
    of four member states (region_of). The BoundData is synthetic where the reference has no statistic (it needs
    capreg_base for BASM and BSY): BASM data's BASM, else its BAS; BSY BAS x 1.05; BAST data's BAST. lo, up as their
    items in order (hex floats)."""
    B = EB.read_bound_sets()
    names = [("Support", "support"), ("coco", "COCO"), ("Expert", "Expert"), ("expertlo", "expertLo"),
             ("expertup", "expertUp"), ("p_data", "P_Data"), ("BASM", "BASM"), ("step3", "step3")]
    tabs = {k: read_csv(res_dir / f"{f}.csv.gz", dtype={"t": str}, keep_default_na=False) for k, f in names}
    mp = set(zip(*[read_csv(_P.SETS_DIR / "map_rr.csv", dtype=str).get(c) for c in ("d0", "d1")]))
    by_reg = {r: g for r, g in data_all.groupby("region")}
    tab_reg = {k: {r: g for r, g in t.groupby("region")} for k, t in tabs.items()}
    prev_of = {BOUND_YEARS[i]: BOUND_YEARS[i - 1] for i in range(1, len(BOUND_YEARS))}

    def year_tab(k, r, y):
        g = tab_reg[k].get(r)
        if g is None:
            return {}
        g = g[g.t == str(y)]
        return dict(zip(zip(g.col, g.row), g.value.astype(float)))

    def case(r, y, ms, extra=False):
        d = by_reg[r]
        data = {t: dict(zip(zip(g.col, g.row), g.value.astype(float))) for t, g in d.groupby("t")}
        if extra:                                  # branches the reference's data does not reach
            for k, v in {**EXTRA_DATA, **EXTRA_DATA_OF.get(ms, {})}.items():
                data.setdefault(k[2], {})[k[:2]] = v
            for s_ in sorted(S.seco_biof):
                data["nObs"][("INHA", s_)] = 1.0

        def pd_(c, w, st, data=data):
            if st == "BASM":
                return data.get("BASM", {}).get((c, w), data.get("BAS", {}).get((c, w), 0.0))
            if st == "BSY":
                return data.get("BAS", {}).get((c, w), 0.0) * 1.05
            return data.get(st, {}).get((c, w), 0.0)
        res = {k: year_tab(k, r, y) for k, _ in names if k != "step3"}
        if extra:
            for (rp, c, w), v in EXTRA_RES.items():
                if (rp, c, w) not in EXTRA_RES_NOT_OF.get(ms, ()):
                    res[rp][(c, w)] = v
        nobs = {k for k, v in data.get("nObs", {}).items() if v}
        kw = dict(nobs=nobs, bas=data.get("BAS", {}), basm=dict(data.get("BASM", {})), const=data.get("Const", {}),
                  slope=data.get("Slope", {}), pdata=res["p_data"], coco=set(res["coco"]), lo={}, up={}, year=y,
                  exante_d=y <= ORD["lst_expostt"])
        for a in S.maact:
            for q in S.reqst:
                kw["basm"][(a, q)] = pd_(a, q, "BASM")
        sup = res["Support"]
        res["Support"] = E.requirements_relative(E.Point(V=sup, support=sup, **kw), S, sup)
        cs = {(a, q): data.get("Const", {}).get((a, q), 0.0) + data.get("Slope", {}).get((a, q), 0.0)
              for a in S.maact for q in S.reqst}
        prev = prev_of.get(y)
        st3 = year_tab("step3", r, prev) if prev else {}
        n2 = {q for a, q in mp if a == r and q != r and q in by_reg}
        nuts2 = {}
        for q in sorted(n2):
            g = by_reg[q]
            g = g[(g.t == "nObs") & (g.row == "LEVL") & (g.value != 0)]
            for c in set(g.col):
                nuts2[c] = nuts2.get(c, 0) + 1
        west = ("EU014000", r) in mp                # a region's own code, as the tests pass it
        return EB.BoundData(ms=r, year=y, pd=pd_, res=res, exante_d=y <= ORD["lst_expostt"], west=west,
                            east=("EU013000", r) in mp, wba7=r in WBA7, bur=r in {"BG000000", "RO000000"},
                            setr_west=1.0 if west else 0.0, prev=prev, prev_exante_d=prev is not None and prev <= 2019,
                            estp_prev=st3, step3_prev=st3, const_slope={k: v for k, v in cs.items() if v},
                            nuts2_with_data=nuts2 if r == ms else {}, **ORD)

    hexd = lambda m: [(k, float(v).hex()) for k, v in m.items()]          # noqa: E731
    out = {}
    if want("bounds"):
        out.update(bound_parts(E, EB, B, case, mp, by_reg, tab_reg, hexd))
    if want("nuts2"):
        out.update(nuts2_bounds_cases(E, EB, S, B, case, mp, by_reg, tab_reg, year_tab, read_csv, _P, hexd))
    if want("ms_retries"):
        out["ms_retries"] = ms_retries_cases(E, EB, B, case, by_reg, hexd)
    if want("step3_copies"):
        out["step3_copies"] = step3_copies_cases(E, S, B, case, tab_reg, year_tab, read_csv, _P, hexd)
    if want("labour"):
        out["labour"] = labour_cases(by_reg, tab_reg, hexd)
    if want("policy"):
        out["policy"] = policy_cases(by_reg, tab_reg, mp, hexd)
    if want("clean_tiny"):
        out["clean_tiny"] = clean_tiny_cases(E, EB, S, B, case, by_reg, year_tab, hexd)
    return out


def clean_tiny_cases(E, EB, S, B, case, by_reg, year_tab, hexd):
    """clean_tiny.clean (clean_tiny.gms) at eight member states in 2030 and 2050: Solve2's levels the stored step3,
    its bounds estimate_bounds.bounds', its variances 1; the cleaning solve stubbed (estimate_nlp.solve returns its
    start), so the check is of what clean hands it (the supports, bounds, variances and levels) and of its result.
    SHA-256 of the exact dictionaries."""
    from capri_mod.pipeline.captrd import clean_tiny as CT
    from capri_mod.pipeline.captrd import estimate_nlp as NLP
    seen = []

    def stub(pc, S_, B_, d_, lo, up, wv, start, log=None, opts=None, widen=True):
        seen.append(_digest(hexd(pc.support), hexd(lo), hexd(up), hexd(wv), hexd(start)))
        return NLP.Result(dict(start), 0.0, True, 1, "Solve_Succeeded", dict(lo), dict(up))
    real = CT.N.solve
    CT.N.solve = stub
    out = {}
    try:
        T = CT.tiny_sets()
        for ms in ("AT000000", "BG000000", "DE000000", "DK000000", "ES000000", "IR000000", "NL000000", "PL000000"):
            for y in (2030, 2050):
                D = case(ms, y, ms)
                lo, up = EB.bounds(D, B, E.REQS_EFF ** (y - E.REQS_YEAR0), artif_as_coded=False)
                g = by_reg[ms]
                g = g[(g.t == "nObs") & (g.value.astype(float) != 0)]
                p = E.Point(V={}, nobs=set(zip(g.col, g.row)), bas={}, basm={}, const={}, slope={},
                            pdata=D.res["p_data"], coco=set(D.res["coco"]), support=D.res["Support"], lo={}, up={},
                            year=y, exante_d=D.exante_d)
                r2 = NLP.Result(year_tab("step3", ms, y), 0.0, True, 1, "Solve_Succeeded", lo, up)
                seen.clear()
                r = CT.clean(p, S, B, D, r2, {k: 1.0 for k in D.res["Support"]}, T=T)
                out[(ms, y)] = (list(seen), _digest(hexd(r.x), hexd(r.lo), hexd(r.up)))
    finally:
        CT.N.solve = real
    return out


def bound_parts(E, EB, B, case, mp, by_reg, tab_reg, hexd):
    """estimate_bounds.bounds at the member states (both readings of ARTIF's bound, the extra inputs) and the NUTS 2
    regions."""
    out = {"ms": {}, "regions": {}}
    states = sorted(r for r in by_reg if r.endswith("000000") and not r.startswith(("EU", "A_")) and r in tab_reg["Support"])
    for ms in states:
        for y in BOUND_YEARS:
            D = case(ms, y, ms)
            eff = E.REQS_EFF ** (y - E.REQS_YEAR0)
            for coded in (False, True):
                lo, up = EB.bounds(D, B, eff, artif_as_coded=coded)
                out["ms"][(ms, y, coded)] = (hexd(lo), hexd(up))
    for ms in EXTRA_STATES:
        for y in (2018, 2030):
            D = case(ms, y, ms, extra=True)
            lo, up = EB.bounds(D, B, E.REQS_EFF ** (y - E.REQS_YEAR0), artif_as_coded=False)
            out["ms"][(ms, y, "extra")] = (hexd(lo), hexd(up))
    for ms in BOUND_REGIONS_OF:
        regs = sorted(q for a, q in mp if a == ms and q != ms and q in by_reg and q in tab_reg["Support"])
        for y in BOUND_REGION_YEARS:
            Dm = case(ms, y, ms)
            for r in regs:
                D = dataclasses.replace(case(r, y, ms), region_of=ms, ms_pd=Dm.pd, ms_res=Dm.res)
                lo, up = EB.bounds(D, B, E.REQS_EFF ** (y - E.REQS_YEAR0), artif_as_coded=False)
                out["regions"][(r, y)] = (hexd(lo), hexd(up))
    return out


POLICY_STATES = ("AT000000", "BG000000", "DE000000", "IR000000", "MT000000", "PL000000")


def policy_cases(by_reg, tab_reg, mp, hexd):
    """policy.apply (captrd_policy.gms with mquota_update.gms, load_quotas.gms, reformsugarquotas.gms) for POLICY_STATES
    and their NUTS 2 regions, p_data synthetic: the stored exogenous series (P_Data) of the years and data.csv's BAS as
    BASM, the years 1984-2070, the ex-ante years 2018-2070 (2018-2019 with data), the base year 2017, the run's Aglink
    version and milk quota expiry. SHA-256 of the exact frame."""
    import pandas as pd
    from capri_mod.pipeline.captrd import policy as Pol
    from capri_mod.pipeline.captrd import prepare as P
    from capri_mod.settings import current as _settings
    sets = P.read_sets()
    dat = Pol.read_policy_dat()
    years, exante = list(range(1984, 2071)), list(range(2018, 2071))
    exantet = [y for y in exante if y > 2019]
    aglink = str(_settings().get("captrd.aglink"))
    expiry = int(_settings().get("captrd.milk_quota_expiry"))
    pdat = tab_reg["p_data"]
    out = {}
    for variant in ("", "early"):
        # early: the ex-ante years from 2005 (the milk quotas' and the set-aside's years), base beet quotas for the
        # NUTS 2 regions and base set-aside rates
        exa = exante if not variant else list(range(2005, 2071))
        ext = exantet if not variant else list(range(2007, 2071))
        base, bm, lex = (2017, [2016, 2017], 2017) if not variant else (2004, [2003, 2004], 2004)
        for ms in POLICY_STATES:
            regs = [ms] + sorted(q for a, q in mp if a == ms and q != ms and q in by_reg)
            parts = []
            for r in regs:
                g = by_reg[r]
                g = g[g.t == "BAS"]
                parts.append(pd.DataFrame({"region": r, "col": g.col.values, "row": g.row.values, "t": "BASM",
                                           "value": g.value.astype(float).values}))
                if r in pdat:
                    h = pdat[r]
                    h = h[h.t.str.fullmatch(r"\d{4}")]
                    parts.append(pd.DataFrame({"region": r, "col": h.col.values, "row": h.row.values, "t": h.t.values,
                                               "value": h.value.astype(float).values}))
            if variant:
                for i, r in enumerate(regs[1:]):
                    if i % 2 == 0:
                        parts.append(pd.DataFrame([{"region": r, "col": "QUTS", "row": "SUGB", "t": "BASM",
                                                    "value": 10.0 + i}]))
                    parts.append(pd.DataFrame([{"region": r, "col": "GROF", "row": "SUGB", "t": "BASM",
                                                "value": 50.0 + i}]))
                parts.append(pd.DataFrame([{"region": ms, "col": "QUTS", "row": "SUGB", "t": "BASM", "value": 99.0}]))
                parts.append(pd.DataFrame([{"region": r, "col": "BARL", "row": "SETR", "t": "BASM", "value": 6.0}
                                           for r in regs]))
            p = pd.concat(parts, ignore_index=True)
            p = p[p.value != 0].drop_duplicates(["region", "col", "row", "t"])
            p["eps"] = 0
            q = Pol.apply(p, sets, [ms], years, exa, ext, years, bm, lex, base, aglink, dat=dat,
                          expiry=expiry if not variant else 2015)
            q = q.sort_values(["region", "col", "row", "t"]).reset_index(drop=True)
            out[(ms, variant)] = _digest(q.to_csv(index=False))
    return out


def labour_cases(by_reg, tab_reg, hexd):
    """labour.ageline_bounds (labour_ageline.gms l. 33-87) for CAPTRD's MS set from the published age lines, the years
    1984-2070, the ex-ante years 2018-2070 and the base year 2017; then labour_bounds (l. 156-205) for every member
    state of the reference run, its p_data synthetic: the BAS of data.csv's LABT and LEVL as BASM, and a MAXS / MINS
    record to replace. SHA-256 of the exact bounds and frames."""
    import pandas as pd
    from capri_mod.pipeline.captrd import labour as Lab
    from capri_mod.pipeline.captrd import prepare as P
    sets = P.read_sets()
    dat = Lab.read_labour_dat()
    years, exante = list(range(1984, 2071)), list(range(2018, 2071))
    bounds = Lab.ageline_bounds(dat["ageline"], sets, years, exante, 2017)
    out = {"ageline": _digest(*[hexd(bounds[k]) for k in ("expt", "min", "max")])}
    states = sorted(r for r in tab_reg["step3"] if r.endswith("000000") and not r.startswith(("EU", "A_")))
    for ms in states:
        g = by_reg[ms]
        g = g[(g.t == "BAS") & g.row.isin(["LABT", "LEVL"])]
        p = pd.DataFrame({"region": ms, "col": g.col.values, "row": g.row.values, "t": "BASM",
                          "value": g.value.astype(float).values})
        p = pd.concat([p, pd.DataFrame([{"region": ms, "col": "MAXS", "row": "LABO", "t": "2030", "value": 9.0}])],
                      ignore_index=True)
        q = Lab.labour_bounds(p, ms, sets, bounds, dat["min_labour"], exante, years, 2017)
        out[ms] = _digest(q.to_csv(index=False, float_format=None))
    return out


def step3_copies_cases(E, S, B, case, tab_reg, year_tab, read_csv, _P, hexd):
    """step3_copies.copy (copy_labour_biofuel_on_presult.gms) at every member state and year of the reference run: the
    stored step3, the BoundData's BASM (synthetic as bounds_cases'), the stored Expert supports and p_data's INHA.
    SHA-256 of the exact result."""
    from capri_mod.pipeline.captrd import step3_copies as SC
    fos = set(read_csv(_P.SETS_DIR / "fosfuels.csv", keep_default_na=False, dtype=str).d0)
    pact = set(S.mpact) | {a for a, _o in S.pact_to_io}
    out = {}
    states = sorted(r for r in tab_reg["step3"] if r.endswith("000000") and not r.startswith(("EU", "A_")))
    for ms in states:
        for y in BOUND_YEARS:
            D = case(ms, y, ms)
            x = SC.copy(year_tab("step3", ms, y), lambda c, w, D=D: D.pd(c, w, "BASM"), S.mpact, pact, fos,
                        D.res["Expert"], D.res.get("p_data", {}).get(("INHA", "LEVL"), 0.0))
            out[(ms, y)] = _digest(hexd(x))
    return out


MS_RETRY_STATES = ("AT000000", "BG000000", "DE000000", "DK000000", "ES000000", "PL000000")
MS_RETRY_YEARS = (2018, 2030, 2050)
MS_RETRY_TRIES = (3, 6, 24, 26, 29, 31)     # nRepeatedSolves around the thresholds 5, 25 and 30


def ms_retries_cases(E, EB, B, case, by_reg, hexd):
    """estimate_nlp's bound-widening after an infeasible solve (estimate_ms.gms l. 252-420, comi_bounds.gms,
    release_comi_yields.gms, biofuel_bounds.gms): _widen, _oind_ocro and _again from estimate_bounds.bounds' bounds at
    a synthetic solve state, for each try count of MS_RETRY_TRIES, at MS_RETRY_STATES and MS_RETRY_YEARS, plain and
    with the extra inputs of bounds_cases. The state: the positions the bounds, the data and the supports name; the
    levels the bounds' midpoints (0 where one is infinite); every third bounded position at its lower bound and the next
    at its upper; OIND and OCRO at their lower level bounds without production; expert calorie bounds (INCE) for half
    the activities with calorie data. SHA-256 of the exact bounds."""
    from capri_mod.pipeline.captrd import estimate_nlp as NLP
    out = {}
    for ms in MS_RETRY_STATES:
        for y in MS_RETRY_YEARS:
            for extra in (False, True):
                D = case(ms, y, ms, extra=extra)
                eff = E.REQS_EFF ** (y - E.REQS_YEAR0)
                lo, up = EB.bounds(D, B, eff, artif_as_coded=False)
                g = by_reg[ms]
                g = g[(g.t == "nObs") & (g.value.astype(float) != 0)]
                nobs = set(zip(g.col, g.row))
                if extra:
                    nobs |= {("OIND", "LEVL"), ("OCRO", "LEVL"), ("GROF", "OIND")}
                ince = sorted(k for k in nobs if k[1] == "INCE")
                expertlo = dict(D.res.get("expertlo", {}))
                expertup = dict(D.res.get("expertup", {}))
                for i, k in enumerate(ince):
                    if i % 2 == 0:
                        expertlo[k], expertup[k] = 0.5, 2.0
                        lo.setdefault(k, 1.0)
                        up.setdefault(k, 3.0)
                if extra:
                    for c in ("OIND", "OCRO"):
                        lo.setdefault((c, "LEVL"), 2.0)
                p = E.Point(V={}, nobs=nobs, bas={}, basm={}, const={}, slope={}, pdata=D.res["p_data"],
                            coco=set(D.res["coco"]), support=D.res["Support"], lo={}, up={}, year=y,
                            exante_d=D.exante_d)
                keys = sorted(set(lo) | set(up) | nobs | set(D.res["Support"]))
                x, at_lo, at_up = [], {}, {}
                for i, k in enumerate(keys):
                    a_, b_ = lo.get(k, -float("inf")), up.get(k, float("inf"))
                    v = 0.5 * a_ + 0.5 * b_ if abs(a_) < float("inf") and abs(b_) < float("inf") else 0.0
                    if k in (("OIND", "LEVL"), ("OCRO", "LEVL")) and k in lo:
                        v = lo[k]
                        at_lo[k] = v
                    elif k[0] == "GROF" and k[1] in ("OIND", "OCRO"):
                        v = 0.0
                    elif i % 3 == 0 and k in lo:
                        at_lo[k] = lo[k]
                    elif i % 3 == 1 and k in up:
                        at_up[k] = up[k]
                    x.append(v)
                basm = lambda c, w, D=D: D.pd(c, w, "BASM")                                     # noqa: E731
                for ntry in MS_RETRY_TRIES:
                    lo_, up_ = dict(lo), dict(up)
                    NLP._widen(ntry, keys, x, at_lo, at_up, lo_, up_, B, p, expertlo, expertup, basm)
                    NLP._oind_ocro(ntry, keys, x, at_lo, lo_)
                    NLP._again(ntry, D, B, lo_, up_, expertup, at_lo, at_up)
                    out[(ms, y, extra, ntry)] = _digest(hexd(lo_), hexd(up_))
    return out


def _digest(*parts):
    """The SHA-256 of the parts' exact text (hex floats, in order) and their sizes: the NUTS 2 parts are too large to
    keep whole (a difference changes the digest; rerun the case to see it)."""
    import hashlib
    return hashlib.sha256(repr(parts).encode()).hexdigest(), tuple(len(p) for p in parts)


NT2_TRIES = (5, 15, 26, 35, 65)          # nRepeatedSolves: below and above the openings' thresholds (10, 20, 25, 30, 60)


def nuts2_bounds_cases(E, EB, S, B, case, mp, by_reg, tab_reg, year_tab, read_csv, _P, hexd):
    """estimate_nuts2.bounds (estimate_nuts2.gms l. 86-402) for the regions of BOUND_REGIONS_OF at BOUND_REGION_YEARS,
    the member state's result its stored step3 (synthetic: absolute requirements), with and without a sugar quota and
    the regions' expert sugar beet production, expert bounds and a milk quota (the branches the reference does not
    reach); then, from those bounds, _open_bounds and _grid_again (est_Nuts2_grid_openbound.gms, est_nuts2_grid.gms) at a synthetic solve state for each
    try count of NT2_TRIES: the levels the bounds' midpoints, every third bounded position at its lower bound and the
    next at its upper, every fifth with a multiplier, half the requirements and the feeds blocking."""
    import dataclasses as _dc
    from capri_mod.pipeline.captrd import estimate_nuts2 as N
    sets = lambda n: read_csv(_P.SETS_DIR / f"{n}.csv", keep_default_na=False, dtype=str)      # noqa: E731
    one = lambda n: set(sets(n).d0)                                                          # noqa: E731
    cor = one("corfeedlosf")
    losf = {o for i, o in B.feed_to_o if i in cor} & one("cropo")
    fodf = {(i, o) for i, o in B.feed_to_o if i in B.foddi}
    c2g = set(zip(sets("cropc_to_g").d0, sets("cropc_to_g").d1))
    out = {"nt2_bounds": {}, "nt2_retries": {}}
    for ms in BOUND_REGIONS_OF:
        B2 = N.nuts2_bound_sets(B, ms, one("landusearto"))
        regs = sorted(q for a, q in mp if a == ms and q != ms and q in by_reg and q in tab_reg["Support"])
        for y in BOUND_REGION_YEARS:
            for variant in ("", "quota"):
                Dm = case(ms, y, ms)
                ms_V = year_tab("step3", ms, y)
                expert = trust = None
                if variant:
                    Dm.res["p_data"][("QUTS", "SUGB")] = 1000.0
                    expert = {r: {("GROF", "SUGB"): 50.0 + i} for i, r in enumerate(regs)}
                    trust = {r: {("GROF", "SUGB"): 5.0 if i % 2 else 1.0} for i, r in enumerate(regs)}
                D = {}
                for i, r in enumerate(regs):
                    D[r] = _dc.replace(case(r, y, ms), region_of=ms, ms_pd=Dm.pd, ms_res=Dm.res, nuts2_with_data={})
                    if variant:
                        D[r].res["p_data"][("QUTS", "SUGB")] = 100.0 + i
                        D[r].res["p_data"][("QUTA", "COMI")] = 10.0 + i
                        a0 = sorted(B2.mpact)[i % len(B2.mpact)]
                        D[r].res["expertlo"][(a0, "LEVL")] = 0.5
                        D[r].res["expertup"][(a0, "LEVL")] = 2.0
                eff = E.REQS_EFF ** (y - E.REQS_YEAR0)
                lo, up, addn = N.bounds(D, B2, eff, ms_V, Dm.pd, ms_V, losf, fodf, c2g, expert, trust)
                out["nt2_bounds"][(ms, y, variant)] = {r: _digest(hexd(lo[r]), hexd(up[r]), sorted(addn[r]))
                                                       for r in regs}
                nobs = {}
                for r in regs:
                    g = by_reg[r]
                    g = g[(g.t == "nObs") & (g.value.astype(float) != 0)]
                    nobs[r] = set(zip(g.col, g.row)) | addn[r]
                for n in (NT2_TRIES if not variant else NT2_TRIES[::3]):
                    lo_r = {r: dict(lo[r]) for r in regs}
                    up_r = {r: dict(up[r]) for r in regs}
                    lo_prev = {r: dict(lo[r]) for r in regs}
                    up_prev = {r: dict(up[r]) for r in regs}
                    res = {}
                    for r in regs:
                        keys = sorted(set(lo_r[r]) | set(up_r[r]))
                        x = {}
                        for k in keys:
                            a_, b_ = lo_r[r].get(k, -float("inf")), up_r[r].get(k, float("inf"))
                            x[k] = 0.5 * a_ + 0.5 * b_ if abs(a_) < float("inf") and abs(b_) < float("inf") else 0.0
                        at_lo = {k: 1.0 for i, k in enumerate(keys) if i % 3 == 0}
                        at_up = {k: -1.0 for i, k in enumerate(keys) if i % 3 == 1}
                        mx = set(at_lo) | set(at_up) | {k for i, k in enumerate(keys) if i % 5 == 0}
                        reqs_m = {(a, q) for i, (a, q) in enumerate(sorted((a, q) for a in B2.mpact for q in B2.reqst))
                                  if i % 2 == 0}
                        feed_m = {(a, f) for i, (a, f) in enumerate(sorted((a, f) for a in B2.mpact for f in B2.feed))
                                  if i % 2 == 0}
                        N._open_bounds(n, r, D[r], B2, lo_r[r], up_r[r], x, at_lo, at_up, mx, reqs_m, feed_m, ms_V,
                                       nobs[r], D[r].res["Support"], losf | set(N.LOSF_EXTRA), lo_prev, up_prev, regs)
                        N._grid_again(n, r, D[r], B2, lo_r[r], up_r[r], x, at_lo, at_up, mx, nobs[r],
                                      D[r].res["Support"], ms_V)
                        res[r] = _digest(hexd(lo_r[r]), hexd(up_r[r]), hexd(x))
                    out["nt2_retries"][(ms, y, variant, n)] = res
    return out


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
    ap.add_argument("--parts", help="comma-separated parts to dump (a block's own check): estimation, bounds, nuts2, "
                                    "ms_retries, step3_copies, labour, policy, clean_tiny, step1, scale_dgagri; default all")
    a = ap.parse_args()
    if a.parts:
        PARTS = set(a.parts.split(","))
    if a.compare:
        sys.exit(compare(*a.compare))
    if not a.out:
        ap.error("OUT.pkl or --compare REF NEW")
    dump(a.out)
