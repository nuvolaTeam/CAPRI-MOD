r"""CAPRI's pesticide module in the supply model, its agg5 stage (supply/supply_model.gms, the PEST_DISAGG blocks; its
bounds and starts supply/set_supply_bounds.gms l. 180-212 and supply/prep_sim.gms l. 259-275): the applications per
ha of the five aggregates (v_pestiPerHa), the regional use (v_pestiQuantReg) and the yield factor's place in the
yields (v_yldPestFac). The yield factor's own equation, yldPestFac_, and its damage function are in
capri_mod/supply/equations/pesti_test.py (the calibration's test uses the same equation), imported here.

In this project's notation, per region, crop c, technology T and aggregate i: a_cTi the application (kg per ha), x_cT
the technology's level (1000 ha), y_cT the yield factor; the regional use q_i = sum_cT a_cTi x_cT (t).

Setting supply.pest_disagg ("none", CAPRI's default; "agg5"). The plan: PESTICIDE_P4_PLAN.md in the developer notes.
"""
from __future__ import annotations

from capri_mod.supply.equations.pesti_test import damage_share, yldPestFac_  # noqa: F401  (the supply model's equation)

#: the endogenous application's bounds and the regional use's, times their level (set_supply_bounds.gms l. 182-189 and
#: l. 193-197); the yield factor's, times its level 1 (l. 201-207)
V_PESTIPERHA_BOUNDS = (0.0, 10.0)
V_PESTIQUANTREG_BOUNDS = (0.0, 10.0)
V_YLDPESTFAC_BOUNDS = (0.1, 2.0)


def v_pestiPerHa_l(ApplPerHa):
    r"""The application's start: the calibration point, CAPRI's DATA(PESTO, "y") x 0.001 x (1 + p_technFact), which is
    ApplPerHa of the calibration (supply/cal_pesti.gms l. 32-34).

    CAPRI's GAMS (supply/prep_sim.gms l. 259-263):

        $iftheni.pes32 %pest_disagg%==on
        *           Applications per ha plus transforming g/ha=>kg/ha:
          v_pestiPerHa.l(%regions%,MCACT,pestoAgg,A) $ p_technFact(%regions%,MCACT,"LEVL",A)
             = Data(%regions%,mCACT,PESTOAGG,"y")*.001*(1+p_technFact(%regions%,MCACT,pestoAgg,A));


    In this project's notation: a_cTi = ApplPerHa_cTi. Departures from CAPRI: none."""
    return float(ApplPerHa)


def v_pestiPerHa_bounds(ApplPerHa, endogenous, shifted=False):
    r"""The application's bounds: fixed at its level, free in [0, 10] x its level where the cell is endogenous and no
    scenario shifter (ScenShifterPos_COLS) acts on the aggregate's input.

    CAPRI's GAMS (supply/set_supply_bounds.gms l. 180-189):

        $iftheni.Pes31 %PEST_DISAGG%==ON
                v_pestiPerHa.fx(%regions%,MCACT,pestoAgg,A) = v_pestiPerHa.l(%regions%,MCACT,pestoAgg,A) ;
                v_pestiPerHa.Lo(%REGIONS%,MCACT,pestoAgg,A) $ ( p_pestPar(%REGIONS%,MCACT,pestoAgg,A,"Endogenous")
                                                              $ (not sum(ScenShifterPos_COLS,DATA(%REGIONS%,MCACT,pestoAgg,ScenShifterPos_COLS)))
                                                              )
                   =  v_pestiPerHa.l(%regions%,MCACT,pestoAgg,A) * .0;
                v_pestiPerHa.up(%REGIONS%,MCACT,pestoAgg,A) $ (p_pestPar(%REGIONS%,MCACT,pestoAgg,A,"Endogenous")
                                                              $ (not sum(ScenShifterPos_COLS,DATA(%REGIONS%,MCACT,pestoAgg,ScenShifterPos_COLS)))
                                                              )
                   =  v_pestiPerHa.l(%regions%,MCACT,pestoAgg,A) * 10;

    In this project's notation: (lo, up) = (a0, a0), or (0, 10 a0) where endogenous and not shifted.
    Departures from CAPRI: none."""
    a0 = float(ApplPerHa)
    if endogenous and not shifted:
        return V_PESTIPERHA_BOUNDS[0] * a0, V_PESTIPERHA_BOUNDS[1] * a0
    return a0, a0


def pestiUse_(cells):
    r"""v_pestiQuantReg(r, i): the aggregate's use in the region, over the crops and technologies (kg per ha x 1000 ha
    = t).

    CAPRI's GAMS (supply/supply_model.gms l. 4389-4398):

           pestiUse_(RUNR,pesModDis) $ v_pestiQuantReg.range(RUNR,pesModDis)..
        *
        *    ---  add up pesticide use over crops and and technology alternatives
        *         (endogenous input coefficient in kg times area in 1000 ha)
        *                                                     kicks out BARL..."T" and other empty combinations:
             SUM( (MCACT,A) $ (Data(runr,mCACT,PESMODDIS,"y")  $ p_technFact(RUNR,MCACT,"LEVL",A)),
        *
                 v_pestiPerHa(RUNR,MCACT,pesModDis,A) * v_actLevl(RUNR,MCACT,A))

             =E=             v_pestiQuantReg(RUNR,pesModDis);

    In this project's notation: q_i = sum_cT a_cTi x_cT; cells: [(a_cTi, x_cT)] (numbers or CasADi expressions).
    Departures from CAPRI: none."""
    return sum(a * x for a, x in cells)


def pestiTot_(uses):
    r"""v_pestiQuantReg(r, "pesTotal"): the total over the aggregates.

    CAPRI's GAMS (supply/supply_model.gms l. 4402-4408):

           pestiTot_(RUNR) $ sum(pesModDis $ v_pestiQuantReg.range(RUNR,pesModDis),1)..
        *
        *    ---  add up different pesticide types to total pesticide use in terms of active ingredients
        *
             v_pestiQuantReg(RUNR,"pesTotal")

             =E= sum(pesModDis, v_pestiQuantReg(RUNR,pesModDis));

    In this project's notation: q = sum_i q_i. Departures from CAPRI: none."""
    return sum(uses)


def v_pestiQuantReg_bounds(level, QUTS=None):
    r"""The regional use's bounds: [0, 10] x its level for an aggregate; the total at most the sum of the aggregates'
    upper bounds, or the quota DATA(r, "QUTS", "pestotal", "y") where it is set.

    CAPRI's GAMS (supply/set_supply_bounds.gms l. 192-198):

        *        Input coefficient in kg/ha times area in kha = quantity in tons (lower bound = zero in case of prohibitive policies)
                v_pestiQuantReg.lo(%regions%,pestoAgg) = 0*v_pestiQuantReg.l(%regions%,pestoAgg);
                v_pestiQuantReg.up(%regions%,pestoAgg) = 10*v_pestiQuantReg.l(%regions%,pestoAgg);

                v_pestiQuantReg.lo(%regions%,"pestotal") = 0;
                v_pestiQuantReg.up(%regions%,"pestotal") = sum(pestoagg,v_pestiQuantReg.up(%regions%,pestoAgg))  ;
                v_pestiQuantReg.up(%regions%,"pestotal") $ DATA(%regions%,"QUTS","pestotal","y") = DATA(%regions%,"QUTS","pestotal","y");

    In this project's notation: an aggregate (0, 10 q0); the total (0, QUTS or the sum of the aggregates' 10 q0): call
    with level the sum of the aggregates' levels. Departures from CAPRI: none."""
    up = V_PESTIQUANTREG_BOUNDS[1] * float(level)
    return V_PESTIQUANTREG_BOUNDS[0] * float(level), (float(QUTS) if QUTS else up)


def v_yldPestFac_bounds(has_slope):
    r"""The yield factor's bounds: fixed at 1 (its level at the calibration point, prep_sim.gms l. 270-271), free in
    [0.1, 2] x 1 where an aggregate of the crop's technology has an application and a slope (SlopLin).

    CAPRI's GAMS (supply/set_supply_bounds.gms l. 200-207):

        *        Yield factors may vary endogenously if this a slope parameter for at least one pesticide type:
                v_yldPestFac.lo(%REGIONS%,MCACT,A) $ SUM(pestoAgg $ ( v_pestiPerHa.l(%regions%,MCACT,pestoAgg,A)
                                                                    $ p_pestPar(%regions%,MCACT,pestoAgg,A,"SlopLin")),1)

                   = .1*v_yldPestFac.l(%REGIONS%,MCACT,A);
                v_yldPestFac.up(%REGIONS%,MCACT,A) $ SUM(pestoAgg $ ( v_pestiPerHa.l(%regions%,MCACT,pestoAgg,A)
                                                                    $ p_pestPar(%regions%,MCACT,pestoAgg,A,"SlopLin")),1)
                   = 2.*v_yldPestFac.l(%REGIONS%,MCACT,A);

    In this project's notation: (0.1, 2) where has_slope, else (1, 1). Departures from CAPRI: none."""
    if has_slope:
        return V_YLDPESTFAC_BOUNDS
    return 1.0, 1.0


def yldPestFac_term(v_yldPestFac, has_range=True):
    r"""The factor CAPRI puts on a crop's yield-driven term in each of its 16 places: 1 + (v_yldPestFac - 1) where the
    yield factor has a range (is not fixed), 1 elsewhere. SUPBAL_'s output term shown; the other places write the same
    factor (supply_model.gms l. 1068, 1107, 1207, 1227, 1264, 1372, 1409, 1431, 1452, 1811, 1843, 3728, 3755, 3888, 3902).

    CAPRI's GAMS (supply/supply_model.gms l. 4586-4594):

                    v_actLevl(RUNR,MPACT,A) * (%data%(RUNR,MPACT,OMS,"Y")
        $iftheni.till6 %ghgAbatement%==on
        *      --- mitigation effect on yield considered
                     * v_yldMit(RUNR,MPACT)
        $endif.till6
        *      --- endogenous pesticide use considered
        $iftheni.Pes1 %PEST_DISAGG%==ON
                     * (1 +(v_yldPestFac(RUNR,mPact,A)-1) $ (v_yldPestFac.range(RUNR,mPact,A) $ cact(mpact)))
        $endif.Pes1

    In this project's notation: 1 + (y_cT - 1) [y_cT with a range]. Departures from CAPRI: none."""
    return 1.0 + (v_yldPestFac - 1.0) if has_range else 1.0


def SURTOT_pestTerms(res, rem, fix, dev_MANN, dev_NITF):
    r"""The yield factor's change of a crop's terms in the N surplus (e_SURTOTHa's v_Cresid, v_expprd, v_biofix: the
    places of e_CRESID, e_EXPPRD and e_BIOFIX), per unit of the crop, t N.

    CAPRI's GAMS (supply/supply_model.gms l. 1400-1413, e_CRESID's crop term):

                 + SUM( (FOUT_T_N(FOUT,FNUT),MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A),v_actLevl(RUNR,MCACT,A)
                          *  (%data%(RUNR,MCACT,FOUT,"Y")
        $iftheni.till13 %ghgAbatement%==on
                             +  (%data%(RUNR,mcact,FOUT,"Y")-(p_nitrBalance(RUNR,"AtmDep")+p_nitrBalance(RUNR,"Mineralis"))
                                                            $ sameas(fout,"mann"))
                             *  (v_yldMit(RUNR,MCACT) - 1)
        $endif.till13
        $iftheni.Pes8a %PEST_DISAGG%==ON
                          +  (%data%(RUNR,mCact,FOUT,"Y") - (p_nitrBalance(RUNR,"AtmDep") + p_nitrBalance(RUNR,"Mineralis")) $ sameas(fout,"mann"))
                          *  (v_yldPestFac(RUNR,mCact,A) - 1) $ v_yldPestFac.range(RUNR,mCact,A)
        $endif.Pes8a
                             )
                          * (p_technFact(RUNR,MCACT,FOUT,A)+1.)
                 )* 0.001

    CAPRI's GAMS (supply/supply_model.gms l. 1424-1433, e_EXPPRD's crop term):

               + SUM( (MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A), v_actLevl(RUNR,MCACT,A)
                          * %data%(RUNR,MCACT,FNUT,"Y") * (p_technFact(RUNR,MCACT,FNUT,A)+1.)
        $iftheni.till7 %ghgAbatement%==on
        *        --- mitigation effect on yield considered
                     * v_yldMit(RUNR,MCACT)
        $endif.till7
        $iftheni.Pes10 %PEST_DISAGG%==ON
                          * (1 +(v_yldPestFac(RUNR,mCact,A)-1) $ v_yldPestFac.range(RUNR,mCact,A))
        $endif.Pes10
                    ) * 0.001

    CAPRI's GAMS (supply/supply_model.gms l. 1446-1460, e_BIOFIX's crop term):

                          * (p_technFact(RUNR,MCACT,FNUT,A)+1.)
        $iftheni.till8 %ghgAbatement%==on
        *                  mitigation effect on yield considered
                         * v_yldMit(RUNR,MCACT)
        $endif.till8
        $iftheni.Pes10a %PEST_DISAGG%==ON
                          * (1 +(v_yldPestFac(RUNR,mCact,A)-1) $ v_yldPestFac.range(RUNR,mCact,A))
        $endif.Pes10a
                         * (p_nitrFact(RUNR,MCACT,"BioFix") $ SAMEAS(FNUT,"NITF")
        $iftheni.fertn3 %ghgAbatement%==on
                         * sum(R_RAGG(RUNR,MSACT),1. + (  p_ghgMiti(MSACT,MCACT,"LegSh","othImpact","BioFix")
                                                        * v_Miti(RUNR,MCACT,"LegSh","BioFix")) $ SAMEAS(MCACT,"OFAR"))
        $endif.fertn3
                           )
                    ) * 0.001

    In this project's notation, per crop: res = DATA(MANN) - AtmDep - Mineralis, rem = DATA(NITF) and fix = DATA(NITF)
    x p_nitrFact(BioFix), per unit of the crop at the mean technology (the environmental accounts' unit balance:
    n_crop_residues, n_crop_uptake, n_fixation); dev_f = sum_T (1 + p_technFact(f, T)) x_T (y_T - 1), x_T the
    technology's level (the NLP's pest_dev):

        d surplus = res x dev_MANN + (fix - rem) x dev_NITF

    with the surplus e_SURTOTHa = ... + v_biofix + v_Cresid - v_expprd.

    Departures from CAPRI: on OFAR the legume share's factor on the fixation (1 + othImpact x v_Miti(LegSh)) is not on
    this term (the change from the two together, second order, is left out)."""
    return res * dev_MANN + (fix - rem) * dev_NITF


def insolve_yield_factors(X, x, y, yield_diff, need_diff):
    r"""A crop's in-solve factors over its technologies, as CAPRI's rows sum them (the technology factors and the
    pesticide module's yield factor; SUPBAL_ for the output, NUTNED_ for the need; quoted in yldPestFac_term and in
    capri_mod/supply/techn_mix.py):

        1 + tf  = sum_T (1 + s_T yield_diff) x_T (1 + (y_T - 1)) / X
        ned     = sum_T (1 + s_T need_diff)  x_T (1 + (y_T - 1)) / X

    x_T the technologies' levels (sum X), y_T their yield factors (1 without the pesticide module), s_T = +1/2 for T1,
    -1/2 for T2, 0 for a crop with one technology (techn_mix_2030.csv: yield_diff, need_diff the T1 - T2 differences of
    (1 + p_technFact)). Returns (tf, ned). Departures from CAPRI: the need's technology term is CAPRI's
    SQRT(1 + tf)(1 + tf) over its LEVL-weighted mean, taken as linear in the share (need_diff, as the technology mix's
    column); the accounts apply ned to the whole need, where NUTNED_ puts v_yldPestFac on DATA(crop, FNUT)'s term alone
    (the additive v_cropNutNeedAddFact is 2-9% of the main crops' need in Denmark; the accounts' mineral N is the
    solve's, SupplyResult.mineral_n_alloc, so the need enters them only through the residues' and manure's spread)."""
    s = {"T1": 0.5, "T2": -0.5}
    out = sum((1.0 + s.get(T, 0.0) * yield_diff) * x[T] * yldPestFac_term(y[T]) for T in x) / X
    ned = sum((1.0 + s.get(T, 0.0) * need_diff) * x[T] * yldPestFac_term(y[T]) for T in x) / X
    return out - 1.0, ned
