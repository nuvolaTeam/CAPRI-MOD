r"""CAPRI's air and water block (supply/supply_model.gms l. 3455-3616): NH3 (NH3MAN_, NH3APP_, NH3GRA_, NH3TOT_),
NOx (NOXMAN_, NOXAPP_, NOXGRA_, NOXTOT_) and NO3 (NO3LEA_, NO3RUN_) from agriculture.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview, notation and departures.

Definitional rows in CAPRI's supply model (binding only under an NH3 or NO3 tax or target, off in the Green Deal step);
the model computes them in the accounts after the solve (environmental/ammonia.py compute_ammonia, environmental/
nitrogen.py leaching with supply/n_leaching.py crop_n), option A as the methane block (methane.py).

Not in the model: NOXMAN_ (l. 3526-3539), NOXAPP_ (l. 3542-3555), NOXGRA_ (l. 3559-3572) and NOXTOT_ (l. 3577-3581):
the accounts report no NOx; the loss cascade's NOx shares (n_flow.py) enter the N losses and the mineral N's
indirect N2O (n2o.py GWPN2OSYN_), not an NOx item. A finding for the main line.

In this project's notation (kt N; NH3 x 17/14):

    NH3MAN_ + NH3APP_ + NH3GRA_   sum_a s_a x N_a          s_a CAPRI's 2030 share of the animal's excreted N lost as
                                                           NH3-N over housing, storage, application and grazing
                                                           (GNH3 / MANN; nh3_factors_capri.csv), N_a its excreted N
    NH3TOT_                        the manure's + m x M     m CAPRI's 2030 NH3MIN / MINFER, M the mineral N
    NO3RUN_                        M x RunTot_NETF + sum_a N_a x RunSurf_a
    NO3LEA_                        by source: M (1 - GasRunTot_NETF - e) L + [sum_a N_a (1 - GasRunTot_a - e) - MTRADE
                                   (1 - e)] L + (ATMOSD + CRESID)(1 - N2O_NETF - e) L + BIOFIX (1 - e) L

Departures from CAPRI: the manure NH3 takes CAPRI's 2030 shares, the stages summed, the options' effects added
afterwards (environmental_module.py: the N the ammonia options keep, the inhibitor on manure), without the lowNFeed,
genet_eff and genet_yld factors on MANN; the mineral NH3 share is CAPRI's 2030 ratio, rescaled by the fertiliser
options' factor (fert_side_factors); NO3RUN_'s manure term is the surface runoff (CAPRI: RunTot, the housing runoff
included; the model's housing runoff is in the manure N2O factors, n2o.py GWPN2OMAN_); NO3LEA_ is computed by source,
as CAPRI's accounts allocate it to the crops (envind/gases.gms l. 696-745), not as CAPRI's v_nutSurSoiKt x
v_nitrBalance(Leach) (e = EXPPRD / IMPORT of CAPRI's 2030 reference).
"""
from __future__ import annotations

from capri_mod.units import M_NH3, M_NH3_N


def NH3MAN_(share, N_excr, v_actLevl):
    r"""NH3MAN_(r) (l. 3459-3472) with NH3APP_ (l. 3475-3488) and NH3GRA_ (l. 3492-3505), for one animal: CAPRI's
    share of the excreted N lost as NH3-N over the stages x the N excreted per head (kg) x the level (1000 head) x 1000
    / 1e6, kt NH3-N.

    CAPRI's GAMS, NH3MAN_ (l. 3459-3472):

        NH3MAN_(RUNR)  ..
    *
            v_NH3NOXEmis(RUNR,"NH3MAN") =E=
    *
               SUM( (MAACT,A) $ ( p_technFact(RUNR,MAACT,"LEVL",A) ),  v_actLevl(RUNR,MAACT,A)
    *                    - consider a possible modification of MANN and hence EMISCALC by mitigation option lowNFeed:
                      * (  (1+v_Miti(RUNR,MAACT,"lowNFeed","N2OEXCR")*p_ghgMiti(RUNR,MAACT,"lowNFeed","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option rumFedEff
                         * (1+v_Miti(RUNR,MAACT,"genet_eff","rumFedEff")*p_ghgMiti(RUNR,MAACT,"genet_eff","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option mlkYld
                         * (1+v_Miti(RUNR,MAACT,"genet_yld","mlkYld")*p_ghgMiti(RUNR,MAACT,"genet_yld","othImpact","MANN")))
                            * %data%(RUNR,MAACT,"MANN","Y")* (p_technFact(RUNR,MAACT,"MANN","T")+1.)
                                   * (v_emiloss(RUNR,MAACT,"NH3","Hous") + v_emiloss(RUNR,MAACT,"NH3","Stor"))) * 0.001;

    NH3APP_ (l. 3475-3488):

        NH3APP_(RUNR)  ..
    *
            v_NH3NOXEmis(RUNR,"NH3APP") =E=
    *
               SUM( (MAACT,A) $ ( p_technFact(RUNR,MAACT,"LEVL",A) ),  v_actLevl(RUNR,MAACT,A)
    *                    - consider a possible modification of MANN and hence EMISCALC by mitigation option lowNFeed:
                      * (1+v_Miti(RUNR,MAACT,"lowNFeed","N2OEXCR")*p_ghgMiti(RUNR,MAACT,"lowNFeed","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option rumFedEff
                      * (1+v_Miti(RUNR,MAACT,"genet_eff","rumFedEff")*p_ghgMiti(RUNR,MAACT,"genet_eff","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option mlkYld
                      * (1+v_Miti(RUNR,MAACT,"genet_yld","mlkYld")*p_ghgMiti(RUNR,MAACT,"genet_yld","othImpact","MANN"))
                      *  %data%(RUNR,MAACT,"MANN","Y")* (p_technFact(RUNR,MAACT,"MANN","T")+1.)
                                   * v_emiloss(RUNR,MAACT,"NH3","Appl")) * 0.001;

    NH3GRA_ (l. 3492-3505):

        NH3GRA_(RUNR) ..
    *
            v_NH3NOXEmis(RUNR,"NH3GRA") =E=
    *
               SUM( (MAACT,A) $ ( p_technFact(RUNR,MAACT,"LEVL",A) ),  v_actLevl(RUNR,MAACT,A)
    *                    - consider a possible modification of MANN and hence EMISCALC by mitigation option lowNFeed:
                      * (1+v_Miti(RUNR,MAACT,"lowNFeed","N2OEXCR")*p_ghgMiti(RUNR,MAACT,"lowNFeed","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option rumFedEff
                      * (1+v_Miti(RUNR,MAACT,"genet_eff","rumFedEff")*p_ghgMiti(RUNR,MAACT,"genet_eff","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option mlkYld
                      * (1+v_Miti(RUNR,MAACT,"genet_yld","mlkYld")*p_ghgMiti(RUNR,MAACT,"genet_yld","othImpact","MANN"))
                      *  %data%(RUNR,MAACT,"MANN","Y")* (p_technFact(RUNR,MAACT,"MANN","T")+1.)
                                   * v_emiloss(RUNR,MAACT,"NH3","Graz")) * 0.001;
    """
    return share * N_excr * v_actLevl * 1000 / 1e6


def NH3TOT_min(share, M_kt):
    r"""NH3TOT_'s mineral term (l. 3510-3514): the mineral N (kt) x its NH3-N share (CAPRI's v_emiLoss(NETF, NH3,
    GasTot); the accounts: CAPRI's 2030 NH3MIN / MINFER), kt NH3-N. CAPRI's GAMS: NH3TOT_'s docstring."""
    return share * M_kt


def NH3TOT_(man_n, min_n):
    r"""NH3TOT_(r) (l. 3510-3514) in kt NH3: (the manure's NH3-N + the mineral N's) x 17/14.

    CAPRI's GAMS, NH3TOT_ (l. 3510-3514):

        NH3TOT_(RUNR) ..
    *
            v_NH3NOXEmis(RUNR,"NH3TOT") =E= v_NH3NOXEmis(RUNR,"NH3GRA") + v_NH3NOXEmis(RUNR,"NH3MAN") + v_NH3NOXEmis(RUNR,"NH3APP")
    * ---   effect of nitrification inhibitors should be checked!!!!!!!!!!!!!!!!!!
                                          - v_netPutQuant(RUNR,"NITF") * v_emiLoss(RUNR,"NETF","NH3","GasTot");
    """
    return (man_n + min_n) * M_NH3 / M_NH3_N


def NO3RUN_(mineral, run_tot_netf, manure_terms):
    r"""NO3RUN_(r) (l. 3600-3609) by source, t N: {"min_run": the mineral N x RunTot_NETF, "man_run": sum_a N_a x
    RunSurf_a}; manure_terms [(N_a, RunSurf_a, GasRunTot_a)] (n_leaching.crop_n's).

    CAPRI's GAMS, NO3RUN_ (l. 3600-3609):

        NO3RUN_(RUNR)..
           v_NO3Emis(RUNR,"NO3RUN") =E=
               SUM( (MAACT,A) $ ( p_technFact(RUNR,MAACT,"LEVL",A) ),  v_actLevl(RUNR,MAACT,A)
               * %data%(RUNR,MAACT,"MANN","Y")* (p_technFact(RUNR,MAACT,"MANN","T")+1.)
                                   * (v_emiloss(RUNR,MAACT,"N","Runtot"))) * 0.001
              - v_netPutQuant(RUNR,"NITF") * v_emiLoss(RUNR,"NETF","N","RunTot");
    """
    return {"min_run": mineral * run_tot_netf,
            "man_run": sum(n * rs_ for n, rs_, _ in manure_terms)}


def NO3LEA_(mineral, grt_netf, n2o_netf, manure_terms, mtrade, dep_res, fixation, L, e):
    r"""NO3LEA_(r) (l. 3592-3596) by source, t N, as CAPRI's accounts allocate it (envind/gases.gms l. 696-745): the
    mineral N's, the manure's (net of the manure trade), the deposition's and residues', the fixation's, each x the
    leaching share L (LEACHN_, n_flow.py) and (1 - e), e = EXPPRD / IMPORT of CAPRI's 2030 reference.

    CAPRI's GAMS, NO3LEA_ (l. 3592-3596):

        NO3LEA_(RUNR)..
           v_NO3Emis(RUNR,"NO3LEA") =E=
               v_nutSurSoiKt(RUNR,"NITF") * v_nitrBalance(RUNR,"Leach");
    """
    return {"min_lea": mineral * (1.0 - grt_netf - e) * L,
            "man_lea": (sum(n * (1.0 - g - e) for n, _, g in manure_terms) - mtrade * (1.0 - e)) * L,
            "dep_lea": dep_res * (1.0 - n2o_netf - e) * L,
            "fix_lea": fixation * (1.0 - e) * L}
