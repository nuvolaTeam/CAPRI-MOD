"""capri-mod's own PMP terms, computed with CAPRI's recipe (supply/define_pmp_terms.gms and supply/pmp_terms/*), for a
calibration year (K61; the project lead's request of 22 October 2026: "we need our own calibration").

CAPRI star 3.0 derives its PMP terms from its econometric estimates (dat/estnlp/results.gdx, estimated around 2004) and
the calibration point's data. Steps ported here, per CAPRI region, with p_infl = 1.019 (gams/captrd.gms):

 1. group terms (forecast_group_pmp_matrix_from_estimates.gms): VB(g, g1) x sqrt(L_BAS(g)/L_Y(g) x L_BAS(g1)/L_Y(g1))
    x p_infl^(CALYEA - 2004) (CAL_YEAR below); a missing diagonal = 1/10 x rent(ARAB) / L_Y(g) where other groups have one; symmetric;
    a pair with |VB(g,g1)| >= sqrt(VB(g,g) VB(g1,g1)) raises both diagonals by 1%; stored upper-triangular in CAPRI's
    group order (CERE, CER2, OILS, OARA, FARA);
 2. activity slopes (forecast_activity_slopes.gms): VD(act) x L_BAS/L_Y x p_infl^(Y - 2004) where estimated; else
    1 / elasticity x max(revenue, costs + rent, rent) / L_Y with elasticity = CAPRI's estimate PELA(act, act, 2004) or
    CAPRI's assumed elasticity (supply/pmp_elas.gms), above 4.5 dampened to min(8, sqrt(e) + 2.5);
 2b. land-nest adjustment (forecast_activity_slopes.gms l. 103-141, crops other than grass): with M = max(revenue,
    costs + rent, rent), the slope's myopic elasticity e_b = M / (slope x L_Y) and c = p_landNestElasContrib,
    slope := slope + (1/e_b - 1/(e_b + c)) x M / L_Y. c (supply/cal_land_nests.gms l. 729, trustee land market):
    L_Y(act) / sum of the levels of the agricultural land types the activity belongs to (landTypes_to_pact over
    landTypesAgr: ARAB, ANNC, ARAC for annual crops; ARAB, ARAC for OCRO; ARAB, FRUN for permanent crops) x the sum
    of those land types' posterior own-rent elasticities, which exist for the market land types only (ARAC, FRUN).
    The posterior elasticity is the land supply calibration's (declare_calibration_models_for_land_supply.gms):
    dlevl/drent = -[inverse of the bordered Hessian ((-Q x p_landMarketScale, -1), (-1, 0))] on the land types with
    land, Q = CAPRI's p_pmpQuadLandTypes, p_landMarketScale = 1000; elasticity = dlevl_i/drent_i x d_area_i / levl_i;
 3. technology matrix (compute_technology_pmp_matrix.gms) for the crops CAPRI splits into T1 / T2 (equal shares):
    the fit's solution, Q(T1,T1) = Q(T2,T2) = a, Q(T1,T2) = b, a + b = slope, a + own = 2 (b + own) (own = the crop
    group's diagonal term), i.e. b = (slope - own) / 3; one technology T: Q(T,T) = slope;
 4. upper bound on the elasticity (impose_upper_bound_on_elasticity.gms): where revenue / (L x tf x share term x
    (Q(A,A) + own)) > 4.5, Q(A,A) = revenue / (L x tf x share term x min(8, sqrt(e) + 4.5 - sqrt(4.5))).

Data of the calibration point: L_BAS = CAPRI's 2017 levels (res_17 LEVL), L_Y the year's levels (2030: CAPRI's 2030
reference, the model's trajectory; 2017: L_BAS); revenue = TOOU, costs = TOIN of the same sources; rent = the land
type's rent (capri_data/2017/supply/land_rents_2030.csv at 2030; D_AREA of res_17 at 2017).

REGISTERED differences from CAPRI's recipe, measured against CAPRI's exported 2030 terms by
tools/check/pmp_recipe_check.py: (a) the land-nest adjustment's land-type elasticities are recomputed from CAPRI's exported
land matrix (2030: pmp_quad_landtypes_2030.csv; 2017: capri_data/sources/capreg/pmp_quad_landtypes_2017.csv), levels
and rents, not read from CAPRI's estimation (v_posterior_elasticity is not exported; the estimation makes it an exact
function of the same matrix); (b) revenue per technology is the
activity's TOOU x (1 + CAPRI's technology factor, +-20%; intens/techf.gms) - CAPRI: outputs x (1 + factor) x unit
values (until 23 October 2026 the factor was left out, so CAPRI's elasticity cap bound on T1 where the recipe's did not:
the 0.84-0.88 ratios in the estimated crops); (c) costs + rent stand in
for CAPRI's |linear objective contribution|.

Output (CAPRI codes, the format of tools/build/build_pmp_2030.py): capri_data/sources/baseline_pmp/recipe_<Y>_quad_techn.csv,
recipe_<Y>_quad_pact.csv

    python tools/build/build_pmp_recipe.py --year 2030|2017
"""
from __future__ import annotations
import argparse, glob, math, re, subprocess
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "baseline_pmp"
REF = Path("/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv")
DUMPS = Path("/home/claude/work/capreg")
PELA = Path("/home/claude/work/up/pmp2030/estnlp_results_PELA.txt")
P_INFL, EST_YEAR = 1.019, 2004
#: CAPRI's technology factors of the outputs (intens/techf.gms l. 84-85): T1 yields 20% above the mean, T2 20% below
TECH_YIELD_FACTOR = {"T1": 0.2, "T2": -0.2}
#: CALYEA of the calibration's simulation year in p_pmpInflationFactor = p_infl**(CALYEA(simulationYear) - 2004)
#: (define_pmp_terms.gms l. 38). 2030: 2030. Base year 2017: 2018, inferred from CAPRI's own CAPREG terms, not from
#: the code (simulationYear is set by the GUI): with 14 years of inflation the recipe's 2017 group terms match CAPRI's
#: within 1% in 100% of 1447 pairs, with 13 years in 3% (all off by 1/1.019); the estimated activity slopes the same.
CAL_YEAR = {2017: 2018, 2030: 2030}
GRP = {"SWHE": "CERE", "DWHE": "CERE", "RYEM": "CERE", "BARL": "CERE", "OATS": "CERE", "MAIZ": "CER2", "OCER": "CER2",
       "PARI": "CER2", "RAPE": "OILS", "SUNF": "OILS", "SOYA": "OILS", "PULS": "OARA", "POTA": "OARA", "SUGB": "OARA",
       "MAIF": "FARA", "ROOF": "FARA", "OFAR": "FARA"}
ORD = ["CERE", "CER2", "OILS", "OARA", "FARA"]
#: CAPRI's assumed own supply elasticities (supply/pmp_elas.gms; every other activity 1)
ASSUMED = {"MAIF": 4.0, "GRAE": 3.0, "GRAI": 3.0, "ISET": 20.0, "PARI": 0.2, "TEXT": 0.2, "TOBA": 0.2, "OLIV": 0.1,
           "FALL": 0.5, "VSET": 10.0, "TOMA": 0.3, "OVEG": 0.3, "APPL": 0.1, "CITR": 0.1, "OFRU": 0.1, "TAGR": 0.1,
           "TABO": 0.1, "TWIN": 0.1, "DCOH": 0.4, "DCOL": 0.4, "SHGM": 0.6, "SHGF": 0.7}
#: activities CAPRI splits into two technologies (TACT, as in its 2030 export)
TACT = {"APPL", "BARL", "CITR", "DWHE", "FALL", "MAIF", "MAIZ", "OATS", "OCER", "OFAR", "OFRU", "OLIV", "OVEG", "PARI",
        "POTA", "PULS", "RAPE", "ROOF", "RYEM", "SOYA", "SUGB", "SUNF", "SWHE", "TABO", "TAGR", "TEXT", "TOBA", "TOMA",
        "TWIN", "VSET"} - {"FALL"}
#: fallow: CAPRI's premium-eligible variant T1 alone carries a term, T2 is fixed (policy/calc_mtr.gms)
ONE_T1 = {"FALL"}
#: activities whose product is a quota product (PACT_TO_Y with QP = COMI, SUGB)
QUOTA_ACTS = {"SUGB", "DCOL", "DCOH"}
ANIMALS = {"DCOL", "DCOH", "SCOW", "BULL", "BULH", "HEIL", "HEIH", "HEIR", "CAMF", "CAFF", "CAMR", "CAFR", "SOWS", "PIGF",
           "HENS", "POUF", "SHGM", "SHGF", "OANI"}
PERMANENT = {"APPL", "OFRU", "CITR", "TAGR", "TWIN", "OLIV", "TABO", "NURS"}
GRASS = {"GRAE", "GRAI"}
#: CAPRI's landTypes_to_pact over landTypesAgr (supply/def_supply_model_par.gms l. 106-111; sets.gms l. 2944-2990):
#: annual crops (sets.gms annualCrops) belong to ARAB, ANNC and ARAC; OCRO to ARAB and ARAC; the permanent crops
#: (cropC_to_landAgg ... FRUN) to ARAB and FRUN
ANNUAL = {"SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER", "PARI", "RAPE", "SUNF", "SOYA", "PULS", "POTA",
          "SUGB", "TEXT", "TOBA", "TOMA", "OVEG", "FALL", "OOIL", "OIND", "FLOW", "ISET", "GSET", "TSET", "VSET", "MAIF",
          "ROOF", "OFAR"}
FRUN_ACTS = {"TWIN", "CITR", "OFRU", "TAGR", "TABO", "OLIV", "APPL", "NURS", "NECR"}
LAND_MRK = ["GRAS", "ARAC", "FRUN", "FORE", "ARTIF", "OLND"]
LAND_SCALE = 1000.0          # p_landMarketScale (supply/def_supply_model_par.gms l. 61)
ACTS = sorted(set(GRP) | set(ASSUMED) | TACT | ANIMALS | {"OOIL", "OIND", "OCRO", "FLOW", "NECR", "TOMA"})


def _damp(e: float) -> float:
    return min(8.0, math.sqrt(e) + 2.5) if e > 4.5 else e


#: CAPRI's outputs of each activity (sets.gms PACT_TO_O l. 5187-5262), for its revenue per technology (prep_cal.gms
#: p_revenues); the model's codes as CAPRI's
PACT_TO_O = {**{a: (a, "STRA", "MANN", "MANP", "MANK") for a in ("SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER",
                                                                    "PARI")},
             **{a: (a, "MANN", "MANP", "MANK") for a in ("PULS", "POTA", "SUGB", "RAPE", "SUNF", "SOYA", "OLIV", "OOIL",
                                                          "TOBA", "OIND", "TOMA", "OVEG", "APPL", "OFRU", "CITR", "TAGR",
                                                          "TABO", "TWIN", "NURS", "FLOW", "OCRO", "MAIF", "ROOF", "OFAR")},
             "TEXT": ("TEXT", "OOIL", "MANN", "MANP", "MANK"), "NECR": ("OCRO", "MANN", "MANP", "MANK"),
             "DCOL": ("COMI", "COMF", "BEEF", "YCAM", "YCAF", "MANN", "MANP", "MANK"),
             "DCOH": ("COMI", "COMF", "BEEF", "YCAM", "YCAF", "MANN", "MANP", "MANK"),
             "SCOW": ("COMF", "BEEF", "YCAM", "YCAF", "MANN", "MANP", "MANK"),
             **{a: ("BEEF", "MANN", "MANP", "MANK") for a in ("BULL", "BULH", "CAMF", "CAFF", "HEIL", "HEIH")},
             "PIGF": ("PORK", "MANN", "MANP", "MANK"), "SHGM": ("SGMI", "SGMF", "SGMT", "YLAM", "MANN", "MANP", "MANK"),
             "SHGF": ("SGMT", "MANN", "MANP", "MANK"), "HENS": ("EGGS", "YCHI", "POUM", "MANN", "MANP", "MANK"),
             "POUF": ("POUM", "MANN", "MANP", "MANK"), "OANI": ("OANI",),
             **{a: ("GRAS", "MANN", "MANP", "MANK") for a in ("GRAE", "GRAI", "GSET")},
             "CAMR": ("YBUL", "MANN", "MANP", "MANK"), "CAFR": ("YHEI", "MANN", "MANP", "MANK"),
             "HEIR": ("YCOW", "MANN", "MANP", "MANK"), "SOWS": ("YPIG", "PORK", "MANN", "MANP", "MANK"),
             **{a: ("MANN", "MANP", "MANK") for a in ("FALL", "VSET", "OSET")}}
#: the yield-dependent inputs in CAPRI's linear objective (sets.gms IobjCont = IY: inputs not produced in the sector -
#: not fertiliser, feed or young animals - without water, ICHI and mitiI; CIREST and IGEN, IPHA)
#: Plant protection is not among them in CAPRI's runs (PEST_DISAGG on: sets.gms CIREST l. 3344-3346 leaves PLAP out; the
#: pesticide model prices it). Checked: |D_OBJC| in CAPRI's 2017 results = these inputs x UVAP without PLAP (DE12 barley
#: 381.3, soybeans 640.0, fodder roots 864.0)
IY = ("CAOF", "SEED", "REPM", "REPB", "ELEC", "EGAS", "EFUL", "ELUB", "IRRO", "WATR", "INPO", "SERI", "IPHA")
#: CAPRI's technology factors of the inputs (intens/techf.gms l. 92-99): +-25%, plant protection +-40%, water 0
TECH_INPUT_FACTOR = {"T1": 0.25, "T2": -0.25}
TECH_INPUT_SPECIAL = {"PLAP": {"T1": 0.40, "T2": -0.40}, "WATR": {"T1": 0.0, "T2": 0.0}}


def levels_2017() -> dict:
    """CAPRI's 2017 results per region (res_17 dumps, 'Y'): every item of the activities and land rows, and the member
    states' unit values of outputs (UVAG) and inputs (UVAP), keyed (column, row)."""
    out = defaultdict(dict)
    rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Z0-9_]+)'\.'([A-Z0-9_]+)'\.'Y'\s+([-\d.Ee+]+)")
    for f in glob.glob(str(DUMPS / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = rx.match(line)
            if m:
                try:
                    v = float(m.group(4))
                except ValueError:                 # GAMS Eps
                    v = 0.0
                out[m.group(1)].setdefault((m.group(2), m.group(3)), v)
    return out


def levels_ref(year: int) -> dict:
    """CAPRI's 2030 reference results (dataOut, '{year}'): every item of the regions' activity and land rows and the
    member states' unit values (UVAG, UVAP), keyed (column, row)."""
    pat = rf"^'[A-Z]{{2}}[0-9A-Z]{{6}}'\.''\.'[A-Z0-9_]+'\.'[A-Z0-9_]+'\.'{year}'"
    txt = subprocess.run(["grep", "-E", pat, str(REF)], capture_output=True, text=True).stdout
    rx = re.compile(rf"^'([A-Z]{{2}}[0-9A-Z]{{6}})'\.''\.'([A-Z0-9_]+)'\.'([A-Z0-9_]+)'\.'{year}'\s+(\S+?),?\s*$")
    out = defaultdict(dict)
    for line in txt.splitlines():
        m = rx.match(line)
        if m:
            try:
                v = float(m.group(4))
            except ValueError:                     # GAMS Eps
                v = 0.0
            out[m.group(1)][(m.group(2), m.group(3))] = v
    return out


SIMINI = SRC / "simini_21730_data.csv"


def calibration_point_2030(ydat: dict, bas: dict) -> None:
    """CAPRI's own 2030 calibration point, in place: DATA(..., "Y") of sim_ini_21730.gdx (the simulation start file of
    the 2030 baseline, provided by the project lead 23 October 2026; its p_pmpQuadTechn equals the exported 2030 terms
    in all 28,169 entries), extracted to simini_21730_data.csv. Every activity item and the member states' unit values
    (UVAG, UVAP) replace the results' values; the land rows (ARAB, ARAC, FRUN, their D_AREA), which the file does not
    carry at "Y", stay those of CAPRI's 2030 results. The activities' L_BAS: DATA(..., "LEVL", "BAS") of the file."""
    if not SIMINI.exists():
        raise FileNotFoundError(f"{SIMINI} is missing (CAPRI's 2030 calibration point, sim_ini_21730.gdx)")
    t = _read_csv(SIMINI)
    for r in t.itertuples(index=False):
        if r.year == "Y":
            ydat.setdefault(r.region, {})[(r.col, r.row)] = float(r.value)
        elif r.year == "BAS" and r.row == "LEVL":
            bas.setdefault(r.region, {})[(r.col, "LEVL")] = float(r.value)


def pela_2004() -> dict:
    out = {}
    rx = re.compile(r"^'([A-Z0-9]{8})'\.'([A-Z]+)'\.'\2'\.'2004'\s+([-\d.Ee+]+)")
    if PELA.exists():
        for line in open(PELA, errors="ignore"):
            m = rx.match(line)
            if m:
                out[(m.group(1), m.group(2))] = float(m.group(3))
    return out


_RENTS = {}


def rents(year: int, dat: dict, region: str) -> dict:
    """Rent per land type (ARAC, FRUN, GRAS), EUR/ha, positive: CAPRI's calibration rents per CAPRI region
    (tools/build/build_land_rents.py --year: the reported D_AREA, CAPRI's rule of cal_land_nests.gms l. 204-226 where it is
    not positive; before 23 October 2026 non-positive cells were left out here, and 2017 grassland had none)."""
    if year not in _RENTS:
        f = ROOT / "capri_data" / "sources" / "capri_land_rents" / f"land_rents_capri_{year}.csv"
        tab = defaultdict(dict)
        for r in _read_csv(f).itertuples():
            tab[r.capri_region][r.land_type] = float(r.rent_eur_ha)
        _RENTS[year] = tab
    return dict(_RENTS[year].get(region, {}))


def land_quad(year: int) -> dict:
    """CAPRI's p_pmpQuadLandTypes per CAPRI region at the calibration point."""
    f = (SRC / "pmp_quad_landtypes_2030.csv" if year == 2030
         else ROOT / "capri_data" / "sources" / "capreg" / "pmp_quad_landtypes_2017.csv")
    out = defaultdict(dict)
    for r in _read_csv(f).itertuples():
        out[r.region][(r.landtype1, r.landtype2)] = float(r.value)
    return out


def land_elasticities(Q: dict, ydat: dict) -> dict:
    """Own-rent elasticities of CAPRI's market land types (v_posterior_elasticity(lt, lt)), from the bordered Hessian
    of the land owner's problem (declare_calibration_models_for_land_supply.gms: e_Hes, e_iHes, e_dlevl_dr,
    e_posterior_elasticity), on the land types with land and a matrix row."""
    import numpy as np
    lts = [t for t in LAND_MRK if float(ydat.get((t, "LEVL"), 0.0) or 0.0) > 0 and Q.get((t, t), 0.0) > 0]
    n = len(lts)
    if n == 0:
        return {}
    H = np.zeros((n + 1, n + 1))
    for i, a in enumerate(lts):
        for j, b in enumerate(lts):
            H[i, j] = -Q.get((a, b), Q.get((b, a), 0.0)) * LAND_SCALE
        H[i, n] = H[n, i] = -1.0
    try:
        iH = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        return {}
    out = {}
    for i, a in enumerate(lts):
        rent = abs(float(ydat.get((a, "D_AREA"), 0.0) or 0.0))
        out[a] = -iH[i, i] * rent / float(ydat[(a, "LEVL")])
    return out


def land_nest_contrib(a: str, ydat: dict, ela: dict) -> float:
    """p_landNestElasContrib(act) (supply/cal_land_nests.gms l. 729, trustee land market)."""
    L = lambda x: float(ydat.get((x, "LEVL"), 0.0) or 0.0)
    if a in GRASS or a in ANIMALS:
        return 0.0
    annc = L("ANNC") or sum(L(x) for x in ANNUAL)
    lv = {"ARAB": L("ARAB"), "ANNC": annc, "ARAC": L("ARAC"), "FRUN": L("FRUN")}
    types = ["ARAB"] + (["FRUN"] if a in FRUN_ACTS else (["ANNC", "ARAC"] if a in ANNUAL else ["ARAC"]))
    den = sum(lv[t] for t in types)
    if den <= 0:
        return 0.0
    return L(a) / den * sum(ela.get(t, 0.0) for t in types)


def _tech(a: str):
    """[(technology, area share)] of an activity (intens/techf.gms: TACT 50/50; fallow's T1 alone carries a term)."""
    if a in TACT:
        return [("T1", 0.5), ("T2", 0.5)]
    return [("T1", 1.0)] if a in ONE_T1 else [("T", 1.0)]


def revenue_cost(a: str, ydat: dict, msdat: dict) -> dict:
    """{technology: (revenue, cost)} per unit of the activity, EUR: CAPRI's p_revenues (prep_cal.gms l. 166-170: each
    output x (1 + p_technFact(O, A)) x the member state's UVAG x 0.001) and its linear objective's costs
    (capmod/define_objc.gms l. 42-44: each yield-dependent input x (1 + p_technFact(I, A)) x the member state's UVAP x
    0.001; UVAG where the data has no UVAP). Missing outputs or inputs count zero."""
    out = {}
    for A, _ in _tech(a):
        fo = TECH_YIELD_FACTOR.get(A, 0.0) if a in TACT else 0.0
        rev = sum(float(ydat.get((a, o), 0.0) or 0.0) * (1.0 + fo) * float(msdat.get(("UVAG", o), 0.0) or 0.0)
                  for o in PACT_TO_O.get(a, (a,))) * 0.001
        cost = 0.0
        for i in IY:
            q_ = float(ydat.get((a, i), 0.0) or 0.0)
            if not q_:
                continue
            fi = (TECH_INPUT_SPECIAL.get(i, TECH_INPUT_FACTOR).get(A, 0.0)) if a in TACT else 0.0
            pr = msdat.get(("UVAP", i))
            pr = float(pr if pr is not None else msdat.get(("UVAG", i), 0.0) or 0.0)
            cost += q_ * (1.0 + fi) * pr * 0.001
        out[A] = (rev, cost)
    return out


def region_terms(c: str, Y: int, bas: dict, ydat: dict, vb: dict, vd: dict, pela: dict, lq: dict | None = None,
                 land_nest: bool = True, msdat: dict | None = None):
    """(techn rows, pact rows) of one CAPRI region."""
    msdat = msdat or {}
    L = lambda a: float(ydat.get((a, "LEVL"), 0.0) or 0.0)
    Lb = lambda a: float(bas.get((a, "LEVL"), 0.0) or 0.0)
    infl = P_INFL ** (CAL_YEAR[Y] - EST_YEAR)
    rent = rents(Y, ydat, c)
    # DATA(ARAB, "d_area", "Y"): CAPRI's arable rent (its results report the land balance's dual, D_AREA, with the
    # opposite sign); else the arable land type's rent
    _da = ydat.get(("ARAB", "D_AREA"))
    arab_rent = abs(float(_da)) if _da is not None and abs(float(_da)) > 0 else rent.get("ARAC", 0.0)
    # 1. group terms
    LY = {g: sum(L(a) for a in GRP if GRP[a] == g) for g in ORD}
    LB = {g: sum(Lb(a) for a in GRP if GRP[a] == g) for g in ORD}
    P = {}
    for (g, g1), v in vb.get(c, {}).items():
        if LY.get(g, 0) > 0 and LY.get(g1, 0) > 0 and LB.get(g, 0) > 0 and LB.get(g1, 0) > 0:
            P[(g, g1)] = v * math.sqrt(LB[g] / LY[g] * LB[g1] / LY[g1]) * infl
    if any(P.get((g, g), 0) for g in ORD):
        for g in ORD:
            if not P.get((g, g)) and LY.get(g, 0) > 0:
                P[(g, g)] = 0.1 * arab_rent / LY[g]
    for (g, g1) in list(P):
        if g != g1 and (g1, g) not in P:
            P[(g1, g)] = P[(g, g1)]
    P = {(g, g1): v for (g, g1), v in P.items() if ORD.index(g) <= ORD.index(g1)}
    bad = [(g, g1) for (g, g1), v in P.items() if g != g1 and abs(v) >= math.sqrt(max(P.get((g, g), 0), 0) * max(P.get((g1, g1), 0), 0))]
    for g, g1 in bad:
        P[(g, g)] = P.get((g, g), 0) * 1.01
        P[(g1, g1)] = P.get((g1, g1), 0) * 1.01
    # 2.-4. activities
    # the share term's denominators: CAPRI's DATA(ARAB, "LEVL") and DATA(GRAS, "LEVL") of the calibration point
    # (impose_upper_bound_on_elasticity.gms); the sums of the activities where the data has no row
    arab_lev = L("ARAB") or (sum(L(a) for a in GRP) + sum(L(a) for a in ("TEXT", "TOBA", "OIND", "OCRO", "FLOW", "NURS",
                                                                           "TOMA", "OVEG", "OOIL", "VSET", "FALL", "NECR")))
    gras_lev = L("GRAS") or (L("GRAE") + L("GRAI"))
    ela = land_elasticities(lq or {}, ydat) if land_nest else {}
    rows = []
    for a in ACTS:
        La = L(a)
        if La <= 0:
            continue
        lt = "GRAS" if a in GRASS else ("FRUN" if a in PERMANENT else (None if a in ANIMALS else "ARAC"))
        # the land rent CAPRI subtracts in the linear objective (prep_cal.gms l. 127-142: the market land type's
        # d_area); the activity's own D_AREA in CAPRI's results is minus that rent (checked on 2017's grassland), else
        # the land type's rent
        _dact = ydat.get((a, "D_AREA"))
        if lt and _dact is not None and float(_dact) < 0:
            r_ = -float(_dact)
        else:
            r_ = rent.get(lt, 0.0) if lt else 0.0
        # the rent term of the fallback slope (forecast_activity_slopes.gms l. 88-97): DATA(ARAB, "d_area") for the
        # crops but grass, DATA(GRAS, "d_area") for grass, none for the animals
        r_slope = (rent.get("GRAS", 0.0) if a in GRASS else (0.0 if a in ANIMALS else arab_rent))
        rc = revenue_cost(a, ydat, msdat)
        if not any(v[0] or v[1] for v in rc.values()):
            rv = float(ydat.get((a, "TOOU"), 0.0) or 0.0)       # no outputs or inputs in the data: CAPRI's TOOU
            rc = {A: (rv, 0.0) for A in rc}
        rev = sum(rc[A][0] * sh for A, sh in _tech(a))          # the activity's mean revenue
        # MR = sum over technologies of the share x max(0, |p_linObjeCont|, rent, p_revenues) (l. 88-97), with
        # p_linObjeCont = - costs - the land rent
        p = sum(sh * max(0.0, rc[A][1] + r_, r_slope, rc[A][0]) for A, sh in _tech(a))
        # activities producing a quota product (QP = COMI, SUGB; sets.gms l. 5614) lose their estimates
        # (forecast_activity_slopes.gms l. 1-2: pact_to_y(qact, QP)) and take the assumed elasticity
        quota = a in QUOTA_ACTS
        if (c, a) in vd and Lb(a) > 0 and not quota:
            slope = vd[(c, a)] * Lb(a) / La * infl
        else:
            e = _damp(ASSUMED.get(a, 1.0) if quota else pela.get((c, a), ASSUMED.get(a, 1.0)))
            if p <= 0 or e <= 0:
                continue
            slope = p / (e * La)
        # 2b. land-nest adjustment (forecast_activity_slopes.gms l. 103-141; not grass)
        cn = land_nest_contrib(a, ydat, ela) if ela else 0.0
        if cn > 0 and p > 0 and slope > 0:
            eb = p / (slope * La)
            slope += (1.0 / eb - 1.0 / (eb + cn)) * p / La
        g = GRP.get(a)
        own = P.get((g, g), 0.0) if g else 0.0
        if a in GRASS:
            st = 1.0 - 0.2 * math.sqrt(La / gras_lev) if gras_lev > 0 else 1.0
        elif a not in ANIMALS and arab_lev > 0 and a not in PERMANENT:
            st = 1.0 - 0.2 * math.sqrt(min(La / arab_lev, 1.0))
        else:
            st = 1.0
        if a in TACT:
            b = (slope - own) / 3.0
            q = {("T1", "T1"): slope - b, ("T2", "T2"): slope - b, ("T1", "T2"): b, ("T2", "T1"): b}
            tf = 0.5
            for A in ("T1", "T2"):
                # each technology's own revenue (prep_cal.gms p_revenues: outputs x (1 + p_technFact(O, A)) x unit
                # values; intens/techf.gms: T1 +20%, T2 -20%, area shares 0.5 / 0.5)
                rev_a = rc[A][0]
                denom = La * tf * st * (q[(A, A)] + own)
                te = rev_a / denom if denom > 0 and rev_a > 0 else 0.0
                if te > 4.5:
                    q[(A, A)] = rev_a / (La * tf * st * min(8.0, math.sqrt(te) + 4.5 - math.sqrt(4.5)))
        else:
            tk = "T1" if a in ONE_T1 else "T"
            q = {(tk, tk): slope}
            rev_t = rc[tk][0] if tk in rc else rev
            denom = La * st * (slope + own)
            te = rev_t / denom if denom > 0 and rev_t > 0 else 0.0
            if te > 4.5:
                q[(tk, tk)] = rev_t / (La * st * min(8.0, math.sqrt(te) + 4.5 - math.sqrt(4.5)))
        rows += [(c, a, t1, t2, v) for (t1, t2), v in q.items()]
    return rows, [(c, g, g1, v) for (g, g1), v in P.items()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, choices=(2017, 2030), default=2030)
    ap.add_argument("--no-land-nest", action="store_true", help="leave out the land-nest adjustment (step 2b)")
    a = ap.parse_args()
    Y = a.year
    vb = defaultdict(dict)
    for r in _read_csv(SRC / "estnlp_vb.csv").itertuples():
        vb[r.region][(r.group1, r.group2)] = float(r.level)
    vd = {(r.region, r.activity): float(r.level) for r in _read_csv(SRC / "estnlp_vd.csv").itertuples()}
    pela = pela_2004()
    bas = levels_2017()
    ydat = levels_ref(Y) if Y == 2030 else bas
    # (CAPRI's 2030 calibration point from sim_ini_21730.gdx, calibration_point_2030, is not used: its DATA(..., "Y")
    # prices are not those of the 2030 calibration - barley 101 EUR/t against 166 in the results; terms built on them
    # matched CAPRI's in 31.6% of pairs, on the results' prices in the figures of PMP_CAPRI_2030.md)
    regions = sorted(c for c in ydat if not c.endswith("0000") or c.endswith("000000") is False)
    regions = sorted(c for c in set(ydat) if c[4:] == "0000" or c.endswith("000000"))
    lq = land_quad(Y)
    tech, pact = [], []
    for c in regions:
        t_, p_ = region_terms(c, Y, bas.get(c, {}), ydat.get(c, {}), vb, vd, pela, lq.get(c, {}), not a.no_land_nest,
                              ydat.get(c[:2] + "000000", {}))
        tech += t_
        pact += p_
    pd.DataFrame(tech, columns=["region", "activity", "tech1", "tech2", "value"]).to_csv(
        SRC / f"recipe_{Y}_quad_techn.csv", index=False)
    pd.DataFrame(pact, columns=["region", "group1", "group2", "value"]).to_csv(
        SRC / f"recipe_{Y}_quad_pact.csv", index=False)
    print(f"recipe {Y}: {len(tech)} technology terms, {len(pact)} group terms, {len({r[0] for r in tech})} CAPRI regions")


if __name__ == "__main__":
    main()
