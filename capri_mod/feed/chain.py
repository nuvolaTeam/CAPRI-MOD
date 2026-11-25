r"""CAPRI's feed chain of the simulation year for one member state, from CAPREG's base year and CAPTRD's trends to the
simulation's start (CAPRI star 3.0, %feedversion% "_pw"): the rations, requirements, shares and days that CAPRI writes
to sim_ini and its supply model starts from.

CAPRI builds them in two capmod runs:

1. The baseline calibration (%BASELINE% on). capmod/create_sim_ini_gdx.gms builds the year's data (l. 34,
   capmod/load_base_data_and_trends.gms; l. 311-369) and the requirements (l. 417-423: capmod/load_feed.gms with
   CAPREG's corrections, v_actLevl, capmod/def_requirements.gms; baseline/adjust.gms is skipped, l. 425).
   capmod/def_fert_and_requirements.gms l. 30-34 then runs the baseline feed calibration (baseline/fedtrm_prep.gms,
   feed/fedtrm_cal_pw.gms, baseline/fedtrm_fin.gms) and writes its corrections and feed input coefficients to
   results/baseline (fedtrm_<...>.gdx, mefed_<...>.gdx).
2. The simulation (%BASELINE% off). create_sim_ini_gdx.gms builds the same year's data and requirements, then (l. 427-
   461) baseline/adjust.gms with the calibration's corrections (load_feed.gms l. 61-66) and feed input coefficients
   (adjust.gms l. 36-43), the shares, the feeds' rows and the days.

Both runs build the year's data and the requirement call from the same inputs, so feed_chain builds them once and the
simulation's start works on a copy taken before def_requirements.

The inputs (ChainInputs) are CAPRI's, read by the caller: CAPREG's results for the member state (its DATA2 at "Y",
p_technFact, the housing days p_rcEmissions of envind/ammo.gms), CAPREG's requirement corrections (results/capreg/
reqrel_17<CC>, p_animReqCorrFac1) and CAPTRD's trends (DATA2 at "Y"). The literal tables come from capri_data
(req_or_man_params.csv, biofuel_resids_params.csv) and the sets from capri_data/codes/capri.

Not run here, as the simulation's start does not read them:
- the baseline run's manure call and its shares and days (def_fert_and_requirements.gms l. 38-51): the simulation's
  start does its own (create_sim_ini_gdx.gms l. 431-461);
- the baseline run's protein factor (fedtrm_fin.gms l. 52): not written to the calibration's file (l. 54), the
  simulation recomputes it (adjust.gms l. 31-32);
- the straw's losses at "TRD" from the calibration (load_feed.gms l. 79-81).

Departures from CAPRI: none in the sequence.
"""
from __future__ import annotations

import copy
import csv
import dataclasses
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from capri_mod.data.definitions import capri_pairs, capri_set
from capri_mod.feed.equations import adjust as adj
from capri_mod.feed.equations import create_sim_ini_gdx as csi
from capri_mod.feed.equations import def_requirements as dr
from capri_mod.feed.equations import fedtrm_cal_pw as cal
from capri_mod.feed.equations import fedtrm_fin as fin
from capri_mod.feed.equations import fedtrm_prep as fp
from capri_mod.feed.equations import fedtrm_prior_pw as pp
from capri_mod.feed.equations import req_or_man_fnc_req as rq
from capri_mod.projection.equations import create_sim_ini_gdx_data as csd
from capri_mod.projection.equations import load_base_data_and_trends as ly

REQ_PARAMS = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "feed" / "req_or_man_params.csv"
# the columns of DATA the requirement call reads besides the animal and crop activities
OTHER_COLS = ("GRAE", "GRAI", "IHISGR", "FallGr", "OFAR", "MAIF", "INDM", "FEDM", "SHEP", "GOAT", "DRMA", "ENNE", "GROF")


def req_or_man_params(path: Path = REQ_PARAMS) -> dict:
    """The literal tables of feed/feed_decl.gms and dat/feed/porkreq.gms (capri_data/2017/feed/req_or_man_params.csv,
    tools/build/build_req_or_man_params.py): {symbol: {key tuple, or the key of a one-key symbol: value}}."""
    keys = ("key1", "key2", "key3", "key4", "key5")
    out: dict = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = tuple(row[k] for k in keys if row[k])
            out[row["symbol"]][key if len(key) > 1 else key[0]] = float(row["value"])
    return out


@dataclass
class ChainInputs:
    """CAPRI's inputs of the chain for one member state MS (its two letters, as CAPRI's country files: DK, DE).

    capreg: CAPREG's results of the member state's regions (DATA2 at "Y", results/capreg/res_17<CC>);
    trends: CAPTRD's DATA2 at "Y" of the regions loaded (the member state's and every MSALL: FROM_CAPTRD's domain is
    the trends' items in any member state, load_base_data_and_trends.gms l. 654);
    others_bas: DATA at "BAS" of the other member states loaded (may be empty);
    p_technFact: CAPREG's p_technFact of the member state's regions {(region, activity, item, A): share} (the chain
    deletes those of the activities without data, create_sim_ini_gdx.gms l. 146-149);
    p_rcEmissions: CAPREG's p_rcEmissions (housing days) of the member state's regions;
    p_animReqCorrFac: CAPREG's corrections {(region, animal, A, requirement or feed): value} (reqrel_17<CC>,
    p_animReqCorrFac1, as load_feed.gms l. 56-60 loads them).
    SIMY, BAS: the simulation and the base year (CALYEA)."""
    MS: str
    capreg: ly.Data
    trends: ly.Data
    p_technFact: dict
    p_rcEmissions: dict
    p_animReqCorrFac: dict
    others_bas: ly.Data = field(default_factory=ly.Data)
    SIMY: int = 2030
    BAS: int = 2017


@dataclass
class ChainResult:
    """The chain's symbols. D, S: the year's data and sets; regions: the member state's regions; p_exoDemand: energy
    maize's industrial use (create_sim_ini_gdx.gms l. 322); cal: the baseline calibration's state (fedtrm_prep.
    FedtrmState: its v_feedInpCoeff, p_animReq, v_lossQuant); log: the calibration's solves [(aggregate, result)];
    p_animReqCorrFac: the calibration's corrections (fedtrm_fin.gms l. 47-48); st, d, a, si: the simulation's start
    (the requirement call's state with p_animReq, p_minFeedShare, p_maxFeedShare, p_animProdDays; def_requirements'
    inputs with the protein factor p_animExcrProtCorrFact_Y as adjust leaves it; adjust's inputs with the feed input
    coefficients' start v_feedInpCoeff_L and DATA_TRD's feed use; SimIniInputs with DATA_DAYS_Y)."""
    D: ly.Data
    S: ly.YearSets
    regions: set
    p_exoDemand: dict
    cal: fp.FedtrmState
    log: list
    p_animReqCorrFac: dict
    st: rq.ReqState
    d: dr.DefReqInputs
    a: adj.AdjustInputs
    si: csi.SimIniInputs


def regions_of(cc: str, S: ly.YearSets) -> tuple:
    """The member state of the country cc (its files' code: DK, TU) and its regions: the member state and its regions
    in CAPRI's hierarchy (MAP_RR), as in RS. Returns (member state, regions); Turkey is TUR with TR100000, ..."""
    ms = next(m for m in S.MS if m[:2] == cc[:2])
    return ms, {r for r in S.RS if r == ms or (ms, r) in S.MAP_RR}


def year_data(ci: ChainInputs):
    """The member state's year data: CAPREG's base year (load_base_data_and_trends.gms l. 44-199), CAPRI's trends and
    the simulation year (l. 297-863), the technologies' factors of the activities without data (create_sim_ini_gdx.gms
    l. 146-149) and create_sim_ini_gdx.gms l. 311-369. Returns (D, S, the member state's regions, p_exoDemand,
    p_technFact)."""
    S = ly.YearSets.from_codes()
    _, mine = regions_of(ci.MS, S)
    loaded = mine | set(S.MSALL)
    S = dataclasses.replace(S, RS=S.RS & loaded, RU=S.RU & loaded, MS=S.MS & loaded)
    own = ly.Data()
    Sm = dataclasses.replace(S, RS=S.RS & mine, RU=S.RU & mine, MS=S.MS & mine)
    ly.base_year_data(own, copy.deepcopy(ci.capreg), Sm)
    D = copy.deepcopy(ci.others_bas)
    for (t, c, w), dd in own.c.items():
        for r, v in dd.items():
            D.set(r, c, w, t, v)
    ly.year_data(D, copy.deepcopy(ci.trends), S)
    tf = {k: v for k, v in ci.p_technFact.items() if k[0] in mine}
    csd.p_technFact_without_data(tf, D, S)
    exo = csd.create_sim_ini_gdx_data(D, S)
    return D, S, mine, exo, tf


def req_state(D: ly.Data, ci: ChainInputs, regions: set, P: dict, p_technFact: dict) -> tuple:
    """The requirement call's state at "Y" (feed/req_or_man_fnc.gms req, capmod/load_feed.gms l. 48-49) on the year's
    data of the regions and the technologies' factors p_technFact (year_data's): (state, DATA at "TRD" of the levels
    and the gross production)."""
    aact, mcact = tuple(capri_set("AACT")), tuple(capri_set("MCACT"))
    cols = set(aact) | set(OTHER_COLS) | set(mcact)
    MS = frozenset(capri_set("MS"))
    data, bas, trd, trd_days = {}, {}, {}, {}
    for (t, c, w), dd in D.c.items():
        if c not in cols:
            continue
        for r, v in dd.items():
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
    tf = {k: v for k, v in p_technFact.items() if k[0] in regions and k[1] in aact}
    r_ms = {a: b for a, b in capri_pairs("R_RAGG") if b in MS}
    feed_q = {(m, f): v for (m, c, f), v in bas.items() if c == "GROF" and m in MS and f in rq.FEED}
    st = rq.ReqState(DATA=data, RS=tuple(r for r in capri_set("RS") if r in regions), MS=MS, R_RAGG_MS=r_ms,
                     GRSACT=tuple(capri_set("GRSACT")), RUMI=tuple(capri_set("RUMI")), AACT=aact,
                     p_LUUnits=P["p_LUUnits"], p_technFact=tf,
                     p_rcEmissions={k: v for k, v in ci.p_rcEmissions.items() if k[0] in regions},
                     p_feedQuant=feed_q, p_carcassShare=P["p_carcassShare"], p_startWgt=P["p_startWgt"],
                     p_reqfcnlim=P["p_reqfcnlim"], p_coeffEnergyForGrowth=P["p_coeffEnergyForGrowth"],
                     p_convFactEnergyUnitsToEnne=P["p_convFactEnergyUnitsToEnne"],
                     p_NutContFeedRef=P["p_NutContFeedRef"], p_pigsReqLowWgt=P["p_pigsReqLowWgt"],
                     p_pigsReqHighWgt=P["p_pigsReqHighWgt"], DATA_BAS=bas, MAACT=tuple(capri_set("MAACT")),
                     MCACT=mcact, FEED_TO_O=frozenset(capri_pairs("FEED_TO_O")),
                     PACT_TO_O=frozenset(capri_pairs("PACT_TO_O")))
    return st, trd


def def_requirements_inputs(st: rq.ReqState, ci: ChainInputs, regions: set, trd: dict) -> dr.DefReqInputs:
    """def_requirements.gms' inputs: CAPREG's corrections of the regions (load_feed.gms l. 56-60)."""
    return dr.DefReqInputs(RU=tuple(r for r in capri_set("RU") if r in regions), MPACT=tuple(capri_set("MPACT")),
                           PACT_TO_Y=frozenset(capri_pairs("PACT_TO_Y")), DATA_BAS=st.DATA_BAS,
                           p_animReqCorrFac={k: v for k, v in ci.p_animReqCorrFac.items() if k[0] in regions},
                           SIMY=ci.SIMY, BAS=ci.BAS, FODDO=tuple(capri_set("FODDO")), DATA_TRD=trd)


def fedtrm_state(ms: str, st: rq.ReqState, D: ly.Data, regions: set, RU: set, p_technFact: dict,
                 p_exoDemand: dict) -> fp.FedtrmState:
    """The baseline feed calibration's state of the member state ms (CAPRI's code, DK000000) after def_requirements:
    its regions (ms and MAP_RR(ms, region)), DATA at "Y", "TRD" and "BAS", the activities' levels v_actLevl =
    LEVL x p_technFact (create_sim_ini_gdx.gms l. 419), the technologies' shares (the animals' of the requirement
    call, the other activities' CAPREG's), the requirements, days, shares and contents of def_requirements, and
    p_exoDemand."""
    mr = capri_pairs("MAP_RR")
    regs = {ms} | {b for a, b in mr if a == ms}
    DATA, TRD, BAS = {}, {}, {}
    for (t, c, w), dd in D.c.items():
        tgt = {"Y": DATA, "TRD": TRD, "BAS": BAS}.get(t)
        if tgt is None:
            continue
        for r, v in dd.items():
            if r in regions:
                tgt[(r, c, w)] = v
    maact = set(st.MAACT)
    tf = {k: v for k, v in st.p_technFact.items() if k[0] in regs and k[2] == "LEVL"}
    tf.update({k: v for k, v in p_technFact.items() if k[0] in regs and k[2] == "LEVL" and k[1] not in maact})
    srn1, srn2 = set(capri_set("SRNUTS1")), set(capri_set("SRNUTS2"))
    act = {}
    for r in regs:
        for a in capri_set("MPACT"):
            for t in capri_set("A"):
                v = DATA.get((r, a, "LEVL"), 0.0) * tf.get((r, a, "LEVL", t), 0.0)
                if v:
                    act[(r, a, t)] = v
    s = fp.FedtrmState(MS=ms, RU=tuple(sorted(r for r in regs if r in RU)),
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
    s.p_exoDemand = {k: v for k, v in p_exoDemand.items() if k[0] in regions}
    return s


def baseline_calibration(s: fp.FedtrmState, log: list) -> dict:
    r"""The baseline feed calibration of def_fert_and_requirements.gms l. 30-34 on its state: fedtrm_prep.gms,
    fedtrm_prior_pw.gms, fedtrm_cal_pw.gms, then fedtrm_fin.gms l. 36-48. Returns the corrections p_animReqCorrFac.

    fedtrm_fin.gms l. 36-37 kill NUTS1 and then take elements out of it, so the set is empty and l. 39-43 empty
    nothing: NUTS1_emptied runs on the empty set, as in CAPRI."""
    fp.fedtrm_prep(s)
    pp.fedtrm_prior_pw(s)
    cal.fedtrm_cal_pw(s, log)
    fin.NUTS1_emptied((), s.DATA, s.p_animReq, s.p_technFact, s.MAACT)
    rs = tuple(sorted({k[0] for k in s.v_animReq.L}))
    return fin.p_animReqCorrFac(rs, s.MAACT, s.p_animReq, s.v_animReq.L)


def simulation_start(st: rq.ReqState, d: dr.DefReqInputs, ms: str, corr: dict, fic: dict) -> tuple:
    """The simulation's start (create_sim_ini_gdx.gms l. 421-461, %BASELINE% off) on the requirement call's state
    before def_requirements: def_requirements, adjust.gms with the calibration's corrections corr and feed input
    coefficients fic (the baseline's v_feedInpCoeff, mefed_<...>.gdx), the shares, the feeds' rows, the days. Returns
    (adjust's inputs, SimIniInputs); st and d are changed in place."""
    a = adj.AdjustInputs(RU=d.RU, p_animReqCorrFac1=corr, p_animExcrProtCorrFact_Y={}, p_feedInpCoeffLoad=dict(fic),
                         DATA_TRD=d.DATA_TRD)
    si = csi.SimIniInputs(MS=(ms,), MAP_RR=frozenset(capri_pairs("MAP_RR")),
                          DATA_BAS_GROF={(r, f): v for (r, c, f), v in st.DATA_BAS.items() if c == "GROF" and r == ms})
    csi.create_sim_ini_gdx_feed(st, d, a, si)
    return a, si


def feed_chain(ci: ChainInputs, log: list | None = None) -> ChainResult:
    """CAPRI's chain for the member state (module docstring)."""
    log = [] if log is None else log
    P = req_or_man_params()
    D, S, mine, exo, tf = year_data(ci)
    ms = next(r for r in mine if r in S.MS)
    st, trd = req_state(D, ci, mine, P, tf)
    st0, trd0 = copy.deepcopy(st), copy.deepcopy(trd)
    d = def_requirements_inputs(st, ci, mine, trd)
    dr.def_requirements(st, d)
    s = fedtrm_state(ms, st, D, mine, set(d.RU), tf, exo)
    corr = baseline_calibration(s, log)
    d0 = def_requirements_inputs(st0, ci, mine, trd0)
    a, si = simulation_start(st0, d0, ms, corr, s.v_feedInpCoeff.L)
    return ChainResult(D=D, S=S, regions=mine, p_exoDemand=exo, cal=s, log=log, p_animReqCorrFac=corr, st=st0, d=d0,
                       a=a, si=si)
