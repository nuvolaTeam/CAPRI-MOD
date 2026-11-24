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
LIGHT = {"step1", "scale_dgagri", "final_supports", "agriprod", "longrun", "eu_supports",
         "expert_support", "national", "stats", "prep", "coco", "captrd_gms"}


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


def agriprod_cases():
    """agriprod_supports.supports (agriprod_supports.gms) on the inputs of test_captrd_agriprod_supports.py (CAPTRD's
    stored P_Data, BAST and BASM, the member states). SHA-256 of the exact absolute supports, trust levels, bounds and
    the positions whose PercentChange it deletes."""
    import pandas as pd
    from capri_mod.external_paths import REFERENCE
    from capri_mod.pipeline.captrd import agriprod_supports as A
    from capri_mod.pipeline.captrd import prepare as P
    from capri_mod.pipeline.captrd import timesets as TS
    R = REFERENCE / "captrd_results" / "1770"
    ref = lambda n: pd.read_csv(R / f"{n}.csv.gz", dtype={"t": str})            # noqa: E731
    s = P.read_sets()
    T = TS.build(1984, 2070, [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070], 2017,
                 TS.lst_dgagri_for("aglink2023dgAgri"), uaar_years_any=range(1984, 2019),
                 uaar_years_all=range(1995, 2019), expostt_extra=[2019])
    I = A.read_inputs(P.SETS_DIR, P.SETS_DIR.parent / "dat")
    meat = set(pd.read_csv(P.SETS_DIR / "meat.csv", dtype=str).d0)
    pty = list(s.pact_to_y)
    meat_act = sorted({a for a, m in pty if m in meat and a in set(s.maact)})
    cols = set(I.one("agriprodaact")) | {"DCOL", "DCOH", "GROF"} | set(meat_act)
    pdd = ref("P_Data")
    pdd = pdd[pdd.t.str.isdigit() & pdd.col.isin(cols)]
    pdata = {(r, c, w, int(t)): v for r, c, w, t, v in zip(pdd.region, pdd.col, pdd.row, pdd.t, pdd.value)}
    d = ref("data")
    d = d[(d.t == "BAST") & d.col.isin(cols)]
    bm = ref("BASM")
    bm = bm[bm.t == "2070"]
    runr = list(s.ms) + (["BL400000"] if "BL000000" in s.ms else [])
    res = A.supports(I, runr=runr, s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, exante=T.exante, exantet=T.exantet,
                     base_year=2017, lst_expostt=T.lst_expostt,
                     basm={(r, c, w): v for r, c, w, v in zip(bm.region, bm.col, bm.row, bm.value)}, pdata=pdata,
                     bast={(r, c, w): v for r, c, w, v in zip(d.region, d.col, d.row, d.value)}, dcow=["DCOL", "DCOH"],
                     meat_act=meat_act, pact_to_y=pty, prior={})
    dig = lambda q: _digest(sorted((k, float(v).hex()) for k, v in q.items()))      # noqa: E731
    return {"absolute": dig(res.absolute), "trust": dig(res.trust),
            "bounds": _digest(sorted((k, tuple(float(x).hex() for x in v)) for k, v in res.bounds.items())),
            "no_percent": _digest(sorted(res.no_percent))}


def longrun_cases():
    """longrun_supports.supports (longrun_supports.gms) and macro.inha_pdata (its l. 368-389) on seeded random p_data,
    nObs, BASM, BAST, supports, DG AGRI outlook, population, national expert supports and long-run information of a
    scenario (the reference run's has none in the long-run file, so its Longrun branches act only here) over CAPTRD's
    sets, for four member states (Ireland's weights, Poland's and Norway's corrections) and the scenarios bright, cv50
    and another, with two densities of zeros. SHA-256 of the exact results and expert supports."""
    import copy
    import random
    from capri_mod.pipeline.captrd import longrun_supports as LR
    from capri_mod.pipeline.captrd import macro as MA
    from capri_mod.pipeline.captrd import national_supports as NS
    from capri_mod.pipeline.captrd import prepare as P
    s = P.read_sets()
    ms = ["IR000000", "PL000000", "FR000000", "NO000000"]
    cols = ["UVAG", "DOMM", "GROF", "MAPR", "HCOM", "PRCM", "SWHE", "BARL", "DCOL", "SUGB", "INHA", "FORE", "OLND"]
    rows = ["LEVL", "HERD", "SWHE", "BARL", "SUGA", "COMI", "MILK", "EGGS", "SGMT", "SGMI", "RAPE", "SOYA", "DCOL"]
    exante = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070]
    expostt = list(range(1995, 2019))
    out = {}
    for seed, z in ((1, 0.3), (2, 0.6)):
        for scen in (LR.BRIGHT, LR.CV50, "OTHER_SCEN"):
            rng = random.Random(seed)
            val = lambda lo=0.1, hi=100.0: 0.0 if rng.random() < z else rng.uniform(lo, hi)   # noqa: E731
            pdata, basm, bast, support, dg, inha, info = {}, {}, {}, {}, {}, {}, {}
            for r in ms:
                for c in cols:
                    for w in rows:
                        for y in (1999, 2000, 2001):
                            pdata[(r, c, w, y)] = val()
                        basm[(r, c, w)], bast[(r, c, w)] = val(), val()
                        dg[(r, c, w, 2035)] = val() if rng.random() < 0.3 else 0.0
                        for y in exante:
                            support[(r, c, w, y)] = val()
                for y in exante:
                    inha[(r, y)] = rng.uniform(1.0, 50.0)               # the population and its BASM: always given
                basm[(r, "HCOM", "SUGA")], basm[(r, "INHA", "LEVL")] = rng.uniform(1.0, 50.0), rng.uniform(1.0, 50.0)
                for c in cols + ["PROD", "UVAP", "BIOF"]:
                    for w in rows:
                        for y in LR.LONG_YEARS:
                            info[(r, c, w, "factorB2000", scen, y)] = val(0.5, 1.5)
                            info[(r, c, w, "share", scen, y)] = val(0.1, 1.0)
                        info[(r, c, w, "share", scen, "B2000")] = val(0.1, 1.0)
                        info[(r, c, w, "data", scen, "B2000")] = val(0.1, 100.0)
            for y in LR.LONG_YEARS:
                info[("World", "UVAP", "SOYA", "factorB2000", scen, y)] = val(0.5, 1.5)
            S = NS.Expert()
            for r in ms:
                for c in cols:
                    for w in rows:
                        for y in exante:
                            if rng.random() < 0.15:
                                S.ab[(r, c, w, y)] = val()
                            if rng.random() < 0.15:
                                S.pc[(r, c, w, y)] = val(-20.0, 20.0)
            nobs = {(r, c, w) for r in ms for c in cols for w in rows if rng.random() > z}
            C = LR.Context(
                ms=ms, msincl=ms, pdata={k: v for k, v in pdata.items() if v}, nobs=nobs,
                basm={k: v for k, v in basm.items() if v}, bast={k: v for k, v in bast.items() if v},
                s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, pact=["SWHE", "BARL", "DCOL", "SUGB"],
                req_feed=["SWHE"], reqst=list(s.reqst), pact_to_y=list(s.pact_to_y), pact_to_o=list(s.pact_to_o),
                mrkbalee=list(s.mrkbalee), mlk_pro=["MILK"], cows_act=["DCOL"], exante=exante, exantet=exante,
                expostt=expostt, years_cur=sorted(set(expostt) | set(exante)), base_year=2017, bast_year=2018,
                lst_expost=2018, lst_exante=2070, lst_dgagri=2035, phase_in=2025, infl=1.019,
                support={k: v for k, v in support.items() if v}, dgagri1={k: v for k, v in dg.items() if v},
                map_rr=list(s.map_rr), cur_europ_agg=["EU014000", "EU013000", "EU27yr19"], inha=inha, scenario=scen,
                longrun_info_all={k: v for k, v in info.items() if v})
            S1 = copy.deepcopy(S)
            res = LR.supports(S1, C)
            dig = lambda q: _digest(sorted((k, float(v).hex()) for k, v in q.items()))      # noqa: E731
            out[(seed, scen)] = [dig(res.b2000), dig(res.longrun), dig(res.longrun1), dig(S1.ab), dig(S1.pc),
                                 dig(S1.tr)]
            macro = {(r, y): val(1.0, 50.0) for r in ms for y in exante + [2016, 2017]}
            macro.update({(r, "BAS"): val(1.0, 50.0) for r in ms})
            wp = {(y, r): val(1.0, 50.0) for r in ms for y in exante + [2017]}
            ip = MA.inha_pdata({k: v for k, v in macro.items() if v}, ms=ms, basm={r: val() for r in ms},
                               years_cur=C.years_cur, bast_year=2018, exante=exante,
                               world_pop={k: v for k, v in wp.items() if v}, basy=2017)
            out[(seed, scen, "inha")] = dig(ip)
    return out


def eu_supports_cases():
    """eu_supports.eu_supports (define_eu_supports.gms, every ex-ante year in turn) on seeded random Step2, Step3,
    DGAgri, DGAgri1, supports, experts, trust levels, wVarErr, Longrun, Longrun1, quotas, BASM, BAST, BAS and nObs, with
    test_captrd_eu_supports.py's sets restricted to the positions its statements name (and those of
    adjust_to_biof_supports.gms) and four member states of the two EU parts, for two densities of zeros. SHA-256 of
    every position it changes. Run both sides with the same PYTHONHASHSEED (e.g. 0): some of the module's sums run
    over sets in hash order (the refactor's C6), so their last digits differ between interpreter runs otherwise."""
    import random
    import pandas as pd
    from capri_mod.external_paths import REFERENCE
    from capri_mod.pipeline.captrd import eu_supports as EU
    from capri_mod.pipeline.captrd import final_supports as F
    from capri_mod.pipeline.captrd import prepare as P
    from capri_mod.pipeline.captrd import timesets as TS
    G = REFERENCE / "sets" / "simini_21730"
    s = P.read_sets()
    rd = lambda n: pd.read_csv(P.SETS_DIR / f"{n}.csv", keep_default_na=False)    # noqa: E731
    one = lambda n: rd(n).d0.tolist()                                            # noqa: E731
    two = lambda n: list(zip(rd(n).d0, rd(n).d1))                                # noqa: E731
    simg = lambda n: pd.read_csv(G / f"{n}.csv", keep_default_na=False)          # noqa: E731
    gl = pd.read_csv(P.SETS_DIR / "globiom" / "euallagg.csv").d0.tolist()
    cols1, rows1 = EU.est_sets(s.s_colsest, s.s_rowsest)
    want_c = {"GROF", "MAPR", "IMPT", "EXPT", "NTRD", "DOMM", "FEDM", "HCOM", "PRCM", "INDM", "PRCI", "BIOF", "UVAG",
              "UVAD", "EAAG", "EXPE", "LOSM", "SEDM", "UAAR", "SWHE", "MAIZ", "RAPE", "SUGB", "SOWS", "PIGF", "HENS",
              "POUF", "SHGM", "SHGF", "DCOL", "DCOH", "CERE", "OILS", "BULL", "INDU"}
    want_r = {"LEVL", "HERD", "TOOU", "SWHE", "MAIZ", "RAPE", "SUGB", "SUGA", "DDGS", "FPRO", "COMI", "IPIG", "YPIG",
              "ICHI", "YCHI", "ILAM", "YLAM", "PORK", "BEEF", "SGMI", "CERE", "OILS", "RAPO", "RAPC", "MILK", "OILS"}
    cols = [c for c in cols1 if c in want_c]
    rows = [w for w in rows1 if w in want_r]
    py = pd.read_csv(P.SETS_DIR.parent / "dat" / "biofuel_proc_yields.csv")
    FS = F.Sets(biostock=one("biostock"), biostock_oilp=one("biostockoilp"), oseeds=one("oseeds"), seco=one("seco"),
                grcu=one("grcu"), cropo=one("cropo"), prcd=two("prcd"), sed_to_oil=two("sed_to_oil"),
                oil_to_cak=two("oil_to_cak"), bio_prcd=two("bio_prcd"), pact_to_y=list(s.pact_to_y),
                shift_sugb=one("shiftsugbpos"), dompos=one("dompos"), mcact=one("mcact"), s_colsest=cols,
                s_rowsest=rows, proc_yields=dict(zip(py.row, py.value)))
    ms = ["AT000000", "DE000000", "PL000000", "BG000000"]
    rto = simg("R_T_OAGG")
    S = EU.Sets(ms=ms, rmaggsup=sorted(set(one("rmaggsup")) | {"EU013000", "EU014000"}),
                ms_to_agg=[(b, a) for a, b in s.map_rr if a in set(gl)], euparts=["EU014000", "EU013000"],
                cur_europ_agg=["EU014000", "EU013000", "EU27yr19"], s_colsest=cols, s_rowsest=rows,
                mrkbalee=one("mrkbalee"), dompos=one("dompos"), pric=["UVAG"], pact_to_y=list(s.pact_to_y),
                pact_to_io=two("pact_to_io"), maact=list(s.maact), mcact=one("mcact"), cact=list(s.cact),
                grpc=one("grpc"), grpr=one("grpr"), cropc_to_g=[(b, a) for a, b in two("cropc_to_g")],
                rows_to_g=[(b, a) for a, b in two("rows_to_g")],
                aact_365=["DCOW", "DCOL", "DCOH", "SCOW", "SOWS", "SHGM", "HENS"],
                meas=rto[rto.d0 == "MEAS"].d1.tolist(), tradeest=one("tradeest"), secod=simg("SECOD").d0.tolist(),
                prcd=two("prcd"), dcow=["DCOL", "DCOH"], biof=FS)
    exante = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070]
    L = TS.lst_dgagri_for("aglink2023dgAgri")
    T0 = TS.build(1984, 2070, exante, 2017, L, uaar_years_any=range(1984, 2019), uaar_years_all=range(1995, 2019),
                  expostt_extra=[2019])
    Y = EU.Years(lst_dgagri=L, lst_exante=max(exante), phase_in=2025, fst_exante=T0.fst_exante,
                 sec_exante=T0.sec_exante, lst_expostt=T0.lst_expostt, before=dict(T0.before), bas_year=2017,
                 bast_year=2018, bast_ord=T0.bast, fst_for_biof=min(exante))
    regs = ms + ["EU013000", "EU014000"]
    years = sorted(set(exante) | {L})
    out = {}
    for seed, z in ((1, 0.3), (2, 0.7)):
        rng = random.Random(seed)
        val = lambda lo=0.1, hi=100.0: 0.0 if rng.random() < z else rng.uniform(lo, hi)   # noqa: E731

        def pos(lo=0.1, share=1.0):
            d = {}
            for r in regs:
                for c in cols:
                    for w in rows:
                        for y in years:
                            if rng.random() < share:
                                v = val(lo)
                                if v:
                                    d[(r, c, w, y)] = v
            return d
        basm, bast, bas = ({(r, c, w): v for (r, c, w, y), v in pos(-20.0).items() if y == L} for _ in range(3))
        nobs = {(r, c, w) for r in ms for c in cols for w in rows if rng.random() > z}
        Pp = EU.Pos(step2=pos(-20.0), step3=pos(), dgagri=pos(), dgagri1=pos(-20.0), support=pos(-20.0),
                    support1=pos(), expert=pos(0.1, 0.2), trust=pos(1.0, 0.5), wvar=pos(), longrun=pos(),
                    longrun1=pos(0.1, 0.5), extrap=pos(0.1, 0.3),
                    quts={(r, "QUTS", w, y): v for (r, c, w, y), v in pos(0.1, 0.1).items()})
        pa, ll, ul = {}, {}, {}
        for y in exante:
            EU.eu_supports(Pp, y, S, Y, bast=bast, basm=basm, bas=bas, nobs=nobs, prd_adj=pa, low_lim=ll, upp_lim=ul)
        dig = lambda q: _digest(sorted((k, float(v).hex()) for k, v in q.items()))      # noqa: E731
        out[seed] = {n: dig(getattr(Pp, n)) for n in ("step2", "dgagri", "dgagri1", "support", "trust", "wvar",
                                                      "longrun1", "extrap", "expert")}
        out[seed]["biof"] = [dig(pa), dig(ll), dig(ul)]
    return out


def expert_support_cases():
    """expert_support.gms's own statements: expert_rules.rules, dairy_supports.dairy (and hcom_expert),
    expert_support.herd_floor and toou on seeded random supports, BASM, BAST, BAS, p_data, DG AGRI positions, dairy
    tables and expert supports over CAPTRD's member states, sets and time sets, for two densities of zeros. SHA-256 of
    the exact results."""
    import random
    import pandas as pd
    from capri_mod.pipeline.captrd import dairy_supports as D
    from capri_mod.pipeline.captrd import expert_rules as ER
    from capri_mod.pipeline.captrd import expert_support as XS
    from capri_mod.pipeline.captrd import national_supports as NS
    from capri_mod.pipeline.captrd import prepare as P
    from capri_mod.pipeline.captrd import timesets as TS
    s = P.read_sets()
    DAT = P.SETS_DIR.parent / "dat"
    exante = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070]
    T = TS.build(1984, 2070, exante, 2017, TS.lst_dgagri_for("aglink2023dgAgri"), uaar_years_any=range(1984, 2019),
                 uaar_years_all=range(1995, 2019), expostt_extra=[2019])
    ms = list(s.ms)
    runr = ms + ["BL400000"]
    europ = ["EU014000", "EU013000", "EU27yr19"]
    breed = pd.read_csv(P.SETS_DIR / "breedact.csv", keep_default_na=False, dtype=str).d0.tolist()
    ncnc = sorted(s.ncnc)[:6]
    m2 = pd.read_csv(DAT / "dairy_ms_agri_to_ms.csv", keep_default_na=False)
    agri = sorted(set(m2.ms_agri))
    cols = ["GROF", "DOMM", "EAAG", "PRCM", "EXPE", "UVAG", "HCOM", "IMPT", "EXPT", "FEDM", "LOSM", "PRCY", "INDM",
            "PRCI", "UAAR", "SHGM", "DCOL", "DCOH", "HCOS", "S1COM", "MAPR"] + breed[:3] + ncnc
    rows = ["COMI", "LEVL", "HERD", "SUGB", "SUGA", "MOLA", "MAIZ", "HFCS", "SLGW", "SGMI", "INCE", "MILK", "TOOU"]
    years = sorted(set(range(1999, 2021)) | set(T.years_cur) | set(exante))
    out = {}
    for seed, z in ((1, 0.3), (2, 0.7)):
        rng = random.Random(seed)
        val = lambda lo=0.1, hi=100.0: 0.0 if rng.random() < z else rng.uniform(lo, hi)   # noqa: E731
        regs = runr + europ + ["A_EU_WEST", "A_EU_EAST"]

        def pos(ys, share=0.6, lo=0.1):
            d = {}
            for r in regs:
                for c in cols:
                    for w in rows:
                        for y in ys:
                            if rng.random() < share:
                                v = val(lo)
                                if v:
                                    d[(r, c, w, str(y))] = v
            return d
        support = pos(exante + [2015, 2020])
        pdata = pos(years, 0.3)
        dg = pos(sorted(set(T.years_cur) | {2015}), 0.4)
        dg.update({(r, "HCOS", "HFCS", str(y)): rng.uniform(0.05, 0.4) for r in ms + europ for y in exante})
        dg.update({(r, c, "COMI", str(y)): rng.uniform(100.0, 1000.0) for r in europ for c in ("GROF", "HCOM")
                   for y in T.years_cur})                              # the aggregates' outlook: always given
        basm3 = {(r, c, w): v for (r, c, w, y), v in pos([2070], 0.8).items()}
        bast3 = {(r, c, w): v for (r, c, w, y), v in pos([2070], 0.5).items()}
        E = ER.rules(ms=ms, ms_no_eu=list(s.msnoeu28), exante=exante, bas_year=2017, support=support, basm=basm3,
                     bast=bast3, pdata_years=pdata, dgagri=dg, dgagri1=pos(exante, 0.4),
                     ms_to_agg=[(b, a) for a, b in s.map_rr], europ_aggs=europ, breed_act=breed[:3], ncnc=ncnc,
                     coef_hfcs={"SUGA": 0.9, "MAIZ": 0.6})
        dig = lambda q: _digest(sorted((k, repr(v)) for k, v in q.items()))      # noqa: E731
        out[(seed, "rules")] = dig(E)
        tables = {n: {(a, y): rng.uniform(990.0, 1010.0) * 1.01 ** (y - 2010) for a in agri for y in range(2010, 2021)}
                  for n in D.TABLES}

        dpos = [(c, w) for c in ("DCOL", "DCOH") for w in ("LEVL", "HERD", "COMI")] + [
            (c, "COMI") for c in ("GROF", "HCOM", "DOMM", "EAAG", "PRCM", "UVAG", "EXPE")] + [("PRCM", "SGMI")]

        def series(ys):
            """complete series growing about 1% a year, the cows' milk yields near 7000 kg, a twentieth of the series
            left out whole (random years make the dairy logistic overflow: real series are complete)"""
            d = {}
            for r in regs:
                for c, w in dpos:
                    if rng.random() < 0.05:
                        continue
                    f = rng.uniform(50.0, 50.5) * (140.0 if c in ("DCOL", "DCOH") and w == "COMI" else 1.0)
                    for y in ys:
                        d[(r, c, w, str(y))] = f * 1.01 ** (y - 2015) * rng.uniform(0.999, 1.001)
            return d
        dbasm = {k[:3]: v for k, v in series([2070]).items()}
        Ed, share = D.dairy(runr=runr, ms=ms, ms_no_eu28=list(s.msnoeu28), dcow=["DCOL", "DCOH"], base_year=2017,
                            exante_t=T.exantet, expost=T.expost, expostt=T.expostt, years_cur=T.years_cur,
                            sim_years=exante, fst_exante=T.fst_exante, lst_exante=2070, lst_dgagri=T.lst_dgagri,
                            tables=tables, ms_agri_to_ms=list(zip(m2.ms_agri, m2.region)),
                            recent={r: rng.uniform(-0.01, 0.03) for r in runr}, basm=dbasm,
                            support=series(sorted(set(exante) | {2015, 2020})), pdata=series(years),
                            dgagri=series(sorted(set(T.years_cur) | {2015})),
                            map_rr=list(s.map_rr) + [(r, r) for r in runr],
                            europ_aggs=europ, sub_aggs=["EU014000", "EU013000"], eu13="EU013000", eu14="EU014000",
                            west="A_EU_WEST", east="A_EU_EAST")
        out[(seed, "dairy")] = [dig(Ed), dig(share)]
        Ex = {k: v for k, v in support.items() if rng.random() < 0.3}
        out[(seed, "hcom")] = dig(D.hcom_expert(share, Ex, support, ms, T.exantet))
        i4 = lambda d: {(r, c, w, int(y)): v for (r, c, w, y), v in d.items()}   # noqa: E731
        sup4 = i4(support)
        bas3 = {(r, c, w): v for (r, c, w, y), v in pos([2070], 0.7).items()}
        XS.herd_floor(sup4, ms=ms, maact=["DCOL", "DCOH", "SHGM"] + breed[:3], bas=bas3, bast=bast3,
                      exantet=T.exantet, base_year=2017, bast_year=2018, lst_exante=2070)
        S = NS.Expert(ab=i4({k: v for k, v in pos(exante, 0.1).items()}),
                      pc=i4({k: v for k, v in pos(exante, 0.1, -20.0).items()}),
                      tr=i4({k: v for k, v in pos(exante, 0.05).items()}))
        pty = [("DCOL", "COMI"), ("DCOH", "COMI"), ("SHGM", "SGMI"), ("UAAR", "MAIZ"), ("GROF", "SUGB")]
        for (r, c, w, y), v in pos(exante, 0.3).items():
            sup4[(r, c, "TOOU", int(y))] = v
        XS.toou(S, support=sup4, basm={**basm3, **{(r, c, "TOOU"): val() for r in ms for c in cols}}, ms=ms,
                s_colsest=cols, exante=exante, pact_to_y=pty, longrun1=i4(pos(exante, 0.1)))
        out[(seed, "floor_toou")] = [dig(sup4), dig(S.ab), dig(S.tr)]
    return out


def national_cases():
    """national_supports.supports (national_supports.gms) on seeded random expert supports (Absolute, PercentChange,
    TrustLevl, bounds), supports, BASM, BAST, BAS, p_data and DGAgri1 over the positions its rules name, for every
    member state, BL400000, NO000000 and TUR, with CAPTRD's sets and NECP's herds, for two densities of zeros. SHA-256
    of the expert supports, the bounds, the supports (CS000000's rewritten) and p_natExpert."""
    import random
    import pandas as pd
    from capri_mod.external_paths import REFERENCE
    from capri_mod.pipeline.captrd import national_supports as NS
    from capri_mod.pipeline.captrd import prepare as P
    from capri_mod.pipeline.captrd import timesets as TS
    G = REFERENCE / "sets" / "simini_21730"
    g_ = lambda n: pd.read_csv(G / f"{n}.csv", keep_default_na=False).d0.str.upper().tolist()   # noqa: E731
    s = P.read_sets()
    I0 = NS.read_inputs(P.SETS_DIR, P.SETS_DIR.parent / "dat")
    I = NS.read_inputs(P.SETS_DIR, P.SETS_DIR.parent / "dat")
    exante = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070]
    T = TS.build(1984, 2070, exante, 2017, TS.lst_dgagri_for("aglink2023dgAgri"), uaar_years_any=range(1984, 2019),
                 uaar_years_all=range(1995, 2019), expostt_extra=[2019])
    ms = list(s.ms)
    runr = ms + ["BL400000"]
    nt2est = sorted({b for a, b in s.map_rr if a in set(s.ms) and b in set(s.nt2ext)})
    cols = ["DCOL", "DCOH", "SCOW", "GROF", "DOMM", "EAAG", "PRCM", "EXPE", "MAPR", "HCOM", "PIGF", "SOWS", "POUF",
            "HENS", "SHGM", "SHGF", "INDM", "VSET", "MAIF", "SWHE", "BARL", "BULL"]
    rows = ["LEVL", "HERD", "COMI", "MILK", "PORK", "DAYS", "YPIG", "IPIG", "SGMI", "SGMT", "MAIF", "POUM", "EGGS",
            "ICOW", "YCAM", "YCAF", "YCOW", "ICAM", "ICAF", "YLAM", "ILAM", "SWHE", "BARL"]
    years = sorted(set(range(1995, 2071)))
    out = {}
    for seed, z in ((1, 0.3), (2, 0.7)):
        rng = random.Random(seed)
        val = lambda lo=0.1, hi=100.0: 0.0 if rng.random() < z else rng.uniform(lo, hi)   # noqa: E731

        def pos(regs, ys, share=0.5, lo=0.1, hi=100.0):
            d = {}
            for r in regs:
                for c in cols:
                    for w in rows:
                        for y in ys:
                            if rng.random() < share:
                                v = val(lo, hi)
                                if v:
                                    d[(r, c, w, y)] = v
            return d
        regs = runr + ["NO000000", "TUR"]
        S = NS.Expert(ab=pos(regs, exante, 0.2), pc=pos(regs, exante, 0.15, -20.0, 20.0),
                      tr=pos(regs, exante, 0.2, 1.0, 10.0), lo=pos(regs, exante, 0.05), up=pos(regs, exante, 0.05))
        for k in [k for k in S.pc if k in S.ab]:
            del S.pc[k]
        k3 = lambda d: {k[:3]: v for k, v in d.items()}          # noqa: E731
        X = NS.Context(
            ms=ms, runr=runr, nuts0=g_("NUTS0"), nuts0_and_2=g_("NUTS0_and_2"), nt2est=nt2est, nt2=s.srnuts2,
            map_rr=s.map_rr, s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, cact=s.cact, maact=s.maact,
            oiyani=g_("OIYANI"), pact_to_y=list(s.pact_to_y), p_t_actagg=s.p_t_actagg, exante=exante,
            exantet=T.exantet, expostt=T.expostt, basyrsm=T.basyrsm, base_year=2017, bast_year=T.lst_expostt - 1,
            lst_expost=T.lst_expost, lst_expostt=T.lst_expostt, lst_exante=2070, lst_dgagri=T.lst_dgagri,
            support=pos(regs, exante, 0.6), basm=k3(pos(regs, [0], 0.8)), bast=k3(pos(regs, [0], 0.6)),
            bas=k3(pos(regs, [0], 0.7)),
            pdata={**pos(regs + nt2est, [T.lst_expost, T.lst_expostt] + list(T.basyrsm), 0.3),
                   **{(r, c, w, y): v for (r, c, w, y), v in pos(regs, years, 0.02).items()}},
            dgagri1=pos(["NO000000", "TUR"], sorted(set(exante) | {T.lst_dgagri}), 0.8), years=list(range(1984, 2071)))
        for r in regs:                                          # the dairy positions' BASM: always given (divisors)
            for c in ("DCOL", "DCOH", "GROF", "DOMM", "EAAG", "PRCM", "EXPE", "HCOM"):
                X.basm[(r, c, "COMI")] = rng.uniform(50.0, 100.0)
            for c in ("DCOL", "DCOH"):
                for w in ("LEVL", "HERD"):
                    X.basm[(r, c, w)] = rng.uniform(50.0, 100.0)
            X.basm[(r, "SOWS", "YPIG")] = rng.uniform(10.0, 30.0)
        I.necp = dict(I0.necp)                                  # NECP's herds plus random series (IT, PT have none)
        for r in ms:
            for xc in I.one("xpcols"):
                if rng.random() < 0.3:
                    f = rng.uniform(50.0, 100.0)
                    for y in range(2000, 2071):
                        I.necp[(r, xc, y)] = f * (1.0 + 0.01 * (y - 2017)) * rng.uniform(0.99, 1.01)
        nat = NS.supports(S, I, X)
        dig = lambda q: _digest(sorted((k, float(v).hex()) for k, v in q.items()))      # noqa: E731
        out[seed] = [dig(S.ab), dig(S.pc), dig(S.tr), dig(S.lo), dig(S.up), dig(X.support), dig(nat)]
    return out


def stats_cases():
    """define_stats_and_supports.gms's supports and their storage on seeded random inputs over CAPTRD's sets:
    supports.supports (both settings of the variance floor) and uvag_from_dgagri1, final_supports.overwrite,
    mcact_scale, wvarerr and domm_wvarerr, expert_support.expert, sugb_trade and trust, coco_supports.coco_supports,
    for two densities of zeros. SHA-256 of the exact results."""
    import random
    import pandas as pd
    from capri_mod.external_paths import REFERENCE
    from capri_mod.pipeline.captrd import coco_supports as CO
    from capri_mod.pipeline.captrd import expert_support as XS
    from capri_mod.pipeline.captrd import final_supports as F
    from capri_mod.pipeline.captrd import national_supports as NS
    from capri_mod.pipeline.captrd import prepare as P
    from capri_mod.pipeline.captrd import supports as SU
    G = REFERENCE / "sets" / "simini_21730"
    g_ = lambda n: set(pd.read_csv(G / f"{n}.csv").d0)                    # noqa: E731
    s = P.read_sets()
    C = P.SETS_DIR
    pty = set(map(tuple, pd.read_csv(G / "PACT_TO_Y.csv")[["d0", "d1"]].values))
    sets = SU.SupportSets(pact_to_y=pty, mcact=g_("MCACT"), no_yield_drop=set(pd.read_csv(C / "noyielddrop.csv").d0),
                          breed_act={"DCOL", "DCOH", "SCOW", "SHGM", "SOWS", "HENS"}, grs_act=g_("GRSACT"),
                          reqst={"ENNE", "CRPR", "FILG", "FICT", "FISM", "FISF"}, feed=g_("FEED"), mpact=g_("MPACT"),
                          reqfcnlim={("DCOL", "DAYS"): (300.0, 400.0), ("PIGF", "DAILY"): (0.5, None),
                                     ("BULL", "DAYS"): (None, 500.0), ("SOWS", "DAYS"): (-5.0, 380.0),
                                     ("HENS", "DAYS"): (30.0, 40.0)})
    regs = ["AT000000", "DE000000", "FR000000", "PL000000"]
    cols = ["NTRD", "GROF", "CSSP", "UAAR", "SWHE", "MAIZ", "GRAS", "DCOL", "PIGF", "BULL", "SOWS", "DOMM", "FEDM",
            "HCOM", "UVAG", "IMPT", "EXPT", "SUGB", "DCOH", "EAAG", "LOSM", "SEDM", "TOOU"]
    rows = ["LEVL", "SWHE", "MAIZ", "SLGW", "DAYS", "DAILY", "FCER", "ENNE", "COMI", "SUGB", "TOOU", "GRAS", "MILK",
            "IPIG", "CSSP"]
    years = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070]
    out = {}
    for seed, z in ((1, 0.2), (2, 0.6)):
        rng = random.Random(seed)
        val = lambda lo=0.1, hi=100.0: 0.0 if rng.random() < z else rng.uniform(lo, hi)   # noqa: E731
        idx = pd.MultiIndex.from_tuples([(r, c, w) for r in regs for c in cols for w in rows
                                         if w not in ("DAYS", "DAILY") or rng.random() < 0.5],   # some without data
                                        names=["region", "col", "row"])
        n = len(idx)
        col = lambda lo=0.1, hi=100.0: [val(lo, hi) for _ in range(n)]   # noqa: E731
        st = pd.DataFrame({"nobs": [float(rng.choice([0, 1, 2, 5, 20])) for _ in range(n)], "wr2": col(-0.2, 1.0),
                           "wave": col(-50.0, 100.0), "wvarerr": col(), "basm": col(-10.0, 100.0), "bast": col(),
                           "bas": col(), "bsy": col(), "wvar": col(), "const": col(), "slope": col()}, index=idx)
        step1 = pd.DataFrame({y: col(-10.0, 120.0) for y in years}, index=idx)
        dig = lambda q: _digest(sorted((k, float(v).hex()) for k, v in q.items()))      # noqa: E731
        res = {}
        for fs in (False, True):
            sup, wv = SU.supports(st, step1, years, 2017, 2018, sets, floor_squared=fs)
            res[fs] = [_digest(sorted((k, tuple(float(x).hex() for x in v)) for k, v in zip(sup.index, sup.values))),
                       _digest(sorted((k, float(v).hex()) for k, v in wv.items()))]
        D4 = lambda share=0.5, lo=0.1: {(r, c, w, y): v for r in regs for c in cols for w in rows for y in years   # noqa: E731
                                         for v in [val(lo)] if v and rng.random() < share}
        R = D4(0.7)
        SU.uvag_from_dgagri1(R, D4(0.3), ms=regs, s_rowsest=rows, exante=years)
        E = D4(0.3)
        F.overwrite(R, E, rest=regs, s_colsest=cols, s_rowsest=rows, exante=years)
        F.mcact_scale(R, rest=regs, mcact=["SWHE", "MAIZ", "SUGB"], exante=years)
        TL = D4(0.3, 1.0)
        W = F.wvarerr(E, TL)
        F.domm_wvarerr(W, R, [D4(0.2), E, D4(0.2)], ms=regs, s_colsest=cols, s_rowsest=rows, exante=years,
                       dompos=list(s.dompos))
        S = NS.Expert(ab=D4(0.2), pc=D4(0.2, -20.0), tr=D4(0.2, 1.0))
        b3 = lambda: {(r, c, w): val(-5.0) for r in regs for c in cols for w in rows}   # noqa: E731
        basm, bast = b3(), b3()
        Ex = XS.expert(S, basm=basm, s_colsest=cols, s_rowsest=rows, rest=regs[:3], rmaggsup=regs[3:])
        XS.sugb_trade(Ex, R, ms=regs, exante=years, bast=bast, basm=basm)
        TR = XS.trust(Ex, coco_trust=D4(0.2, 1.0), expert_trust=S.tr, s_colsest=cols, s_rowsest=rows, rest=regs)
        long = [(r, c, w, t, v) for r in regs for c in cols for w in rows for t in ["BASM", "2016", "2017", "2018", "2019"]
                for v in [val(-5.0)] if v]
        pdata = pd.DataFrame(long, columns=["region", "col", "row", "t", "value"])
        nobs = pd.DataFrame([(r, c, w, float(rng.choice([0, 3]))) for r in regs for c in cols for w in rows],
                            columns=["region", "col", "row", "value"])
        co = CO.coco_supports(pdata, nobs, [2018, 2019], 2018, reqst=["ENNE"], mlko=["COMI", "MILK"],
                              bio_cols=["SUGB"], bio_rows=["SUGB"], pact_to_y=pty, cols_est=cols, rows_est=rows,
                              regions=regs)
        out[seed] = {"supports": res, "R": dig(R), "W": dig(W), "expert": dig(Ex), "trust": dig(TR),
                     "coco": _digest(sorted((a, b, c, d, float(e).hex(), float(f).hex(), float(g).hex())
                                            for a, b, c, d, e, f, g in co.itertuples(index=False)))}
    return out


def prep_cases():
    """prep_data_for_estimation.gms: prepare.prep_for_estimation and statistics.statistics (both settings of
    captrd.zeros_as_missing) on seeded random p_data of three member states and two NUTS 2 regions over the positions
    the statements name, with CAPTRD's sets, for two densities of zeros. SHA-256 of the exact p_data they return."""
    import random
    import pandas as pd
    from capri_mod.pipeline.captrd import prepare as P
    from capri_mod.pipeline.captrd import statistics as STA
    s = P.read_sets()
    regs = ["AT000000", "DE000000", "PL000000", "AT310000", "AT120000"]
    cols = ["GROF", "MAPR", "IMPT", "EXPT", "DOMM", "FEDM", "HCOM", "INHA", "UVAG", "EAAG", "PADM", "QUTS", "UAAR",
            "SWHE", "MAIZ", "BARL", "DCOL", "DCOH", "SHGM", "PIGF", "SOWS", "BULL", "UVAD", "EXPE", "foodSh", "NTRD",
            "CSSP", "LOSF", "LOSM", "PRCY", "N_CAL", "N_FAT", "BIOF", "INDM", "SEDM", "CERE", "OILS", "TOOU"]
    rows = ["SUGA", "SWHE", "MAIZ", "BARL", "LEVL", "SLGW", "ILAM", "YLAM", "CATT", "COMI", "BEEF", "PORK", "CERE",
            "MEAS", "ICOW", "FCER", "FGRA", "INCE", "MILK", "MOLA", "MANK", "SGMT", "IBUL", "YCOW", "TOOU", "DAYS"]
    years = [str(y) for y in range(1995, 2020)] + ["BASM"]
    ex = list(range(1995, 2020))
    out = {}
    for seed, z in ((1, 0.3), (2, 0.7)):
        rng = random.Random(seed)
        recs = []
        for r in regs:
            for c in cols:
                for w in rows:
                    if rng.random() < 0.35:
                        continue
                    lo = -20.0 if c in ("DOMM", "NTRD", "CSSP") else 0.0
                    f = rng.uniform(lo, 100.0)
                    for t in years:
                        if rng.random() >= z:
                            recs.append((r, c, w, t, f * rng.uniform(0.8, 1.2) if rng.random() > 0.05 else 1e-5))
        p = pd.DataFrame(recs, columns=["region", "col", "row", "t", "value"])
        p["eps"] = 0
        q = P.prep_for_estimation(p, s, ex, [y for y in ex if abs(y - 2017) <= 3], [2016, 2017, 2018],
                                  range(1984, 2071), luunits={"DCOL": 1.0, "DCOH": 1.0, "PIGF": 0.3, "BULL": 0.8,
                                                              "SHGM": 0.1, "SOWS": 0.5})
        key = lambda d: _digest(sorted((a, b, c, t, float(v).hex()) for a, b, c, t, v in   # noqa: E731
                                       d[["region", "col", "row", "t", "value"]].itertuples(index=False)))
        out[(seed, "prep")] = key(q)
        for zm in (False, True):
            st = STA.statistics(q, s, ex, [y for y in ex if abs(y - 2017) <= 2], range(2011, 2019), first_year=1984,
                                zeros_as_missing=zm)
            out[(seed, "statistics", zm)] = key(st)
    return out


def coco_cases():
    """load_coco1_data.gms: coco.exante_d, prepare_country, bio_flags and apply_country chained as prepare_run does,
    on seeded random COCO1 data, p_data, fao_agg biofuel data and conversion factors, for two member states with NUTS 2
    regions and a non-EU country over the positions the statements name, with CAPTRD's sets, for two densities of
    zeros. SHA-256 of the exact p_data returned."""
    import random
    import pandas as pd
    from capri_mod.pipeline.captrd import coco as CO
    from capri_mod.pipeline.captrd import prepare as P
    s = P.read_sets()
    ms_list = ["AT000000", "PL000000", "NO000000"]
    nt2 = {"AT000000": ["AT310000", "AT120000"], "PL000000": ["PL210000", "PL220000"], "NO000000": []}
    cols = ["UAAR", "GROF", "IMPT", "MAPR", "PRCM", "NETF", "SEDF", "SEDM", "INDM", "BIOF", "HCOM", "LOSM", "LOSF",
            "EXPT", "STCM", "FEDM", "DOMM", "UVAD", "UVAP", "UVAG", "FALL", "VSET", "PRCB", "PRCBY", "NAGR", "CTAX",
            "EAAG", "SWHE", "MAIZ", "DCOL", "DCOH", "DCOW", "BULL", "BULF", "GSET", "NONF", "SETA", "CPRI", "HEIL"]
    rows = ["SWHE", "MAIZ", "OCER", "RAPO", "SUGA", "MILK", "LEVL", "DAYS", "HERD", "BIOD", "BIOE", "DDGS", "DISL",
            "GASL", "CRDO", "GLYC", "BEEF", "GRAS", "COMI", "RYEM", "BARL", "SUNO", "OTHO"]
    years = list(range(2000, 2020))
    expost = list(range(2000, 2019))
    basyrs5, basyrsm = [2015, 2016, 2017, 2018, 2019], [2016, 2017, 2018]
    out = {}
    for seed, z in ((1, 0.3), (2, 0.6)):
        rng = random.Random(seed)
        val = lambda lo=0.0, hi=100.0: 0.0 if rng.random() < z else rng.uniform(lo, hi)   # noqa: E731
        crec, prec = [], []
        for m in ms_list:
            for c in cols:
                for w in rows:
                    if rng.random() < 0.4:
                        continue
                    f = rng.uniform(-10.0 if c in ("DOMM", "FEDM") else 0.0, 100.0)
                    for t in [str(y) for y in years]:
                        v = val() if (c, w) != ("UAAR", "LEVL") else rng.uniform(50.0, 100.0)
                        if v:
                            crec.append((m, "COCO1", c, w, t, f * v / 50.0))
                    for reg in [m] + nt2[m]:
                        for t in [str(y) for y in expost] + ["BASM"]:
                            v = val()
                            if v:
                                prec.append((reg, c, w, t, f * v / 50.0 if rng.random() > 0.05 else 1e-14))
        coco = pd.DataFrame(crec, columns=["region", "item", "col", "row", "t", "value"])
        coco["eps"] = 0
        p0 = pd.DataFrame(prec, columns=["region", "col", "row", "t", "value"])
        p0["eps"] = 0
        bf = pd.DataFrame([(m, c, w, str(y), rng.uniform(0.0, 10.0), 0) for m in ms_list
                           for c in ("NAGR", "EXOG", "PPRI", "PMRK", "PRCB", "PRCBY", "UVAG", "UVAP", "BIOF")
                           for w in ("BIOD", "BIOE", "RAPO", "MAIZ", "GLYC") for y in years if rng.random() > z],
                          columns=["d0", "d1", "d2", "d3", "value", "eps"])
        extr = {"extr_rates": {("BIOE", "SWHE"): 0.3, ("BIOD", "RAPO"): 0.4},
                "byproduct": {("DDGS", "MAIZ"): 0.3, ("DDGS", "OCER"): 0.32}}
        exd = CO.exante_d(coco, s.ms, expost, years)
        prepared, usable = {}, {}
        for m in ms_list:
            pm = p0[p0["region"].isin([m] + nt2[m])]
            prepared[m], usable[m] = CO.prepare_country(coco[coco["region"] == m], pm, m, s, expost, exd, years,
                                                        basyrs5, basyrsm)
        flags = CO.bio_flags(prepared, sorted(set(expost) | set(exd)))
        res = {"exd": tuple(exd), "flags": tuple(sorted(flags))}
        for m in ms_list:
            pm = p0[p0["region"].isin([m] + nt2[m])]
            q, sk = CO.apply_country(pm, prepared[m], usable[m], m, s, expost, exd, years, basyrsm, flags, bf, extr)
            res[m] = (_digest(sorted((a, b, c, t, float(v).hex()) for a, b, c, t, v in
                                     q[["region", "col", "row", "t", "value"]].itertuples(index=False))), tuple(sk))
            res[m + "_coco"] = _digest(sorted((k, tuple(float(x).hex() for x in v.values))
                                              for k, v in prepared[m].s.items()))
        out[seed] = res
    return out


def captrd_gms_cases():
    """captrd.gms's data statements: prepare.load_fixes, load_basm and labour_household on seeded random CAPREG series
    and base-year data over CAPTRD's sets, for two densities of zeros. SHA-256 of the exact p_data returned."""
    import random
    import pandas as pd
    from capri_mod.pipeline.captrd import prepare as P
    s = P.read_sets()
    regs = ["AT000000", "AT310000", "PL000000"]
    lus = sorted(s.landusearto)
    cols = ["GROF", "ARTO", "UAAR", "SWHE", "DCOL", "BULL", "STCM", "HOLD"] + lus + sorted(s.aact)[:4]
    rows = ["LEVL", "LABO", "LABN", "LABH", "DAYS", "DRMN", "DRMX", "EDAYS", "N_EXPT", "SETR", "MILK", "YCOW"] + \
        sorted(s.secom)[:3] + sorted(s.seco)[:2]
    out = {}
    for seed, z in ((1, 0.3), (2, 0.6)):
        rng = random.Random(seed)
        recs = [(r, c, w, t, rng.uniform(-5.0, 100.0)) for r in regs for c in cols for w in rows
                for t in [str(y) for y in range(2010, 2019)] + ["BASM"] if rng.random() > z]
        recs += [(r, "ARTO", "LEVL", t, rng.uniform(50.0, 100.0)) for r in regs for t in [str(y) for y in range(2010, 2019)]]
        recs += [(r, c, "LEVL", t, rng.uniform(-5.0, 20.0)) for r in regs for c in lus for t in [str(y) for y in range(2010, 2019)]]
        p = pd.DataFrame(recs, columns=["region", "col", "row", "t", "value"]).drop_duplicates(["region", "col", "row", "t"],
                                                                                            keep="last")
        d2 = pd.DataFrame([(r, c, w, "Y", rng.uniform(0.1, 100.0)) for r in regs for c in cols for w in rows
                           if rng.random() > z] + [(r, c, "LEVL", "Y", 50.0) for r in regs for c in ("UAAR", "ARTO")],
                          columns=["region", "col", "row", "t", "value"]).drop_duplicates(["region", "col", "row"],
                                                                                         keep="last")
        key = lambda d: _digest(sorted((a, b, c, t, float(v).hex()) for a, b, c, t, v in   # noqa: E731
                                       d[["region", "col", "row", "t", "value"]].itertuples(index=False)))
        q = P.load_fixes(p, s)
        out[(seed, "fixes")] = key(q)
        out[(seed, "basm")] = key(P.load_basm(q, d2, s))
        out[(seed, "labh")] = key(P.labour_household(q))
    return out


LIGHT_CASES = {"step1": step1_cases, "scale_dgagri": scale_dgagri_cases, "final_supports": final_supports_cases,
               "agriprod": agriprod_cases, "longrun": longrun_cases, "eu_supports": eu_supports_cases,
               "expert_support": expert_support_cases, "national": national_cases, "stats": stats_cases,
               "prep": prep_cases, "coco": coco_cases, "captrd_gms": captrd_gms_cases}


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
