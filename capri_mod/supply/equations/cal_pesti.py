r"""CAPRI's calibration of the pesticides' yield effects and input demand (supply/cal_pesti.gms, star 3.0; its model
supply/declare_cal_pesti.gms), the 5_aggregates stage (%PESTDISAGGStage% = agg5: the damage function's aggregates
pestoAgg and the items bought pesModDis are both pesTSAgg = PESTOF, PESTOG, PESTOH, PESTOI, PESTOO; sets.gms
l. 4646-4655). The selAI stage's CES nests are not ported (cal_pesti.gms l. 36-142 and every "$Ifi
%PESTDISAGGStage%==SelAI" line).

One function per CAPRI statement block, CAPRI's GAMS quoted at its top. The cells are (region, crop, aggregate,
technology) = (RUNR, MCACT, pestoAgg, A); a cell's values are a dict keyed by CAPRI's item names of p_pestPar
("ApplPerHa", "priceDamagRatio", "SlopLin", ...). The power-function calibration m_pestiCaliPower follows CAPRI's
loop (m_pestiCaliPower_loop) with each cell solved as its own NLP by IPOPT, where CAPRI solves a region's cells, then
all regions' cells, in one NLP with CONOPT (register DEP-59).

The damage function the calibration fits (supply/supply_model.gms yldPestFac_, the power form): the damage factor of
an aggregate at an application a (kg per ha) is 1 - SlopLin a + SlopExpo a^Expon, the yield factor NoDamageFac minus
the sum over the aggregates of maxDamage x that factor; the linear fall-back is the smooth max(0, 1 - SlopFudg a).

The plan: claude/pesticide_module_plan_2026-11-25.md (P3); the data audit claude/pesticide_p1_audit_2026-11-27.md.
"""
from __future__ import annotations

import math

#: CAPRI's prior own-price elasticity of the pesticide demand and the weights of the calibration's compromise
#: (cal_pesti.gms l. 154-161), and the weights of the choice of form (l. 472-473)
PESTI_ELA = {"prior": -0.3, "wgt": 1.0, "negwgt": 100.0}
PESTI_ELA_CHOICE = {"wgt": 1.0, "negwgt": 1000.0}
#: the largest price-damage ratio kept (l. 254), the power utility below which the linear form is taken (l. 490)
PRICE_DAMAGE_RATIO_MAX = 3000.0
POWER_UTILITY_MIN = 0.05
#: CAPRI's p_pestFudge (supply/def_supply_model_par.gms l. 56), the smooth max's term
P_PESTFUDGE = 1e-8


def p_pestPar_ApplPerHa(DATA_PEST_Y, technFact_pest, technFact_LEVL, LEVL_Y):
    r"""The application per ha of an aggregate on a crop's technology (kg per ha).

    CAPRI's GAMS (supply/cal_pesti.gms l. 32-34):

          p_pestPar(runr,mCACT,pesModDis,A,"ApplPerHa")
             = Data(runr,mCACT,PESMODDIS,"y")*.001*(1+p_technFact(runr,MCACT,pesModDis,A))
             $ (p_technFact(runr,MCACT,"LEVL",A)*Data(runr,mCACT,"LEVL","y"))     ;

    In this project's notation: ApplPerHa = DATA(pesto, "Y") x 0.001 x (1 + technFact(pesto, A)) where the technology
    has a share (technFact(LEVL, A)) and the crop a level at "Y"; DATA in g per ha. technFact of an aggregate is the
    general inputs' +-0.25 (intens/techf.gms l. 92-93; with the module on, PACT_TO_I(PACT, pesModDis) = PACT_TO_I(PACT,
    "PLAP"), sets.gms l. 5365-5368).

    Departures from CAPRI: none."""
    if not (float(technFact_LEVL) * float(LEVL_Y)):
        return 0.0
    return float(DATA_PEST_Y) * 0.001 * (1.0 + float(technFact_pest))


def p_pestPar_NoDamageYld(outputs, technFact_LEVL, LEVL_Y):
    r"""The crop's monetary yield after the on-farm share and without damage (EUR per ha), the value the avoided damage
    is measured in.

    CAPRI's GAMS (supply/cal_pesti.gms l. 168-175):

          p_pestPar(RUNR,MCACT,"yild",A,"NoDamageYld")  $ p_technFact(runr,MCACT,"LEVL",A)
             = sum(pact_to_o(mCact,OMS),data(RUNR,mcact,OMS,"y")*( data(RUNR,"uvag",OMS,"y")
                                                                                             $ (not sameas(oms,"sugb"))
                                                                  +p_emr(runr,a)             $ (    sameas(oms,"sugb"))
                                                                  )
                                                                *(1+p_technFact(RUNR,MCACT,OMS,A))
                                                                *(1-p_onFarmShare(RUNR,OMS))*.001)
             $ (p_technFact(runr,MCACT,"LEVL",A)*Data(runr,mCACT,"LEVL","y"))     ;

    In this project's notation: sum over the crop's outputs OMS (PACT_TO_O) of DATA(OMS, "Y") x price x (1 +
    technFact(OMS, A)) x (1 - p_onFarmShare(OMS)) x 0.001, the price UVAG(OMS) at "Y" (sugar beet: p_emr, the expected
    marginal revenue of sugar beet production, sugar/adjQuot.gms), where the technology has a share and the crop a level.
    outputs: [(DATA_Y, price, technFact, onFarmShare)].

    Departures from CAPRI: none."""
    if not (float(technFact_LEVL) * float(LEVL_Y)):
        return 0.0
    return sum(float(d) * float(p) * (1.0 + float(tf)) * (1.0 - float(s)) * 0.001 for d, p, tf, s in outputs)


def p_pestPar_margCostYld(fnut, DATA_FNUT_Y, multFact, technFact_FNUT, technFact_Yield, residues, UVAG_FNUT_MS,
                          bioFix=0.0, defr=1.0, crop="", emiLoss_N2O_GasTot=0.0, emiLoss_N_GasRunTot=0.0):
    r"""The marginal fertiliser cost of the avoided yield loss for one nutrient (EUR per ha): the nutrient need the
    yield carries, net of the residues' supply, at the member state's fertiliser price; FERC their sum over the
    nutrients (l. 223).

    CAPRI's GAMS (supply/cal_pesti.gms l. 181-223):

          p_pestPar(RUNR,MCACT,FNUT,A,"margCostYld") $ (p_technFact(RUNR,MCACT,"LEVL",A) $ p_pestPar(RUNR,MCACT,"yild",A,"NoDamageYld"))

            =  (
        *     - total nutrient need of crops in kg/ha (retention - biolog. fixation for certain crops) * nutrient factor
        *
                 %data%(RUNR,MCACT,FNUT,"Y")*(1-p_nitrFact(RUNR,MCACT,"BioFix") $ SAMEAS(FNUT,"NITF"))*v_cropNutNeedMultFact.l(RUNR,FNUT,A)
        *
        *     - soil property effect
        *
               * (p_nitrFact(RUNR,"ALL","DEFR") $ SAMEAS(FNUT,"NITF") + 1 $ (NOT SAMEAS(FNUT,"NITF")))
        *
        *     - increasing fertilizing needs as a function of the exogenous yield differential between technologies (works together with next)
        *
               * SQRT([1.+p_technFact(RUNR,MCACT,"Yield",A)+.2 $ SAMEAS(MCACT,"GRAI") - .2 $ SAMEAS(MCACT,"GRAE")] $ data(RUNR,MCACT,FNUT,"Y"))
        *
        *     - factor describing the changes in removal of nutrients resulting from yield difference stored in TECHF
        *
               *(p_technFact(RUNR,MCACT,FNUT,A)+1.)
        *
        *     - crop residue output of nutrients from crops in kg/ha (without atmospheric deposition),
        *
               - SUM( FOUT_T_N(FOUT,FNUT),

                    (p_technFact(RUNR,mCact,FOUT,A)+1.)
                   *(%data%(RUNR,mCact,FOUT,"Y")-(p_nitrBalance(RUNR,"AtmDep")+p_nitrBalance(RUNR,"Mineralis")) $ sameas(fout,"mann"))

        *     - considering nutrient availability and gaseous losses
        *
                   * v_nutAvailFactCRes.l(RUNR,FOUT)
                   *(1.-v_emiLoss.l(RUNR,"NETF","N2O","GasTot") $ SAMEAS(FNUT,"NITF") ) )
        *
        *     - additional mineral fertiliser need to compensate for runoff losses and gaseous losses
        *
               ) / (1.-v_emiLoss.l(RUNR,"NETF","N","GasRunTot") $ SAMEAS(FNUT,"NITF") )
        *
        *     - multiplied with mineral fertiliser price /t*.001 = /kg
        *
            *  SUM(R_RAGG(RUNR,MSACT), %data%(MSACT,"UVAG",FNUT,"Y"))*.001 ;


        * --- Adding up marginal fertiliser cost of higher yield for all nutients kg/ha*/t*.001=/ha:

          p_pestPar(RUNR,MCACT,"FERC",A,"margCostYld") = sum(fnut,p_pestPar(RUNR,MCACT,FNUT,A,"margCostYld"));

    In this project's notation, for the nutrient f (NITF, PHOF, POTF): (DATA(f) x (1 - BioFix if NITF) x
    v_cropNutNeedMultFact(f, A) x (DEFR if NITF else 1) x sqrt(1 + technFact(Yield, A) + 0.2 (GRAI) - 0.2 (GRAE)) x (1 +
    technFact(f, A)) - sum over the residue outputs FOUT of f (FOUT_T_N) of (1 + technFact(FOUT, A)) x (DATA(FOUT) -
    (AtmDep + Mineralis) for MANN) x v_nutAvailFactCRes(FOUT) x (1 - v_emiLoss(NETF, N2O, GasTot) if NITF)) / (1 -
    v_emiLoss(NETF, N, GasRunTot) if NITF) x UVAG(MS, f) x 0.001; the square root's term 0 where DATA(f) is 0 (its
    $ condition). residues: [(technFact_FOUT, DATA_FOUT_Y_net, nutAvailFactCRes)], DATA_FOUT_Y_net with the MANN
    deduction already made. The levels of the fertiliser calibration (v_cropNutNeedMultFact.l, v_nutAvailFactCRes.l,
    v_emiLoss.l) are the inputs.

    Departures from CAPRI: none."""
    nit = str(fnut) == "NITF"
    d = float(DATA_FNUT_Y)
    root = 1.0 + float(technFact_Yield) + (0.2 if crop == "GRAI" else 0.0) - (0.2 if crop == "GRAE" else 0.0)
    need = (d * (1.0 - (float(bioFix) if nit else 0.0)) * float(multFact) * (float(defr) if nit else 1.0)
            * (math.sqrt(root) if d else 0.0) * (float(technFact_FNUT) + 1.0))
    supply = sum((float(tf) + 1.0) * float(q) * float(av) * (1.0 - (float(emiLoss_N2O_GasTot) if nit else 0.0))
                 for tf, q, av in residues)
    return (need - supply) / (1.0 - (float(emiLoss_N_GasRunTot) if nit else 0.0)) * float(UVAG_FNUT_MS) * 0.001


def p_negMargWoPesti(margCostYld_FERC, NoDamageYld):
    r"""Whether the crop's margin of the avoided loss is negative (the marginal fertiliser cost above the yield's
    value): such a crop gets no price-damage ratio (CAPRI writes the cases to a check file).

    CAPRI's GAMS (supply/cal_pesti.gms l. 225-237):

          p_negMargWoPesti(RUNR,MCACT,rows,A,"margCostYld")
            $ (   p_pestPar(RUNR,MCACT,"FERC",A,"margCostYld") gt p_pestPar(RUNR,MCACT,"yild",A,"NoDamageYld"))
            = p_pestPar(RUNR,MCACT,rows,A,"margCostYld");
          p_negMargWoPesti(RUNR,MCACT,"yild",A,"NoDamageYld")
            $ (   p_pestPar(RUNR,MCACT,"FERC",A,"margCostYld") gt p_pestPar(RUNR,MCACT,"yild",A,"NoDamageYld"))
            = p_pestPar(RUNR,MCACT,"yild",A,"NoDamageYld");

          if(card(p_negMargWoPesti),
        $ifi     %mode%==capreg  execute_unload "%RESULTS_OUT%\capreg\chk_neg_margin_%bas%%countries_fst2%.gdx" p_negMargWoPesti;
        $ifi not %mode%==capreg  execute_unload "%RESULTS_OUT%\baseline\chk_neg_margin_%bas%%sim%%countries_fst2%.gdx" p_negMargWoPesti;

        *     abort "negative priceDamagRatio in %system.fn% %system.incline%", p_negMargWoPesti;
            );

    In this project's notation: margCostYld(FERC) > NoDamageYld.

    Departures from CAPRI: the check file is not written (the flag is returned)."""
    return float(margCostYld_FERC) > float(NoDamageYld)


def p_pestPar_priceDamagRatio(UVAG_pesto, NoDamageYld, margCostYld_FERC, maxDamage, negative_margin=False):
    r"""The ratio of the aggregate's price to the avoided maximum damage net of the marginal fertiliser cost (ha per
    kg), the key term of the farmer's first-order condition; huge ratios removed; the cell endogenous where a ratio
    remains.

    CAPRI's GAMS (supply/cal_pesti.gms l. 242-257):

          p_pestPar(RUNR,MCACT,pestoAgg,A,"priceDamagRatio")
            $ ( ((p_pestPar(RUNR,MCACT,"yild",A,"NoDamageYld")-p_pestPar(RUNR,MCACT,"FERC",A,"margCostYld"))*p_pestPar(RUNR,mCACT,pestoAgg,A,"maxdamage"))
              $ (not p_negMargWoPesti(RUNR,MCACT,"yild",A,"NoDamageYld")))
            = (data(RUNR,"uvag",pestoAgg,"y")
        *     Prices are only assigned to data() for elements of set inputs I (in calc_aver)=> Use crop specific aggregate prices:
        $Ifi %PESTDISAGGStage%==SelAI      + p_pestPar(RUNR,MCACT,pestoAgg,A,"uvag") $ (not data(RUNR,"uvag",pestoAgg,"y"))
              )
            / (( p_pestPar(RUNR,MCACT,"yild",A,"NoDamageYld")
               - p_pestPar(RUNR,MCACT,"FERC",A,"margCostYld")   )
            *p_pestPar(RUNR,mCACT,pestoAgg,A,"maxdamage")) ;

        *     Remove huge priceDamagRatio entries as these create often unbounded calibration problems (will be treated as fixed)
          p_pestPar(RUNR,MCACT,pestoAgg,A,"priceDamagRatio") $ (p_pestPar(RUNR,MCACT,pestoAgg,A,"priceDamagRatio") gt 3000) = 0;

        *     Initially we try to model endogenously all cases with a "reasonable" priceDamagRatio (this endogenous set may be reduced later)
          p_pestPar(RUNR,MCACT,pestoAgg,A,"endogenous") = 1 $ p_pestPar(RUNR,MCACT,pestoAgg,A,"priceDamagRatio");

    In this project's notation: r = UVAG(pesto) / ((NoDamageYld - margCostYld(FERC)) x maxDamage) where that
    denominator is non-zero and the crop's margin is not negative (p_negMargWoPesti, l. 225-232: margCostYld above
    NoDamageYld); r = 0 above 3,000; endogenous = 1 where r is non-zero. UVAG in EUR per kg (l. 239: "Euro/kg for
    pesticides"; CAPREG's DATA in g per ha x UVAG / 1000 is EUR per ha), so r in ha per kg as the slopes (l. 262-263).
    Returns (r, endogenous).

    Departures from CAPRI: none (the selAI line not ported)."""
    den = (float(NoDamageYld) - float(margCostYld_FERC)) * float(maxDamage)
    if not den or negative_margin:
        return 0.0, 0
    r = float(UVAG_pesto) / den
    if r > PRICE_DAMAGE_RATIO_MAX:
        r = 0.0
    return r, (1 if r else 0)


def p_pestPar_slopFudg(ApplPerHa, priceDamagRatio, endogenous):
    r"""The linear fall-back's slope from the origin to the observed point (ApplPerHa, 1), and the cell exogenous where
    that slope is below the price-damage ratio (the observed point is then not an optimum of any linear form).

    CAPRI's GAMS (supply/cal_pesti.gms l. 268-272):

          p_pestPar(RUNR,MCACT,pestoAgg,A,"slopFudg") $ p_pestPar(RUNR,MCACT,pestoAgg,A,"applPerHa")
             = 1/p_pestPar(RUNR,MCACT,pestoAgg,A,"applPerHa");

          p_pestPar(RUNR,MCACT,pestoAgg,A,"endogenous")
             $ (p_pestPar(RUNR,MCACT,pestoAgg,A,"slopFudg") lt p_pestPar(RUNR,MCACT,pestoAgg,A,"priceDamagRatio")) = 0;

    In this project's notation: SlopFudg = 1 / ApplPerHa where ApplPerHa is non-zero; endogenous = 0 where SlopFudg <
    priceDamagRatio. Returns (SlopFudg, endogenous).

    Departures from CAPRI: none."""
    a = float(ApplPerHa)
    s = 1.0 / a if a else 0.0
    if s < float(priceDamagRatio):
        endogenous = 0
    return s, endogenous


def pestiOptimal_(a, pdr, SlopLin, SlopExpo, Expon, log=math.log):
    r"""The farmer's first-order condition at the observed application (the derivative of the damage function equals
    the price-damage ratio), in logs.

    CAPRI's GAMS (supply/declare_cal_pesti.gms l. 60-64):

          pestiOptimal_(runr,PACTCUR,pestCur,A) $ (p_pestPar(RUNR,PACTCUR,pestCur,A,"priceDamagRatio") $ (not excl_map(runr,pactCur,pestCur)))..

              log(p_pestPar(RUNR,PACTCUR,pestCur,A,"ApplPerHa"))*(v_pestPar(RUNR,PACTCUR,pestCur,A,"Expon")-1)
                 =E= log(v_pestPar(RUNR,PACTCUR,pestCur,A,"SlopLin")-p_pestPar(RUNR,PACTCUR,pestCur,A,"priceDamagRatio"))
                    -log(v_pestPar(RUNR,PACTCUR,pestCur,A,"SlopExpo")*v_pestPar(RUNR,PACTCUR,pestCur,A,"Expon")) ;

    In this project's notation: log(a) (Expon - 1) - log(SlopLin - pdr) + log(SlopExpo Expon) = 0, with a = ApplPerHa,
    pdr = priceDamagRatio. Returns the residual (left minus right).

    Departures from CAPRI: none."""
    return log(a) * (Expon - 1.0) - (log(SlopLin - pdr) - log(SlopExpo * Expon))


def pestiEla_(pdr, powerPriceEla, SlopLin, Expon):
    r"""The demand's own-price elasticity implied by the power function at the observed point.

    CAPRI's GAMS (supply/declare_cal_pesti.gms l. 66-70):

          pestiEla_(runr,PACTCUR,pestCur,A) $ (p_pestPar(RUNR,PACTCUR,pestCur,A,"priceDamagRatio") $ (not excl_map(runr,pactCur,pestCur)))..

              v_pestPar(RUNR,PACTCUR,pestCur,A,"powerPriceEla")*(1 - v_pestPar(RUNR,PACTCUR,pestCur,A,"SlopLin")
                                                                   / p_pestPar(RUNR,PACTCUR,pestCur,A,"priceDamagRatio"))
                 =E= 1/(v_pestPar(RUNR,PACTCUR,pestCur,A,"Expon")-1) ;

    In this project's notation: powerPriceEla (1 - SlopLin / pdr) - 1 / (Expon - 1) = 0. Returns the residual.

    Departures from CAPRI: none."""
    return powerPriceEla * (1.0 - SlopLin / pdr) - 1.0 / (Expon - 1.0)


def pestiMinDamage_(minRelDamage, SlopLin, SlopExpo, Expon):
    r"""The lowest damage factor the power function reaches (at its minimum in the application).

    CAPRI's GAMS (supply/declare_cal_pesti.gms l. 73-79):

          pestiMinDamage_(runr,PACTCUR,pestCur,A) $ (p_pestPar(RUNR,PACTCUR,pestCur,A,"priceDamagRatio") $ (not excl_map(runr,pactCur,pestCur)))..

              v_pestPar(RUNR,PACTCUR,pestCur,A,"minRelDamage")
                 =E= 1 - (v_pestPar(RUNR,PACTCUR,pestCur,A,"SlopLin")
                         /(v_pestPar(RUNR,PACTCUR,pestCur,A,"SlopExpo")
                          *v_pestPar(RUNR,PACTCUR,pestCur,A,"Expon")   ))**(1/(v_pestPar(RUNR,PACTCUR,pestCur,A,"Expon")-1))
                         *(1-1/v_pestPar(RUNR,PACTCUR,pestCur,A,"Expon"))*v_pestPar(RUNR,PACTCUR,pestCur,A,"SlopLin") ;

    In this project's notation: minRelDamage - (1 - (SlopLin / (SlopExpo Expon))^(1 / (Expon - 1)) (1 - 1 / Expon)
    SlopLin) = 0. Returns the residual.

    Departures from CAPRI: none."""
    return minRelDamage - (1.0 - (SlopLin / (SlopExpo * Expon)) ** (1.0 / (Expon - 1.0)) * (1.0 - 1.0 / Expon) * SlopLin)


def powerObje_(minRelDamage, powerPriceEla, ela=PESTI_ELA, sqrt=math.sqrt):
    r"""A cell's term of the calibration's objective: the minimum damage close to zero, the elasticity close to the
    prior, a penalty on a negative minimum damage (a yield gain).

    CAPRI's GAMS (supply/declare_cal_pesti.gms l. 81-94):

          powerObje_..

              v_obje*100
                 =E= sum((RUNR,PACTCUR,pestCur,A) $ (p_pestPar(RUNR,PACTCUR,pestCur,A,"priceDamagRatio") $ (not excl_map(runr,pactCur,pestCur))),

                                                sqr(v_pestPar(RUNR,PACTCUR,pestCur,A,"minRelDamage"))

                           + p_pestiEla("wgt")* sqr(v_pestPar(RUNR,PACTCUR,pestCur,A,"powerPriceEla")-p_pestiEla("prior") )


                        + p_pestiEla("negwgt")* SQR(( 0+ v_pestPar(RUNR,PACTCUR,pestCur,A,"minRelDamage")
                                                    - SQRT( SQR( 0-v_pestPar(RUNR,PACTCUR,pestCur,A,"minRelDamage")) + SQR(0.01))
                                                     + 0.01)/2 -0)
                           ) ;

    In this project's notation, per cell: (md^2 + wgt (pe - prior)^2 + negwgt ((md - sqrt(md^2 + 0.01^2) + 0.01) / 2)^2)
    / 100 with md = minRelDamage, pe = powerPriceEla; v_obje the sum over the cells. Returns the cell's term.

    Departures from CAPRI: none."""
    md, pe = minRelDamage, powerPriceEla
    neg = (md - sqrt(md * md + 0.01 * 0.01) + 0.01) / 2.0
    return (md * md + ela["wgt"] * (pe - ela["prior"]) ** 2 + ela["negwgt"] * neg * neg) / 100.0


def v_pestPar_start_and_bounds(pdr, ApplPerHa, retry=False):
    r"""The power calibration's start values and bounds of a cell's variables; the retry's start values.

    CAPRI's GAMS (supply/cal_pesti.gms l. 299-319):

          v_pestPar.l(RUNR,MCACT,pestoAgg,A,"powerPriceEla")
            $ (p_pestPar(runr,mCACT,pestoAgg,A,"ApplPerHa") $ p_pestPar(RUNR,MCACT,pestoAgg,A,"priceDamagRatio")) = p_pestiEla("prior") ;
          v_pestPar.lo(RUNR,MCACT,pestoAgg,A,"powerPriceEla") $ v_pestPar.l(RUNR,MCACT,pestoAgg,A,"powerPriceEla") = -10000;
          v_pestPar.up(RUNR,MCACT,pestoAgg,A,"powerPriceEla") $ v_pestPar.l(RUNR,MCACT,pestoAgg,A,"powerPriceEla") = 0;

          v_pestPar.l(RUNR,MCACT,pestoAgg,A,"SlopLin")
            $ (p_pestPar(runr,mCACT,pestoAgg,A,"ApplPerHa") $ p_pestPar(RUNR,MCACT,pestoAgg,A,"priceDamagRatio")) = 1;
          v_pestPar.lo(RUNR,MCACT,pestoAgg,A,"SlopLin")
            $ p_pestPar(RUNR,MCACT,pestoAgg,A,"priceDamagRatio") = p_pestPar(RUNR,MCACT,pestoAgg,A,"priceDamagRatio") + 1.e-2;
          v_pestPar.up(RUNR,MCACT,pestoAgg,A,"SlopLin")
            $ v_pestPar.l(RUNR,MCACT,pestoAgg,A,"SlopLin") = max(v_pestPar.lo(RUNR,MCACT,pestoAgg,A,"SlopLin")+1.e+2,1.e+3);

          v_pestPar.l(RUNR,MCACT,pestoAgg,A,"SlopExpo")   $ v_pestPar.l(RUNR,MCACT,pestoAgg,A,"SlopLin") = 1;
          v_pestPar.lo(RUNR,MCACT,pestoAgg,A,"SlopExpo")  $ v_pestPar.l(RUNR,MCACT,pestoAgg,A,"SlopLin") = 1.e-4;
          v_pestPar.up(RUNR,MCACT,pestoAgg,A,"SlopExpo")  $ v_pestPar.l(RUNR,MCACT,pestoAgg,A,"SlopLin") = 1.e+3;

          v_pestPar.l(RUNR,MCACT,pestoAgg,A,"Expon")   $ v_pestPar.l(RUNR,MCACT,pestoAgg,A,"SlopLin") = 2;
          v_pestPar.lo(RUNR,MCACT,pestoAgg,A,"Expon")  $ v_pestPar.l(RUNR,MCACT,pestoAgg,A,"SlopLin") = 1.+1.e-1;
          v_pestPar.up(RUNR,MCACT,pestoAgg,A,"Expon")  $ v_pestPar.l(RUNR,MCACT,pestoAgg,A,"SlopLin") = 10.;

          v_pestPar.lo(RUNR,MCACT,pestoAgg,A,"minRelDamage")  $ v_pestPar.l(RUNR,MCACT,pestoAgg,A,"SlopLin") = -2000;

    and the retry's (l. 345-355):

            if((m_pestiCaliPower.modelstat gt 2)  ,
        *
              v_obje.l = 0;
              v_pestPar.l(RUNR,MCACT,pestCur,A,"minRelDamage")  = 0;
              v_pestPar.l(RUNR,MCACT,pestCur,A,"powerPriceEla")
                 $ (p_pestPar(runr,mCACT,pestCur,A,"ApplPerHa") $ p_pestPar(RUNR,MCACT,pestCur,A,"priceDamagRatio")) = p_pestiEla("prior") ;
              v_pestPar.l(RUNR,PACTCUR,pestCur,A,"SlopLin")
                 $ (p_pestPar(runr,pactCur,pestCur,A,"ApplPerHa") $ p_pestPar(RUNR,PACTCUR,pestCur,A,"priceDamagRatio")) = 1;
              v_pestPar.l(RUNR,PACTCUR,pestCur,A,"SlopExpo")   $ v_pestPar.l(RUNR,PACTCUR,pestCur,A,"SlopLin") = 1;
              v_pestPar.l(RUNR,PACTCUR,pestCur,A,"Expon")   $ v_pestPar.l(RUNR,PACTCUR,pestCur,A,"SlopLin") = 1.1;
              SOLVE m_pestiCaliPower USING NLP MinIMIZING v_obje;

    In this project's notation, for a cell with ApplPerHa and pdr: powerPriceEla in [-10000, 0] from the prior; SlopLin
    in [pdr + 0.01, max(pdr + 0.01 + 100, 1000)] from 1; SlopExpo in [1e-4, 1e3] from 1; Expon in [1.1, 10] from 2
    (the retry: 1.1); minRelDamage from 0, at least -2000. Returns {name: (start, lower, upper)}.

    Departures from CAPRI: a start below its lower bound (SlopLin's 1 under pdr + 0.01) is CAPRI's too; GAMS hands it
    to the solver, which moves it to the bound, as IPOPT does."""
    if not (float(ApplPerHa) and float(pdr)):
        return {}
    lo_sl = float(pdr) + 1e-2
    inf = float("inf")
    return {"powerPriceEla": (PESTI_ELA["prior"], -10000.0, 0.0),
            "SlopLin": (1.0, lo_sl, max(lo_sl + 1e2, 1e3)),
            "SlopExpo": (1.0, 1e-4, 1e3),
            "Expon": (1.1 if retry else 2.0, 1.0 + 1e-1, 10.0),
            "minRelDamage": (0.0, -2000.0, inf)}


VARS = ("powerPriceEla", "SlopLin", "SlopExpo", "Expon", "minRelDamage")
#: IPOPT's tolerance on an equation, for flagging a cell of a failed solve (CAPRI: an equation's level off its bound)
PESTI_CALI_ROW_TOL = 1e-6
_SOLVERS = {}


def _solver(n):
    """IPOPT on m_pestiCaliPower over n cells (the equations above, CasADi), parametric in each cell's (a, pdr); built
    once per size."""
    if n in _SOLVERS:
        return _SOLVERS[n]
    import casadi as ca
    x = ca.SX.sym("x", 5 * n)
    p = ca.SX.sym("p", 2 * n)
    g, f = [], 0
    for j in range(n):
        pe, sl, se, ex, md = (x[5 * j + i] for i in range(5))
        a, pdr = p[2 * j], p[2 * j + 1]
        g += [pestiOptimal_(a, pdr, sl, se, ex, log=ca.log), pestiEla_(pdr, pe, sl, ex),
              pestiMinDamage_(md, sl, se, ex)]
        f += powerObje_(md, pe, sqrt=ca.sqrt)
    opts = {"ipopt.print_level": 0, "print_time": False, "ipopt.sb": "yes", "ipopt.max_iter": 10000,
            "ipopt.tol": 1e-10, "ipopt.constr_viol_tol": 1e-10}
    _SOLVERS[n] = ca.nlpsol("m_pestiCaliPower", "ipopt", {"x": x, "p": p, "f": f, "g": ca.vertcat(*g)}, opts)
    return _SOLVERS[n]


def m_pestiCaliPower(cells, x0):
    r"""One solve of m_pestiCaliPower (powerObje_, pestiOptimal_, pestiEla_, pestiMinDamage_) over the cells given, all
    in one NLP, from x0 (n x 5, VARS' order) within v_pestPar_start_and_bounds. cells: [(ApplPerHa, pdr)].
    Returns (x, ok, IPOPT's status, the largest equation residual per cell); ok as CAPRI's modelstat 1 or 2.

    Departures from CAPRI: the solver (IPOPT for CONOPT)."""
    import numpy as np
    n = len(cells)
    if not n:
        return np.zeros((0, 5)), True, "empty", np.zeros(0)
    b = [v_pestPar_start_and_bounds(pdr, a) for a, pdr in cells]
    lbx = np.array([[bb[v][1] for v in VARS] for bb in b]).ravel()
    ubx = np.array([[bb[v][2] for v in VARS] for bb in b]).ravel()
    S = _solver(n)
    r = S(x0=np.clip(np.asarray(x0, float).ravel(), lbx, np.where(np.isfinite(ubx), ubx, 1e30)), lbx=lbx, ubx=ubx,
          lbg=0.0, ubg=0.0, p=np.array(cells, float).ravel())
    st = S.stats()
    ok = bool(st.get("success")) or st.get("return_status") in ("Solve_Succeeded", "Solved_To_Acceptable_Level")
    res = np.abs(np.asarray(r["g"], float).ravel()).reshape(n, 3).max(axis=1)
    return np.asarray(r["x"], float).reshape(n, 5), ok, str(st.get("return_status")), res


def m_pestiCaliPower_loop(cells):
    r"""CAPRI's calibration of the power form: the loop over (region, crop) solving at each pass m_pestiCaliPower for
    each of the region's cells, the levels carried from pass to pass, a retry from the retry's starts where a solve is
    not optimal, the cell of a failed retry flagged (powerInfes); then the last solve of the cells whose crop and
    aggregate has no flagged cell (excl_map, all technologies), minRelDamage reset to 0, from the loop's levels.

    CAPRI's GAMS (supply/cal_pesti.gms l. 322-371, the loop with its retry; l. 373-405, the last solve and its results):

          loop((ru,mcact) $  sum((A,pestoAgg) $ ( rcmp(ru) $ p_pestPar(RU,MCACT,pestoAgg,A,"priceDamagRatio")),1),

            option kill   = RUNR;
            RUNR(ru) = YES;

            pestCur(pestoAgg) = yes;

            option kill   = pactCur;
            pactCur(mCact) $ sum(pestcur, Data(ru,mCACT,PESTcur,"y")) = yes;

            v_obje.l = 0;
            v_pestPar.l(RU,MCACT,pestcur,A,"minRelDamage")  = 0;

                 m_pestiCaliPower.SOLprint = 2;
                 m_pestiCaliPower.SOLVELINK = 5;
                 m_pestiCaliPower.limrow = 0;
                 m_pestiCaliPower.limcol = 0;
                 m_pestiCaliPower.iterlim = 10000;
            SOLVE m_pestiCaliPower USING NLP MinIMIZING v_obje;
            if ( EXECERROR > 0,abort "internal error in %system.fn% in %system.incline%";);

        * -- retry if infeasible or non-optimal (helped in several cases)

            if((m_pestiCaliPower.modelstat gt 2)  ,
        *
              v_obje.l = 0;
              v_pestPar.l(RUNR,MCACT,pestCur,A,"minRelDamage")  = 0;
              v_pestPar.l(RUNR,MCACT,pestCur,A,"powerPriceEla")
                 $ (p_pestPar(runr,mCACT,pestCur,A,"ApplPerHa") $ p_pestPar(RUNR,MCACT,pestCur,A,"priceDamagRatio")) = p_pestiEla("prior") ;
              v_pestPar.l(RUNR,PACTCUR,pestCur,A,"SlopLin")
                 $ (p_pestPar(runr,pactCur,pestCur,A,"ApplPerHa") $ p_pestPar(RUNR,PACTCUR,pestCur,A,"priceDamagRatio")) = 1;
              v_pestPar.l(RUNR,PACTCUR,pestCur,A,"SlopExpo")   $ v_pestPar.l(RUNR,PACTCUR,pestCur,A,"SlopLin") = 1;
              v_pestPar.l(RUNR,PACTCUR,pestCur,A,"Expon")   $ v_pestPar.l(RUNR,PACTCUR,pestCur,A,"SlopLin") = 1.1;
              SOLVE m_pestiCaliPower USING NLP MinIMIZING v_obje;

              if (       (m_pestiCaliPower.numinfes gt 0) or (m_pestiCaliPower.ModelStat eq 4)
                      or (m_pestiCaliPower.ModelStat eq 5) or (m_pestiCaliPower.ModelStat eq 6),

                  p_pestPar(runr,pactCur,pestCur,A,"powerInfes") $ (   (abs(pestiOptimal_.m(runr,pactCur,pestCur,A)) gt eps)
                                                                    or (abs(pestiEla_.m(runr,pactCur,pestCur,A)) gt eps)
                                                                    or (abs(pestiMinDamage_.m(runr,pactCur,pestCur,A)) gt eps)
                                                                    or (abs(pestiOptimal_.lo(runr,pactCur,pestCur,A)-pestiOptimal_.l(runr,pactCur,pestCur,A)) gt 1.e-10)
                                                                    or (abs(pestiEla_.lo(runr,pactCur,pestCur,A)-pestiEla_.l(runr,pactCur,pestCur,A)) gt  1.e-10)
                                                                    or (abs(pestiMinDamage_.lo(runr,pactCur,pestCur,A)-pestiMinDamage_.l(runr,pactCur,pestCur,A)) gt  1.e-10)
                                                                    ) = 1;
                 );
        *   end of "if((m_pestiCaliPower.modelstat gt 2)":
            );
        * end of "loop((ru,mcact,pestoAgg)":
          );



        * --- Store results from power fct calibration for later evaluation

            option kill   = RUNR;
            runr(rcmp) = yes;

            pestCur(pestoAgg) = yes;

            option kill   = pactCur;
            pactCur(mCact) $ sum((runr,pestoAgg,A) $ (p_pestPar(RUNR,MCACT,pestoAgg,A,"priceDamagRatio") $ Data(runr,mCACT,pestoAgg,"y")),1) = yes;
            excl_map(runr,pactCur,pestCur) $ sum(a, p_pestPar(runr,pactCur,pestCur,A,"powerInfes")) = yes;

        *   Reinitialise to avoid that huge results from single infeasible cases render the whole country infeasible (unbnd)
            v_obje.l = 0;
            v_pestPar.l(RUNR,MCACT,pestoAgg,A,"minRelDamage")  = 0;
        *
                         m_pestiCaliPower.holdfixed = 0;
                         m_pestiCaliPower.Solprint  = 1;
                         m_pestiCaliPower.Solvelink = 5;
        *                 m_pestiCaliPower.iterlim   = 0;

        *    SOLVE m_pestiCaliPower USING NLP MinIMIZING v_obje;

                         m_pestiCaliPower.iterlim   = 10000;

            SOLVE m_pestiCaliPower USING NLP MinIMIZING v_obje;

          p_pestPar(RUNR,PACTCUR,pestoAgg,A,"powerpriceEla") = v_pestPar.l(RUNR,PACTCUR,pestoAgg,A,"powerPriceEla") ;
          p_pestPar(RUNR,PACTCUR,pestoAgg,A,"SlopLin")  = v_pestPar.l(RUNR,PACTCUR,pestoAgg,A,"SlopLin");
          p_pestPar(RUNR,PACTCUR,pestoAgg,A,"SlopExpo") = v_pestPar.l(RUNR,PACTCUR,pestoAgg,A,"SlopExpo");
          p_pestPar(RUNR,PACTCUR,pestoAgg,A,"Expon")    = v_pestPar.l(RUNR,PACTCUR,pestoAgg,A,"Expon");
          p_pestPar(RUNR,PACTCUR,pestoAgg,A,"minRelDamage") = v_pestPar.l(RUNR,PACTCUR,pestoAgg,A,"minRelDamage");

    In this project's notation: cells {key: (ApplPerHa, pdr)} with key = (region, crop, aggregate, technology), only
    cells with a price-damage ratio; a region has one pass per crop with a ratio (CAPRI's loop over (ru, mcact)), each
    pass solving all the region's cells. Returns {key: {the five items, "powerInfes", "status"}}.

    Departures from CAPRI (register DEP-59):
    - Each cell is its own NLP (m_pestiCaliPower over one cell), solved by IPOPT, where CAPRI solves a region's cells
      in one NLP at each pass, and all regions' cells in one NLP at the end, with CONOPT. The objective and the
      equations are separable by cell, so the joint NLP and the cells' NLPs are the same problem (docs/
      DEPARTURES_FROM_CAPRI.md, "Separable NLPs"). IPOPT fails CAPRI's joint form (Austria at 2017: 229 of 645 cells
      within 1e-4 of CAPREG's terms, against 645 cell by cell; the bake-off of 27 November 2026); CONOPT, which solves
      it, needs a licence (the project lead, 27 November 2026: cell by cell with IPOPT).
    - Kept from CAPRI's loop for each cell: the passes over the region's crops, minRelDamage reset at each, the levels
      carried, the retry from the retry's starts, the flag, excl_map after the loop, the last solve from the levels.
      The retry and the flag follow the cell's own solve, not the region's.
    - CAPRI flags a cell of a failed retry where an equation's marginal is non-zero or its level is off its bound
      (CONOPT's infeasible solution); here where an equation's residual exceeds PESTI_CALI_ROW_TOL (IPOPT's
      multipliers at an infeasible end are not CONOPT's phase-1 marginals)."""
    import numpy as np
    keys = list(cells)
    X = {k: np.array([v_pestPar_start_and_bounds(cells[k][1], cells[k][0])[v][0] for v in VARS]) for k in keys}
    infes = {k: 0 for k in keys}
    status = {k: "" for k in keys}
    by_region = {}
    for k in keys:
        by_region.setdefault(k[0], []).append(k)
    for reg, ks in by_region.items():
        for _crop in sorted({k[1] for k in ks}):                      # the loop over (ru, mcact)
            for k in ks:                                              # excl_map is set after the loop only
                X[k][4] = 0.0                                         # minRelDamage reset (l. 333)
                x, ok, st, res = m_pestiCaliPower([cells[k]], [X[k]])
                if not ok:                                            # the retry (l. 345-355)
                    rs = np.array([v_pestPar_start_and_bounds(cells[k][1], cells[k][0], retry=True)[v][0]
                                   for v in VARS])
                    x, ok, st, res = m_pestiCaliPower([cells[k]], [rs])
                    if not ok and res[0] > PESTI_CALI_ROW_TOL:        # infeasible: flag (l. 357-367)
                        infes[k] = 1
                X[k], status[k] = x[0], st
    excl = {(k[0], k[1], k[2]) for k in keys if infes[k]}            # excl_map (l. 384)
    for k in keys:
        if (k[0], k[1], k[2]) in excl:
            continue
        X[k][4] = 0.0                                                 # l. 388
        x, ok, st, res = m_pestiCaliPower([cells[k]], [X[k]])         # the last solve (l. 399)
        X[k], status[k] = x[0], st
    return {k: dict(zip(VARS, (float(v) for v in X[k])), powerInfes=infes[k], status=status[k]) for k in keys}


def p_pestPar_powerDamageFac(SlopLin, SlopExpo, Expon, ApplPerHa, technFact_LEVL=1.0):
    r"""The power function's damage factor at the observed application.

    CAPRI's GAMS (supply/cal_pesti.gms l. 406-410):

          p_pestPar(RUNR,PACTCUR,pestoAgg,A,"powerDamageFac") $ p_technFact(RUNR,PACTCUR,"LEVL",A)
            =  (1 - p_pestPar(RUNR,PACTCUR,pestoAgg,A,"SlopLin")
                  * p_pestPar(runr,pactCur,pestoAgg,A,"ApplPerHa")
                  + p_pestPar(RUNR,PACTCUR,pestoAgg,A,"SlopExpo")
                  * p_pestPar(runr,pactCur,pestoAgg,A,"ApplPerHa")**p_pestPar(RUNR,PACTCUR,pestoAgg,A,"Expon"));

    In this project's notation: 1 - SlopLin a + SlopExpo a^Expon where the technology has a share.

    Departures from CAPRI: none."""
    if not float(technFact_LEVL):
        return 0.0
    a = float(ApplPerHa)
    return 1.0 - float(SlopLin) * a + float(SlopExpo) * a ** float(Expon)


def p_pestPar_PowerUtility(cells_A, endogenous, powerPriceEla):
    r"""The power form's utility for a (region, crop, aggregate): the inverse of the penalties over its technologies
    (elasticity off the prior, remaining damage, negative damage, an infeasible calibration).

    CAPRI's GAMS (supply/cal_pesti.gms l. 472-484):

          p_pestiEla("wgt") = 1;
          p_pestiEla("negwgt") = 1000;
        *
        *      We kick out SUGB, as this crop was never perfectly calibrating (inspite of using p_emr):
          p_pestPar(RUNR,"SUGB",pestoAgg,A,"endogenous") = 0;
        *
          p_pestPar(RUNR,MCACT,pestoAgg,A,"PowerUtility") $  ( p_pestPar(RUNR,MCACT,pestoAgg,A,"powerPriceEla")
                                                             $ p_pestPar(RUNR,MCACT,pestoAgg,A,"endogenous"))
            = 1/ sum(A1,
                        sqr(  p_pestPar(RUNR,MCACT,pestoAgg,A1,"powerPriceEla") - p_pestiEla("prior"))
                    +   p_pestiEla("wgt") * sqr(max(0,p_pestPar(RUNR,MCACT,pestoAgg,A1,"powerDamageFac")))
                    +   p_pestiEla("negwgt") * sqr(min(0,p_pestPar(RUNR,MCACT,pestoAgg,A1,"powerDamageFac")))
                    +   1e+6*p_pestPar(runr,MCACT,pestoAgg,A1,"powerInfes"));

    In this project's notation, for a cell with powerPriceEla and endogenous non-zero: 1 / sum over the technologies
    A1 of the same (region, crop, aggregate) of (pe_A1 - prior)^2 + wgt max(0, dmg_A1)^2 + negwgt min(0, dmg_A1)^2 +
    1e6 powerInfes_A1, with wgt 1, negwgt 1000 (the choice's weights); dmg = powerDamageFac. cells_A: the
    technologies' dicts. Sugar beet's endogenous flag is set to 0 beforehand (l. 476).

    Departures from CAPRI: none."""
    if not (float(powerPriceEla) and int(endogenous)):
        return 0.0
    s = 0.0
    for c in cells_A:
        d = float(c.get("powerDamageFac", 0.0))
        s += ((float(c.get("powerPriceEla", 0.0)) - PESTI_ELA["prior"]) ** 2 + PESTI_ELA_CHOICE["wgt"] * max(0.0, d) ** 2
              + PESTI_ELA_CHOICE["negwgt"] * min(0.0, d) ** 2 + 1e6 * float(c.get("powerInfes", 0)))
    return 1.0 / s if s else 0.0


def choose_form(cell):
    r"""The form kept per cell: the power function where its utility reaches 0.05, else the linear fall-back (Expon set
    to 0, SlopLin its slope); the damage factors at the observed point and the current damage.

    CAPRI's GAMS (supply/cal_pesti.gms l. 490-508):

          p_pestPar(RUNR,MCACT,pestoAgg,A,"Expon")        $ (  p_pestPar(RUNR,MCACT,pestoAgg,A,"PowerUtility") lt .05) = 0;

        * --- Fall back option damage factor (for checking file)
          p_pestPar(RUNR,MCACT,pestoAgg,A,"fudgeDamageFac")      $ p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopFudg")
            =(     (1-p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopFudg")*p_pestPar(runr,mCact,pestoAgg,A,"ApplPerHa"))
              +SQRT(sqr(p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopFudg")*p_pestPar(runr,mCact,pestoAgg,A,"ApplPerHa")-1)
                   +p_pestFudge))/2;
        *
        *     Delete the fall back option parameters if they are not needed...
          p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopFudg")  $ p_pestPar(RUNR,MCACT,pestoAgg,A,"Expon") = 0;
        *
        *     ... but copy the slope to the standard slopLin if needed
          p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopLin") $ (not p_pestPar(RUNR,MCACT,pestoAgg,A,"Expon"))
              = p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopFudg")   ;

          p_pestPar(RUNR,MCACT,pestoAgg,A,"curDamage")
            = p_pestPar(RUNR,MCACT,pestoAgg,A,"maxDamage")
            *( p_pestPar(RUNR,MCACT,pestoAgg,A,"powerDamageFac")  $ (    p_pestPar(RUNR,MCACT,pestoAgg,A,"Expon"))
              +p_pestPar(RUNR,MCACT,pestoAgg,A,"fudgeDamageFac")  $ (not p_pestPar(RUNR,MCACT,pestoAgg,A,"Expon")))  ;

    In this project's notation, on the cell's dict (changed in place and returned): Expon = 0 where PowerUtility <
    0.05; fudgeDamageFac = ((1 - s a) + sqrt((s a - 1)^2 + p_pestFudge)) / 2 with s = SlopFudg where SlopFudg is
    non-zero; SlopFudg = 0 where Expon remains; SlopLin = SlopFudg where Expon is 0; curDamage = maxDamage x
    (powerDamageFac if Expon else fudgeDamageFac).

    Departures from CAPRI: none."""
    if float(cell.get("PowerUtility", 0.0)) < POWER_UTILITY_MIN:
        cell["Expon"] = 0.0
    s, a = float(cell.get("SlopFudg", 0.0)), float(cell.get("ApplPerHa", 0.0))
    if s:
        cell["fudgeDamageFac"] = ((1.0 - s * a) + math.sqrt((s * a - 1.0) ** 2 + P_PESTFUDGE)) / 2.0
    if float(cell.get("Expon", 0.0)):
        cell["SlopFudg"] = 0.0
    else:
        cell["SlopLin"] = float(cell.get("SlopFudg", 0.0))
    cell["curDamage"] = float(cell.get("maxDamage", 0.0)) * (
        float(cell.get("powerDamageFac", 0.0)) if float(cell.get("Expon", 0.0)) else float(cell.get("fudgeDamageFac", 0.0)))
    return cell


def p_pestPar_NoDamageFac(curDamage_by_agg, ApplPerHa_by_agg, technFact_LEVL=1.0):
    r"""The yield factor without damage, so that the yield factor is one at the observed applications.

    CAPRI's GAMS (supply/cal_pesti.gms l. 510-515):

          p_pestPar(RUNR,MCACT,"pestotal",A,"curDamage") = sum(PESTOAGG $ pestCur(pestoAgg), p_pestPar(RUNR,MCACT,pestoAgg,A,"curDamage"));

          p_pestPar(RUNR,MCACT,"yild",A,"NoDamageFac") $ p_technFact(RUNR,MCACT,"LEVL",A) = 1+p_pestPar(RUNR,MCACT,"pestotal",A,"curDamage") ;

          p_pestPar(RUNR,MCACT,"yild",A,"NoDamageFac") $ ( (not p_pestPar(RUNR,MCACT,"yild",A,"NoDamageFac") )
                                                         $ sum(PESTOAGG $ pestCur(pestoAgg),p_pestPar(runr,mCACT,pestoAgg,A,"ApplPerHa")))=1;

    In this project's notation: NoDamageFac = 1 + sum over the aggregates of curDamage where the technology has a
    share; 1 where that is 0 and some aggregate is applied.

    Departures from CAPRI: none."""
    if not float(technFact_LEVL):
        return 0.0
    v = 1.0 + sum(float(d) for d in curDamage_by_agg)
    if not v and any(float(a) for a in ApplPerHa_by_agg):
        v = 1.0
    return v
