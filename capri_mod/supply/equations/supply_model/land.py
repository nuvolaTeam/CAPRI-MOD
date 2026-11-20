r"""CAPRI's land block (supply/supply_model.gms l. 2358-2516): the land balances of the land types, the land market
and the land use change estimation (LUC, luc_supply on).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview and departures.

Written so far: the land balances' rows of the regional QP (RegionalSupplyModel._build_constraints: "arable_land",
"permanent_land", "grassland"). With Trustee_land on (CAPRI's 2030 Green Deal step), CAPRI's land types without a
slack are ARAC, FRUN and GRAS (sets.gms l. 3056-3057) and their balance is LandBalNoSlak_: the activities on a land
type equal the land type's level, a variable of the land market. The model's base QP writes the rows with the land
fixed at the data; the land market (supply/land.py _land_augment) makes the land a column.

A porting difference, kept by the move (for the main line; not a departure): the base rows' right-hand side is
max(the land data, the base area of the land type's activities) (LandBal_rhs), which keeps the base year feasible
where the land data and the crop areas come from different aggregations (54 of 248 regions for arable land, 56 for
permanent crops; supply_module's comments); CAPRI's right-hand side is the land type's level alone.

The land market (supply/land.py _land_augment): LandMarket_'s cost on the land types (LandMarket_quad, LandMarket_cnst),
LandBalNoSlak_ with the land as a column (LandBalNoSlak_landCol) and as an equality at the base use (LandBalNoSlak_baseUse),
e_artoBal's total land (e_artoBal) and the grassland floor (permGrasGreening_land). Porting differences, kept and listed:
the land market's Q is regularised (1e-9 I); LandBalNoSlak_ holds at the base use, not at the land data (the model's land
data carry idle land, CAPRI's do not), with tolerances of 1e-7 and 1e-9; the grassland floor duplicates permGrasGreening_
on the land column.

The land use change estimation (luc_supply on in the Green Deal step: supply_model.gms l. 80-82), solved after the
regional model (environmental/luc.py LUCModel.solve; without a price on LULUCF the block enters no other equation):
the classes from the land types (e_landTypes_to_LUclass), the adding-up rows (e_luClassInitial, e_luClassFinal) and
the posterior mode of the transitions under CAPRI's gamma priors (e_FocLUC with e_derivativeOfGammaLUC, p_lucPrior_gamma).
CAPRI's bounds are the problem's variable bounds: e_lowerBoundLUC 1e-8 for the gamma transitions, e_upperBoundLUC +inf
(supply/prep_sim_luc.gms l. 407-408); a transition with mode 0 is a spike at 0, left out of the problem (l. 341-342).
e_derivativeOfNormalLUC is empty in the step: no transition has a normal prior (prep_sim_luc.gms l. 337-370 assigns
gamma and spike densities only). A porting difference, kept: CAPRI also renders up to ten of the smallest transitions
(mode <= 1e-4 kha, keeping two non-spike per row and column) spike at their mode (l. 344-370); the model keeps them
gamma.
"""
from __future__ import annotations

import numpy as np


def LandBalNoSlak_(n, acts_idx, acts):
    r"""LandBalNoSlak_(r, landTypesNoSlak) (l. 2381-2385), its left-hand side: the activities on the land type
    (landTypes_to_pact), one per unit of their level; the row of the regional QP over its n columns (acts_idx: column
    of each activity; acts: the land type's activities).

    CAPRI's GAMS, LandBalNoSlak_ (l. 2381-2385):

        LandBalNoSlak_(RUNR,landTypesNoSlak)  ..
            SUM( (landTypes_to_pact(landTypesNoSlak,MPACT),A)  $ p_technFact(RUNR,MPACT,"LEVL",A),
                           v_actLevl(RUNR,MPACT,A)) =E= v_actLevl(RUNR,landTypesNoSlak,"T")     ;
    """
    row = np.zeros(n)
    for a in acts:
        if a in acts_idx:
            row[acts_idx[a]] = 1.0
    return row


def LandBal_rhs(land, base_use):
    r"""The base QP's right-hand side of a land balance: max(the land type's data level, the base area of its
    activities). A porting difference (the module's docstring): CAPRI's LandBalNoSlak_ has the land type's level, and
    in its fixed-land form, LandBalSlak_ (l. 2364-2377), the data level with a slack:

         LandBalSlak_(RUNR,landTypesSlak)  $ ((not sameas(landTypesSlak,"ANNC")) or (p_landIsFixed eq 0)) ..
            SUM( (landTypes_to_pact(landTypesSlak,MPACT),A)  $ p_technFact(RUNR,MPACT,"LEVL",A),
                v_actLevl(RUNR,MPACT,A))
              + v_landbalslak(RUNR,landTypesSlak)
            =e=  %data%(RUNR,landTypesSlak,"LEVL","Y") $ (p_landIsFixed eq 1)
               + v_actLevl(RUNR,landTypesSlak,"T")     $ (p_landIsFixed eq 0);
    """
    return max(land, base_use)


def LandMarket_quad(p_pmpQuadLandTypes, keep):
    r"""LandMarket_'s quadratic term (l. 4830-4841, Trustee_land on), the land market's cost 0.5 L'QL over the model's
    land types (keep: their positions in the data's order): Q = 1000 x the symmetric part of p_pmpQuadLandTypes (CAPRI's
    terms per ha, the model's land in 1000 ha) + 1e-9 x I (a regularisation; not in CAPRI).

    CAPRI's GAMS, LandMarket_ (l. 4830-4841):

        LandMarket_(RUNR) $ (p_landIsFixed eq 0)..
            v_pmpCostLandMarket(RUNR)
    $iftheni.tru1 %Trustee_land%==ON
                           =E= SUM[ LandTypesMrk $ %data%(runr,landTypesMrk,"levl","y"),
                                    p_pmpCnstLandTypes(runr,LandtypesMrk)*v_actLevl(runr,LandtypesMrk,"T")
                                  + 0.5*sum(landTypesMrk1, p_pmpQuadLandTypes(runr,LandtypesMrk,LandtypesMrk1)
                                                          *v_actLevl(runr,LandtypesMrk,"T")*v_actLevl(runr,LandtypesMrk1,"T"))];
    """
    Qf = np.array(p_pmpQuadLandTypes, dtype=float)[np.ix_(keep, keep)]
    return 1000.0 * 0.5 * (Qf + Qf.T) + 1e-9 * np.eye(len(keep))


def LandMarket_cnst(Q, L0):
    """LandMarket_'s linear term, p_pmpCnstLandTypes, at the calibration point before the land rents: -Q L0, so that the
    base land is optimal (the rents are added by the builder, CAPRI's cal_land_nests.gms). CAPRI's GAMS:
    LandMarket_quad's docstring."""
    return -Q @ L0


def LandBalNoSlak_landCol(b_row, coeffs, L0):
    """LandBalNoSlak_ (l. 2381-2385) with the land type as a column of the land market: activities - land <= the base
    limit - the base land; returns that right-hand side, b_row - sum_j coef_j L0_j (the builder subtracts the
    coefficients in the land columns). CAPRI's GAMS: LandBalNoSlak_'s docstring."""
    return float(b_row) - sum(cf * L0[j] for j, cf in coeffs)


def LandBalNoSlak_baseUse(row, const, xb, n, k):
    """LandBalNoSlak_ as an equality at the base use, as a pair of rows (l. 2381-2385): used = min(the row at the base
    point, its limit); the upper row's right-hand side used + 1e-7 max(1, |used|) + 1e-9 scale, the lower row -row with
    -used + the same tolerances (scale: the row's largest coefficient). A porting difference (the module's docstring):
    the model's land data carry idle land, so the balance holds at the base use, crops - land = base crops - base land.
    Returns (upper rhs, lower row, lower rhs)."""
    scale = float(np.abs(row).max()) if row.any() else 1.0
    used = min(float(row[:n + k] @ xb), float(const))
    return (used + 1e-7 * max(1.0, abs(used)) + 1e-9 * scale, -row.copy(),
            -used + 1e-7 * max(1.0, abs(used)) + 1e-9 * scale)


def e_artoBal(width, n, k, L0):
    r"""e_artoBal(r) (l. 2422-2425, Trustee_land on): the land types add up to the region's total, as a pair of rows on
    the land columns n..n+k (width: the augmented problem's columns): sum L <= sum L0 + 1e-9 and -sum L <= -sum L0 +
    1e-9 max(1, sum L0) (CAPRI's ARTO - INLW, the model's base land types). Returns ([up, lo], [rhs up, rhs lo]).

    CAPRI's GAMS, e_artoBal (l. 2422-2425):

        e_artoBal(RUNR)..
           %data%(runr,"arto","levl","y")-v_actLevl(RUNR,"inlw","T")
           =E=   sum(landTypesMrk $ %data%(runr,landTypesMrk,"levl","y"), v_actLevl(RUNR,landTypesMrk,"T")) ;
    """
    tot = np.zeros(width); tot[n:n + k] = 1.0
    return [tot, -tot], [L0.sum() + 1e-9, -L0.sum() + 1e-9 * max(1.0, L0.sum())]


def permGrasGreening_land(width, j_gras, L0_gras, allowance):
    r"""The land market's grassland floor: GRAS >= (1 - allowance) x its base area (supply.grassland_allowance, CAPRI's
    Green Deal default 0), on the land type's column j_gras; returns (row, rhs) of -L_GRAS <= -(1 - allowance) L0 + 1e-9.
    CAPRI's counterpart is permGrasGreening_ (l. 1902-1904; premiums.py's block), on the grassland activities with
    p_DPGreeningLimits; the model writes that row too ("CAP greening"): two rows for one CAPRI equation, a porting
    difference (N10).

    CAPRI's GAMS, permGrasGreening_ (l. 1902-1904):

       permGrasGreening_(RUNR) $ (p_DPGreeningLimits(runr,"permGras")) ..
           sum((GRSACT,A) $ [DDREG_MPACT("ddGreen",GRSACT) and p_technFact(runr,GRSACT,"LEVL",A)], v_actLevl(runr,GRSACT,A) ) =G= p_DPGreeningLimits(runr,"permGras");
    """
    grs = np.zeros(width); grs[j_gras] = -1.0
    return grs, -(1.0 - allowance) * L0_gras + 1e-9


def e_landTypes_to_LUclass(final, dl, shG, shW, shR):
    r"""e_landTypes_to_LUclass(r, LUclass) (l. 2430-2432) as the change of the land use classes from CAPRI's 2030 ones
    by the model's land types' change dl (1000 ha): CROP + ARAC + FRUN, GRSLND + GRAS + shG OLND, WETLND + shW OLND,
    RESLND + shR OLND, FORE + FORE, ARTIF + ARTIF (p_shFstInSec: OLND's shares, luc_2030.csv; ARTIF's own share 1). Updates final in place (environmental/
    luc.py LUCModel.solve) and returns it.

    CAPRI's GAMS, e_landTypes_to_LUclass (l. 2430-2432):

        e_landTypes_to_LUclass(runr,LUclass) ..
           v_actLevl(runr,LUclass,"T") =E= sum(LandTypesAll, p_shFstInSec(runr,LUclass,LandTypesAll)
                                                            *v_actLevl(runr,LandTypesAll,"T"));
    """
    final["CROP"] += dl["ARAC"] + dl["FRUN"]
    final["GRSLND"] += dl["GRAS"] + shG * dl["OLND"]
    final["WETLND"] += shW * dl["OLND"]
    final["RESLND"] += shR * dl["OLND"]
    final["FORE"] += dl["FORE"]
    final["ARTIF"] += dl.get("ARTIF", 0.0)                 # p_shFstInSec(ARTIF, ARTIF) = 1, prep_sim_luc.gms l. 51
    return final


def e_luClassInitial(idx, keys, fac, i):
    r"""e_luClassInitial(r, LUclass) (l. 2446-2450), the row of the initial class i over the free transitions idx:
    the transitions from i (keys[k][:3] == i) x p_lucAnnualFac_sup (fac: the step length for changes, 1 for remaining);
    its right-hand side the initial area (the model's row not divided by it; luc.py scales the rows by max(1, |b|)).

    CAPRI's GAMS, e_luClassInitial (l. 2446-2450):

        e_luClassInitial(runr,LUclass)  $ p_lucPrior("initialLandUse",runr,LUclass,"T")..
          sum(luc_from_luClass(lucPos,LUclass),v_actLevl(runr,LUCpos,"T")*p_lucAnnualFac_sup(lucPos))
          / (p_lucPrior("initialLandUse",runr,LUclass,"T"))
          =E=  1;
    """
    return np.array([fac[k] if keys[k][:3] == i else 0.0 for k in idx])


def e_luClassFinal(idx, keys, fac, j):
    r"""e_luClassFinal(r, LUclass1) (l. 2438-2441), the row of the final class j: the transitions to j (keys[k][3:] ==
    j) x p_lucAnnualFac_sup; its right-hand side the final area (e_landTypes_to_LUclass).

    CAPRI's GAMS, e_luClassFinal (l. 2438-2441):

        e_luClassFinal(runr,LUclass1) ..
           v_actLevl(runr,LUClass1,"T")
           =E=  (sum(luc_to_luClass(lucPos,LUclass1),v_actLevl(runr,LUCpos,"T")*p_lucAnnualFac_sup(lucPos)) ) ;
    """
    return np.array([fac[k] if keys[k][3:] == j else 0.0 for k in idx])


def p_lucPrior_gamma(m):
    r"""The gamma prior of the transitions with mode m (supply/prep_sim_luc.gms, relative standard error 1: var = m^2):
    alpha - 1 = temp and beta = temp / m, temp = (sqrt(m^2 (m^2 + 4 var)) + m^2) / (2 var); the parameters of
    e_derivativeOfGammaLUC (its GAMS: e_FocLUC's docstring). Returns (alpha - 1, beta)."""
    var = m * m
    temp = (np.sqrt(m * m * (m * m + 4 * var)) + m * m) / (2 * var)
    return temp, temp / m


def e_FocLUC(a1, beta_m, z):
    r"""e_FocLUC(r, LUCpos) (l. 2454-2460) with e_derivativeOfGammaLUC (l. 2466-2468), as the problem whose
    stationarity they are: the negative log posterior density, - sum (alpha - 1) log z - beta m z, z = T / m (CasADi),
    minimised under e_luClassInitial and e_luClassFinal (their duals CAPRI's v_dualOfLUCfromIniClass and
    v_dualOfLUCtoCurClass; environmental/luc.py). a1 = alpha - 1, beta_m = beta x m (p_lucPrior_gamma).

    CAPRI's GAMS, e_FocLUC (l. 2454-2460):

        e_FocLUC(runr,LUCpos)..
        v_derivativeOfLogDensity(runr,LUCpos)
        + v_derivativeOfLogDensSlak(runr,LUCpos)
        + SUM(LUC_TO_LUclass(LUCpos,LUclass1),v_dualOfLUCtoCurClass(runr,LUclass1))
        + SUM(LUC_FROM_LUclass(LUCpos,LUclass),v_dualOfLUCfromIniClass(runr,LUclass))
        =E= 0;

    e_derivativeOfGammaLUC (l. 2466-2468):

        e_derivativeOfGammaLUC(runr,LUCpos) $ [p_lucPrior("distributionFamily",runr,LUCpos,"T") eq gammaDensity]..
            v_derivativeOfLogDensity(runr,LUCpos)
            =E= -p_lucPrior("beta",runr,LUCpos,"T") + (p_lucPrior("alpha",runr,LUCpos,"T")-1) * 1/v_actLevl(runr,LUCpos,"T");
    """
    import casadi as ca
    return -ca.sum1(ca.DM(a1) * ca.log(z) - ca.DM(beta_m) * z)
