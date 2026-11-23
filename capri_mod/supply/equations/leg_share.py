"""CAPRI's increased legume share in temporary grassland (LegSh, target BioFix) as envind/leg_share.gms sets it up
(CAPRI star 3.0; run by capmod.gms l. 1107 with %ghgTechLegSh% on, as in CAPRI's Green Deal runs,
pol_input/greendeal/refpol_endotech_all_sup.gms l. 148): the share v of other arable fodder (OFAR) whose temporary
grassland part, the share 1 - FLEG that is not fodder legumes, has its legume share raised; its biological N fixation
x (1 + othImpact(BioFix) x v) in NUTNED_ (supply/supply_model.gms l. 1111-1112), e_BIOFIX (l. 1456-1457), the
fixation's N2O (GWPN2OFIX_, l. 3761) and its leaching's (l. 3890); its cost per ha of OFAR (GHG_Mit_Cost_, l. 5058-5059).

Used by tools/build/build_legsh_option.py. The cost function per ha of OFAR and per share v,

    (costParLin + pmpParLin) v + 0.5 pmpParSqr v^2,

with CAPRI's miti_data_jul15 parameters of the member state (IniShare 0, MaxShare 1, pmpParLin = Subs0 - costParLin,
pmpParSqr = Subs1 - Subs0), inflated to the simulation year by envind/ghgMiti.gms l. 155-158 and scaled here to the
temporary grassland part (l. 40-42), is GHG_Mit_Cost_ on OFAR's level: equations/supply_model/mitigation.py
GHG_Mit_Cost_legSh. leg_share.gms then adds p_fertCostGains, the value of the N need it removes at the member state's
mineral N price (l. 53-73), to pmpParLin; the model calibrates the linear term with its own value of N instead (DEP-30's
rule, the project lead's decision of 31 October 2026: equations/ghgmiti.py pmpParlin_fertTech_DEP30), so p_fertCostGains
is not ported. Nor is the soil carbon of l. 80-83 (othImpact CO2SEQ, into GLUC; the model has no LULUCF account,
KNOWN_ISSUES K189).
"""
from __future__ import annotations


def othImpact_BioFix_LegSh_full(nfixRate_gras_MS, FLEG_LEVL_BAS, BioFix_FLEG):
    r"""p_ghgMiti(RS, OFAR, LegSh, othImpact, bioFix) before its normalisation: OFAR's fixation rate with the temporary
    grassland's rate raised to at least 0.2 x 0.75 (a legume share of 20% at the legumes' rate) (l. 31-36).

    CAPRI's GAMS (envind/leg_share.gms l. 33-36):

      p_ghgMiti(RS,"OFAR","LegSh","othImpact","bioFix") $ ( sum(map_rr(ms,rs),MitiTech_map(MS,"OFAR","LegSh","bioFix"))
                                                          $ sum(map_rr(ms,rs),p_nfixRate_gras(ms)) )
         =  sum(map_rr(ms,rs),max(0.2*0.75,p_nfixRate_gras(MS))  * (1.-DATA(RS,"FLEG","LEVL","BAS"))
                            + p_nitrFact("RALL","FLEG","BioFix") * (   DATA(RS,"FLEG","LEVL","BAS")));

    In this project's notation, g(m) the member state's grassland rate (p_nfixRate_gras, fert/fertpar.gms l. 265-295),
    s(r) the fodder legume share of OFAR (DATA(r, FLEG, LEVL, BAS)), f(FLEG) the legumes' rate (fertpar.gms l. 235):

        F(r) = max(0.15, g(m)) (1 - s(r)) + f(FLEG) s(r)

    Departures from CAPRI: none."""
    s = float(FLEG_LEVL_BAS)
    return max(0.2 * 0.75, float(nfixRate_gras_MS)) * (1.0 - s) + float(BioFix_FLEG) * s


def LegSh_costPar(costPar_MS, FLEG_LEVL_BAS):
    r"""p_ghgMiti(RS, OFAR, LegSh, bioFix, mitiCostfPars) of a region: the member state's parameter on the temporary
    grassland part of OFAR (l. 38-42).

    CAPRI's GAMS (envind/leg_share.gms l. 40-42):

        p_ghgMiti(RS,"OFAR","LegSh","bioFix",mitiCostfPars) $ sum(map_rr(ms,rs),MitiTech_map(MS,"OFAR","LegSh","bioFix"))
         = sum(map_rr(ms,rs),p_ghgMiti(MS,"OFAR","LegSh","bioFix",mitiCostfPars) * (1.-DATA(RS,"FLEG","LEVL","BAS")))
        ;

    mitiCostfPars: revenue, costParSqr, costParLin, pmpParLin, pmpParSqr, subs0, subs1 (sets.gms l. 9485; the member
    state's values already inflated to the simulation year, envind/ghgMiti.gms l. 155-158, which runs before this file:
    capmod.gms l. 779, 1107). In this project's notation: par(r) = par(m) (1 - s(r)). Departures from CAPRI: none."""
    return float(costPar_MS) * (1.0 - float(FLEG_LEVL_BAS))


def othImpact_BioFix_LegSh(full, p_nitrFact_MS_OFAR_BioFix):
    r"""p_ghgMiti(RS, OFAR, LegSh, othImpact, BioFix): the relative change of OFAR's fixation at v = 1 (l. 44-47).

    CAPRI's GAMS (envind/leg_share.gms l. 45-47):

        p_ghgMiti(RS,"OFAR","LegSh","othImpact","BioFix") $ ( sum(map_rr(ms,rs),MitiTech_map(MS,"OFAR","LegSh","bioFix"))
                                                            $ sum(map_rr(ms,rs),p_nitrFact(MS,"OFAR","BioFix")))
         =   p_ghgMiti(RS,"OFAR","LegSh","othImpact","BioFix") / sum(map_rr(ms,rs),p_nitrFact(MS,"OFAR","BioFix")) - 1;

    In this project's notation, BF(m) = p_nitrFact(m, OFAR, BioFix) = g(m) (1 - s(m)) + f(FLEG) s(m) (fertpar.gms
    l. 300-301; equations/fertpar.py p_nitrFact_BioFix): othImpact(r) = F(r) / BF(m) - 1 (0 where BF(m) = 0, the $
    condition). It is 0 where g(m) >= 0.15. NUTNED_, e_BIOFIX and the fixation's N2O take the member state's value
    (sum over R_RAGG(RUNR, MSACT)). Departures from CAPRI: none."""
    bf = float(p_nitrFact_MS_OFAR_BioFix)
    return float(full) / bf - 1.0 if bf else 0.0


def NUTNED_LegSh_needShare(DATA_OFAR_NITF, BioFix_OFAR, othImpact_BioFix, multFact_NITF, addFact_NITF):
    r"""The share of other arable fodder's N need in NUTNED_ that the legume share removes at v = 1: the LegSh term of
    NUTNED_'s need (supply/supply_model.gms l. 1095-1137) over OFAR's need at v = 0.

    CAPRI's GAMS, NUTNED_'s need per ha of a crop (l. 1100-1124; the whole equation: equations/supply_model/
    nutrients.py NUTNED_):

                * (%data%(RUNR,MCACT,FNUT,"Y")
                   ...
                   * (1-p_nitrFact(RUNR,MCACT,"BioFix") $ SAMEAS(FNUT,"NITF")
        $iftheni.fertn1 %ghgAbatement%==on
                   * sum(R_RAGG(RUNR,MSACT),1. + (  p_ghgMiti(MSACT,MCACT,"LegSh","othImpact","BioFix")
                                                  * v_Miti(RUNR,MCACT,"LegSh","BioFix")) $ SAMEAS(MCACT,"OFAR"))
        $endif.fertn1
                   )
                    * v_cropNutNeedMultFact(RUNR,FNUT,A)
                    + v_cropNutNeedAddFact(RUNR,FNUT))
                   * (p_nitrFact(RUNR,"ALL","DEFR") $ SAMEAS(FNUT,"NITF") + 1 $ (NOT SAMEAS(FNUT,"NITF")))
                   ...

    In this project's notation, D = DATA(r, OFAR, NITF, Y), b = p_nitrFact(r, OFAR, BioFix), o = othImpact (the member
    state's), k = v_cropNutNeedMultFact(r, NITF, A), a = v_cropNutNeedAddFact(r, NITF), and Q the factors common to the
    two parts (the soil factor DEFR, the technology's SQRT(1 + p_technFact(yield, A)) (1 + p_technFact(NITF, A))):

        need(v) = (D (1 - b (1 + o v)) k + a) Q = need(0) (1 - share v),   share = D b o k / (D (1 - b) k + a)

    The same share holds for each technology (CAPRI's k is the same for T, T1 and T2 in sim_ini_21730), so the term is
    the share times OFAR's need columns, the technology mix column's included. At other yields fertned.gms moves D
    alone: the model's need of OFAR moves as (1 - s) r + s, s the additive part's share (NUTNED_needYieldFactor,
    capri_mod/supply/fertilisation.py), and the term takes the columns' part that follows D, r / ((1 - s) r + s) of
    them (the groups' need_yf; capri_regional_nlp's NUTNED_), so it is D(y) b o k Q v as CAPRI's. Until 23 November
    2026 the whole need of OFAR moved as one (register DEP-10 item 1b). Departures from CAPRI: none."""
    D, b, o, k, a = (float(DATA_OFAR_NITF), float(BioFix_OFAR), float(othImpact_BioFix), float(multFact_NITF),
                     float(addFact_NITF))
    den = D * (1.0 - b) * k + a
    return D * b * o * k / den if den > 0 else 0.0
