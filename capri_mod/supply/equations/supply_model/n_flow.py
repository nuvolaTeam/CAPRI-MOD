r"""CAPRI's nitrogen flow (supply/supply_model.gms l. 3206-3471, ghgAbatement on): the loss cascade of the manure N of
each animal activity (GRAZN_, HOUSN_, STORN_, RUNHOUSN_, RUNSURFN_, APPLN_, RUNTOTN_, GASRUNTOTN_) and of mineral
fertiliser (GASTOTNETF_, RUNTOTNETF_, GASRUNTOTNETF_), CAPRI's v_emiLoss as fractions of the N excreted or of the
mineral N bought; docs/N_CASCADE_SPEC.md has the factors (p_Nemidat) with their sources; and the leaching of the soil
surplus (LEACHN_ with AMMOAGG_). Written so far: the cascade (moved from capri_mod/supply/n_cascade.py on 19 November
2026, unchanged); LEACHN_, its first factor LEACHN_B1 and AMMOAGG_ (moved the same day from capri_mod/supply/
n_leaching.py and the accounts, capri_mod/environmental/nitrogen.py, unchanged). e_nitrBal_ (l. 3464-3466: leaching,
accumulation and mineralisation add up to the soil surplus) is not written: the model computes no accumulation.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview, notation and departures.

In this project's notation (one animal activity; g a gas NH3, NOX, N2O, and N2 at storage; tsg the grazing share
p_Nemidat(N, TypeShare, Graz); s_t the option shares v_Miti, e_t,item their othImpact; ad the anaerobic digestion
share):

    GRAZN_     L(g, Graz) = tsg x graz_g
    HOUSN_     L(g, Hous) = (1 - tsg [- L(NH3, Hous) - L(NOX, Hous) for N2O]) x hous_g x (1 - sum_t e_t,gHOU s_t)
                            [x (1 - ad e_AD,N2OHOU) for N2O]
    STORN_     L(g, Stor) = (1 - tsg - sum_g L(g, Hous) [- L(NH3, Stor) - L(NOX, Stor) for N2]) x stor_g
                            x (1 - sum_t e_t,gSTO s_t) [x (1 - ad e_AD,gSTO) for NH3, NOX]
    RUNHOUSN_  L(N, RunHous) = (1 - tsg - sum L(Hous) - sum L(Stor)) x run_hous x (1 - sum_t e_t,no3runh s_t)
    RUNSURFN_  L(N, RunSurf) = (tsg (1 - sum L(Graz)) + left) x run_surf x (a - sum_t e_t,no3mrun s_t) x b
    APPLN_     L(g, Appl) = (left [- L(NH3, Appl) - L(NOX, Appl) for N2O]) x (1 - run_surf x m_appl)
                            x appl_g x (1 - sum_t e_t,gAPP s_t - fert_g [- e_AD,N2OAPP ad for N2O])
    RUNTOTN_   L(N, RunTot) = L(N, RunHous) + L(N, RunSurf)
    GASRUNTOTN_  L(N, GasRunTot) = sum_g,stage L(g, stage) + L(N, RunHous) + L(N, RunSurf)
    GASTOTNETF_  L(NH3) = netf_NH3 (1 - urea e_urea - fert_NH3), L(NOX) = netf_NOX (1 - fert_NOX),
                 L(N2O) = (1 - L(NH3) - L(NOX)) netf_N2O (1 - fert_N2O - till_N2O)
    RUNTOTNETF_  L(RunTot) = (1 - sum_g L(g)) x run_surf x m_run
    GASRUNTOTNETF_  L(GasRunTot) = sum_g L(g) + L(RunTot)

with left = 1 - tsg - sum L(Hous) - sum L(Stor) - L(N, RunHous); a, b RUNSURFN_'s crop factors (a = 1 - winter cover -
tillage - fertiliser options, b = 1 - buffer strips - biodiversity), m_appl APPLN_'s crop factor on the runoff,
fert_g the fertiliser options' terms (shares + AECM initial shares) x effect.

The leaching share of the region's soil surplus (the accounts compute it after the solve, capri_mod/environmental/
nitrogen.py leaching):

    LEACHN_    L = leach_base x B1 x B2
               B1 = 1 - 0.35 wc - nminSh x sum_fert s x e_SLEA - nmanSh x sum_fert s x e_MLEA - agg     (LEACHN_B1)
               B2 = 1 - the tillage, buffer strip, biodiversity and biochar terms (options the model has not)
    AMMOAGG_   agg = v_ammoAppLeaAgg = sum_a N_a (1 - GasRunTot_a) x sum_{AmmAppLE, AmmAppHE} no3mlea x s
                                       / sum_a N_a (1 - GasRunTot_a)

with wc the winter cover share (its effect 0.35: WINTERCOV_NO3_REDUCTION, envind/cover_crops.gms l. 402), nminSh and
nmanSh the mineral and manure shares of the N input (nminInputSh_, nmanInputSh_: n_surplus.py's block), e_SLEA =
1 - (1 - lit) (1 + NMIN) the fertiliser options' effect (ghgMiti.gms l. 552-563; NMAN for manure;
capri_mod/supply/n_leaching.py fert_effect), N_a the N excreted by animal a.

Arguments of the functions
  f       p_Nemidat of the region and animal activity: tsg, graz_<g>, hous_<g>, stor_<g>, appl_<g>, run_hous
          (tools/build/build_n_cascade.py, n_cascade_factors.csv)
  run_surf  p_Nemidat(RUNR, MAACT, "N", "Runoff", "Surf") (n_cascade_region.csv; 0 where the activity has no base level)
  sh      the animal's option shares v_Miti {tech: share} (missing = 0)
  eff     the options' othImpact {(tech, item): value}, items as CAPRI's (NH3HOU, NOXHOU, N2OHOU, N2HOU, NH3STO, ...,
          no3runh, no3mrun)
  m_runsurf   RUNSURFN_'s crop factors (a, b); the application options' own no3mrun is taken off a here
  m_appl_run  APPLN_'s crop factor on the runoff from the surface: (1 - winter cover - NoTill - fertiliser options) x
          (1 - buffer strips - biodiversity)
  fert_appl   APPLN_'s fertiliser-option terms by gas (sum over AllTechFert of (shares + AECM initial) x effect)
Every function takes plain arithmetic, so it evaluates with floats (accounts, checks) and with CasADi symbols (the
regional NLP) alike.

Departures from CAPRI: none in the equations. CAPRI's own code is kept where it reads oddly (REGISTERED,
docs/N_CASCADE_SPEC.md section 4):
  * HOUSN_ sums only LowEmHous, AirPur, AirPurCovLow, AirPurCovLowC, AirPurCovHigh and ManAcid, so the storage covers'
    N2O effect, moved by ammo_tech.gms (l. 2236) from N2OSTO to N2OHOU, does not act;
  * STORN_ takes NH3 + NOX off before N2 only (N2O at storage is 0 by data);
  * APPLN_ takes NH3 + NOX off for N2O inside the bracket multiplied by (1 - runoff).
The options' terms with a zero effect are left out of the sums (_terms; e x share = 0 exactly).

Departures from CAPRI in the leaching (docs/CAPRI_DEPARTURES_REGISTER.md):
  * B2 is held at CAPRI's Green Deal 'ini' reference: L = leach_ini x B1 / B1_ini (B1_ini at CAPRI's initial shares
    and the base winter cover). REGISTERED.
  * CAPRI-ERROR-FIX (the project lead's decision, 20 October 2026; FIX-2): CAPRI adds agg in LEACHN_ ("+
    v_ammoAppLeaAgg", l. 3430) while it subtracts the same options' runoff effect in RUNSURFN_ and the fertiliser
    options' leaching effects in LEACHN_. Its literature table gives reductions (prep_data_LitRev.gms p_reducGains:
    positive = less loss; LNA_low liquid: NH3 0.51, RunSurf -0.24, Leach -0.24), copied without change of sign to
    no3mlea (ammo_tech.gms l. 2293), so with the '+' low-emission application lowers the leaching share where the data
    say it raises it. The model subtracts it (the setting environment.ammapp_sign = "consistent", the default);
    "capri" reproduces CAPRI's code. The base is calibrated to CAPRI's realised share either way (leach_ini), so the
    sign acts only through changes in the options' adoption.
"""
from __future__ import annotations

GASES = ("NH3", "NOX", "N2O")
NMAT = ("N2O", "NH3", "NOX", "N2")
# the ammonia technologies each stage's equation names: CAPRI writes these lists inside its equations (HOUSN_,
# STORN_, RUNHOUSN_, APPLN_: supply/supply_model.gms l. 3217-3344), so they stay the equations' terms here (the project
# lead's decision); tools/build/build_code_lists.py checks each name against CAPRI's MitiTechAmm
HOUS_TECHS = ("LowEmHous", "AirPur", "AirPurCovLow", "AirPurCovLowC", "AirPurCovHigh", "ManAcid")
STOR_TECHS = ("CovStorLow", "CovStorLowCon", "CovStorHigh", "AirPurCovLow", "AirPurCovLowC", "AirPurCovHigh",
              "LowEmHous", "ManAcid")
RUNH_TECHS = ("LowEmHous", "CovStorLow", "CovStorLowCon", "CovStorHigh", "ManStorCon", "AirPurCovLowC",
              "AirPurCovHigh")
APPL_TECHS = ("AmmAppHE", "AmmAppLE")


def _s(sh, t):
    return sh.get(t, 0.0)


def _e(eff, t, item):
    return eff.get((t, item), 0.0)


_NZ = {}


def _terms(eff, techs, item):
    """The options of techs with a nonzero effect on item, with that effect: ((tech, effect), ...), cached per effect
    table. A zero effect adds e x share = 0 exactly (CasADi drops such terms too), so leaving them out of the sums below
    changes no result; it spares most of the cascade's work (27 October 2026: the cascade was 28% of a regional solve)."""
    k = (id(eff), techs, item)
    v = _NZ.get(k)
    if v is None or v[0] is not eff:
        v = (eff, tuple((t, eff[(t, item)]) for t in techs if eff.get((t, item), 0.0) != 0.0))
        _NZ[k] = v
    return v[1]


def GRAZN_(L, f, tsg):
    """GRAZN_ (l. 3209-3213): the losses at grazing, L(g, Graz) = tsg x graz_g; N2 none.

    CAPRI's GAMS, GRAZN_ (l. 3209-3213):

               GRAZN_(RUNR,MAACT,emmat_N)..
               v_emiloss(RUNR,MAACT,emmat_N,"Graz") =E=   sum(R_RAGG(RUNR,MSACT), p_Nemidat(MSACT,MAACT,"N","TypeShare","Graz")
                                                    * p_Nemidat(MSACT,MAACT,emmat_N,"LossHous","Graz"));
    """
    for g in GASES:
        L[(g, "Graz")] = tsg * f.get(f"graz_{g}", 0.0)
    L[("N2", "Graz")] = 0.0


def HOUSN_(L, f, sh, eff, tsg, ad):
    """HOUSN_ (l. 3217-3235): the losses in housing, NH3 and NOX first, N2O after their removal; N2 none.

    CAPRI's GAMS, HOUSN_ (l. 3217-3235):

               HOUSN_(RUNR,MAACT,emmat_N)..
               v_emiloss(RUNR,MAACT,emmat_N,"Hous") =E=  sum(R_RAGG(RUNR,MSACT), (1. - p_Nemidat(MSACT,MAACT,"N","TypeShare","Graz")
                                                     - (v_emiloss(RUNR,MAACT,"NH3","Hous") + v_emiloss(RUNR,MAACT,"NOX","Hous")) $ sameas(emmat_N,"N2O") )
                                                    * p_Nemidat(MSACT,MAACT,emmat_N,"LossHous","av")
                                                    * (1 - sum(mitihous $  map_gas_tag(emmat_N,mitihous),
                                                         + p_ghgMiti(RUNR,MAACT,"LowEmHous","othImpact",mitihous) * v_Miti(RUNR,MAACT,"LowEmHous","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"AirPur","othImpact",mitihous) * v_Miti(RUNR,MAACT,"AirPur","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"AirPurCovLow","othImpact",mitihous) * v_Miti(RUNR,MAACT,"AirPurCovLow","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"AirPurCovLowC","othImpact",mitihous) * v_Miti(RUNR,MAACT,"AirPurCovLowC","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"AirPurCovHigh","othImpact",mitihous) * v_Miti(RUNR,MAACT,"AirPurCovHigh","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"ManAcid","othImpact",mitihous) * v_Miti(RUNR,MAACT,"ManAcid","NH3MAN")))
                                                    * (1-(v_Miti(RUNR,MAACT,"Ad_AnCh","CH4MAN")
                                                    * p_ghgMiti(RUNR,MAACT,"AD_AnCh","OthImpact","N2OHOU")) $ sameas(emmat_N,"N2O")));
    """
    for g in ("NH3", "NOX", "N2O"):
        tag = f"{g}HOU"
        base = 1.0 - tsg
        if g == "N2O":
            base = base - (L[("NH3", "Hous")] + L[("NOX", "Hous")])
        red = 0.0
        for t, e in _terms(eff, HOUS_TECHS, tag):
            red = red + e * _s(sh, t)
        v = base * f.get(f"hous_{g}", 0.0) * (1.0 - red)
        if g == "N2O":
            v = v * (1.0 - ad * _e(eff, "AD_AnCh", "N2OHOU"))
        L[(g, "Hous")] = v
    L[("N2", "Hous")] = 0.0


def STORN_(L, f, sh, eff, tsg, ad, hous):
    """STORN_ (l. 3239-3259): the losses in storage, N2 after NH3 and NOX; hous = the housing losses' sum.

    CAPRI's GAMS, STORN_ (l. 3239-3259):

               STORN_(RUNR,MAACT,nmat)..
               v_emiloss(RUNR,MAACT,nmat,"Stor") =E= sum(R_RAGG(RUNR,MSACT), (1. - p_Nemidat(MSACT,MAACT,"N","TypeShare","Graz")
                                                    - SUM(emmat_N, v_emiLoss(RUNR,MAACT,emmat_N,"Hous"))
                                                    - (v_emiloss(RUNR,MAACT,"NH3","Stor") + v_emiloss(RUNR,MAACT,"NOX","Stor")) $ sameas(nmat,"N2"))
                                                     * p_Nemidat(MSACT,MAACT,nmat,"LossStor","av")
                                                     * (1 - sum(mitistor $  map_gas_tag(nmat,mitistor),
                                                         + p_ghgMiti(RUNR,MAACT,"CovStorLow","othImpact",mitistor) * v_Miti(RUNR,MAACT,"CovStorLow","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"CovStorLowCon","othImpact",mitistor) * v_Miti(RUNR,MAACT,"CovStorLowCon","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"CovStorHigh","othImpact",mitistor) * v_Miti(RUNR,MAACT,"CovStorHigh","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"AirPurCovLow","othImpact",mitistor) * v_Miti(RUNR,MAACT,"AirPurCovLow","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"AirPurCovLowC","othImpact",mitistor) * v_Miti(RUNR,MAACT,"AirPurCovLowC","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"AirPurCovHigh","othImpact",mitistor) * v_Miti(RUNR,MAACT,"AirPurCovHigh","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"LowEmHous","othImpact",mitistor) * v_Miti(RUNR,MAACT,"LowEmHous","NH3MAN")
                                                         + p_ghgMiti(RUNR,MAACT,"ManAcid","othImpact",mitistor) * v_Miti(RUNR,MAACT,"ManAcid","NH3MAN")))
                                                     * (1 - (v_Miti(RUNR,MAACT,"Ad_AnCh","CH4MAN")
                                                      * (p_ghgMiti(RUNR,MAACT,"AD_AnCh","OthImpact","NH3STO") $ sameas(nmat,"NH3")
                                                       + p_ghgMiti(RUNR,MAACT,"AD_AnCh","OthImpact","NOXSTO") $ sameas(nmat,"NOX")))));
    """
    for g in ("NH3", "NOX", "N2", "N2O"):
        tag = f"{g}STO"
        base = 1.0 - tsg - hous
        if g == "N2":
            base = base - (L[("NH3", "Stor")] + L[("NOX", "Stor")])
        red = 0.0
        for t, e in _terms(eff, STOR_TECHS, tag):
            red = red + e * _s(sh, t)
        v = base * f.get(f"stor_{g}", 0.0) * (1.0 - red)
        if g in ("NH3", "NOX"):
            v = v * (1.0 - ad * _e(eff, "AD_AnCh", tag))
        L[(g, "Stor")] = v


def RUNHOUSN_(L, f, sh, eff, tsg, hous, stor):
    """RUNHOUSN_ (l. 3263-3278): the runoff from housing and storage.

    CAPRI's GAMS, RUNHOUSN_ (l. 3263-3278):

               RUNHOUSN_(RUNR,MAACT)..
               v_emiloss(RUNR,MAACT,"N","RunHous") =E= sum(R_RAGG(RUNR,MSACT),(1. - p_Nemidat(MSACT,MAACT,"N","TypeShare","Graz")
                                                    - SUM(emmat_N1, v_emiLoss(RUNR,MAACT,emmat_N1,"Hous"))
                                                    - SUM(nmat, v_emiLoss(RUNR,MAACT,nmat,"Stor")))
                                                     * p_Nemidat(RUNR,MAACT,"N","Runoff","av")
                                                     * (1 - p_ghgMiti(RUNR,MAACT,"LowEmHous","othImpact","no3runh") * v_Miti(RUNR,MAACT,"LowEmHous","NH3MAN")
                                                          - p_ghgMiti(RUNR,MAACT,"CovStorLow","othImpact","no3runh") * v_Miti(RUNR,MAACT,"CovStorLow","NH3MAN")
                                                          - p_ghgMiti(RUNR,MAACT,"CovStorLowCon","othImpact","no3runh") * v_Miti(RUNR,MAACT,"CovStorLowCon","NH3MAN")
                                                          - p_ghgMiti(RUNR,MAACT,"CovStorHigh","othImpact","no3runh") * v_Miti(RUNR,MAACT,"CovStorHigh","NH3MAN")
                                                          - p_ghgMiti(RUNR,MAACT,"ManStorCon","othImpact","no3runh") * v_Miti(RUNR,MAACT,"ManStorCon","NH3MAN")
                                                          - p_ghgMiti(RUNR,MAACT,"AirPurCovLowC","othImpact","no3runh") * v_Miti(RUNR,MAACT,"AirPurCovLowC","NH3MAN")
                                                          - p_ghgMiti(RUNR,MAACT,"AirPurCovHigh","othImpact","no3runh") * v_Miti(RUNR,MAACT,"AirPurCovHigh","NH3MAN")));
    """
    red = 0.0
    for t, e in _terms(eff, RUNH_TECHS, "no3runh"):
        red = red + e * _s(sh, t)
    L[("N", "RunHous")] = (1.0 - tsg - hous - stor) * f.get("run_hous", 0.0) * (1.0 - red)


def RUNSURFN_(L, sh, eff, tsg, graz, left, run_surf, m_runsurf):
    """RUNSURFN_ (l. 3283-3307): the runoff from grazing and application; the application options' own runoff effect
    enters the first crop factor.

    CAPRI's GAMS, RUNSURFN_ (l. 3283-3307):

               RUNSURFN_(RUNR,MAACT)..
               v_emiloss(RUNR,MAACT,"N","RunSurf") =E= sum(R_RAGG(RUNR,MSACT), ( p_Nemidat(MSACT,MAACT,"N","TypeShare","Graz")
                                                    *(1.- SUM(emmat_N1, v_emiLoss(RUNR,MAACT,emmat_N1,"Graz")))
                                                    +(1. - p_Nemidat(MSACT,MAACT,"N","TypeShare","Graz")
                                                    - SUM(nmat, v_emiLoss(RUNR,MAACT,nmat,"Hous")
                                                                    +v_emiLoss(RUNR,MAACT,nmat,"Stor") )
                                                    - v_emiLoss(RUNR,MAACT,"N","RunHous")))
                                                    * p_Nemidat(RUNR,MAACT,"N","Runoff","Surf")
                                                    * (1 - sum(mitiTechCov,p_ghgMiti(RUNR,"catc",mitiTechCov,"othImpact","no3mrun") * v_Miti(RUNR,"CATC",mitiTechCov,"CO2SEQ"))
                                                         - sum(mitiTechTill,p_ghgMiti(RUNR,"cropMiti",mitiTechTill,"othImpact","no3mrun") * v_Miti(RUNR,"cropMiti",mitiTechTill,"CO2SEQ"))
                                                         - sum(AllTechFert,(v_Miti(RUNR,"CropMiti",AllTechFert,"N2OMAN") + v_Miti(RUNR,"CropMiti",AllTechFert,"N2OMAN2")
                                                                           + p_ghgMiti(RUNR,"cropMiti",AllTechFert,"n2oman","iniShareAECM"))
                                                            * (p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","no3mrun")
                                                            + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","no3mrun") $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","no3mrun"))))
                                                         - p_ghgMiti(RUNR,MAACT,"AmmAppHE","othImpact","no3mrun") * v_Miti(RUNR,MAACT,"AmmAppHE","NH3APP")
                                                         - p_ghgMiti(RUNR,MAACT,"AmmAppLE","othImpact","no3mrun") * v_Miti(RUNR,MAACT,"AmmAppLE","NH3APP"))
                                                    * (1 - sum(mitiTechBuff, p_ghgMiti(RUNR,"cropMiti",mitiTechBuff,"othImpact","no3mrun") * v_Miti(RUNR,"cropMiti",mitiTechBuff,"no3man"))
                                                         - sum(mitiTechBiod, p_ghgMiti(RUNR,"cropMiti",mitiTechBiod,"othImpact","no3run") * v_Miti(RUNR,"cropMiti",mitiTechBiod,"BioDiv"))));
    """
    app_run = 0.0
    for t, e in _terms(eff, APPL_TECHS, "no3mrun"):
        app_run = app_run + e * _s(sh, t)
    L[("N", "RunSurf")] = (tsg * (1.0 - graz) + left) * run_surf * (m_runsurf[0] - app_run) * m_runsurf[1]


def APPLN_(L, f, sh, eff, ad, left, ro, fert_appl):
    """APPLN_ (l. 3312-3344): the losses at application, N2O after NH3 and NOX inside the bracket; ro = 1 - run_surf
    x m_appl_run; N2 none.

    CAPRI's GAMS, APPLN_ (l. 3312-3344):

               APPLN_(RUNR,MAACT,emmat_N)..
               v_emiloss(RUNR,MAACT,emmat_N,"Appl") =E= sum(R_RAGG(RUNR,MSACT), (1. - p_Nemidat(MSACT,MAACT,"N","TypeShare","Graz")
                                                    - SUM(nmat, v_emiLoss(RUNR,MAACT,nmat,"Hous")
                                                                    +v_emiLoss(RUNR,MAACT,nmat,"Stor") )
                                                    - v_emiLoss(RUNR,MAACT,"N","RunHous")
                                                    - (v_emiloss(RUNR,MAACT,"NH3","Appl") + v_emiloss(RUNR,MAACT,"NOX","Appl")) $ sameas(emmat_N,"N2O") )
                                                    * (1. - p_Nemidat(RUNR,MAACT,"N","Runoff","Surf")
                                                    * (1 - sum(mitiTechCov,p_ghgMiti(RUNR,"catc",mitiTechCov,"othImpact","no3mrun") * v_Miti(RUNR,"CATC",mitiTechCov,"CO2SEQ"))
                                                         - p_ghgMiti(RUNR,"cropMiti","NoTill","othImpact","no3mrun") * v_Miti(RUNR,"cropMiti","NoTill","CO2SEQ")
                                                         - sum(AllTechFert,(v_Miti(RUNR,"CropMiti",AllTechFert,"N2OMAN") + v_Miti(RUNR,"CropMiti",AllTechFert,"N2OMAN2")
                                                                           + p_ghgMiti(RUNR,"cropMiti",AllTechFert,"n2oman","iniShareAECM"))
                                                            * (p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","no3mrun")
                                                            + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","no3mrun") $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","no3mrun")))))
                                                    * (1 - sum(mitiTechBuff, p_ghgMiti(RUNR,"cropMiti",mitiTechBuff,"othImpact","no3mrun") * v_Miti(RUNR,"cropMiti",mitiTechBuff,"no3man"))
                                                         - sum(mitiTechBiod, p_ghgMiti(RUNR,"cropMiti",mitiTechBiod,"othImpact","no3run") * v_Miti(RUNR,"cropMiti",mitiTechBiod,"BioDiv"))))
                                                    *  p_Nemidat(MSACT,MAACT,emmat_N,"LossAppl","av")
                                                    * (1 - sum(mitiappl $  map_gas_tag(emmat_N,mitiappl),
                                                         + p_ghgMiti(RUNR,MAACT,"AmmAppHE","othImpact",mitiappl) * v_Miti(RUNR,MAACT,"AmmAppHE","NH3APP")
                                                         + p_ghgMiti(RUNR,MAACT,"AmmAppLE","othImpact",mitiappl) * v_Miti(RUNR,MAACT,"AmmAppLE","NH3APP"))
                                                         - sum(AllTechFert,(v_Miti(RUNR,"CropMiti",AllTechFert,"N2OMAN") + v_Miti(RUNR,"CropMiti",AllTechFert,"N2OMAN2")
                                                                           + p_ghgMiti(RUNR,"cropMiti",AllTechFert,"n2oman","iniShareAECM"))
                                                           * ((p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","N2OAPP")
                                                           + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","N2OAPP") $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","N2OAPP"))) $ (sameas(emmat_N,"n2o"))
                                                           + (p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NH3APP")
                                                           + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","NH3APP") $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NH3APP"))) $ (sameas(emmat_N,"nh3"))
                                                           + (p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NOXAPP")
                                                           + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","NOXAPP") $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NOXAPP"))) $ (sameas(emmat_N,"nox"))))
                                                        - (p_ghgMiti(RUNR,MAACT,"AD_Anch","othImpact","N2OAPP")* v_Miti(RUNR,MAACT,"AD_Anch","CH4MAN")) $ (sameas(emmat_N,"n2o"))));
    """
    for g in ("NH3", "NOX", "N2O"):
        tag = f"{g}APP"
        base = left
        if g == "N2O":
            base = base - (L[("NH3", "Appl")] + L[("NOX", "Appl")])
        red = 0.0
        for t, e in _terms(eff, APPL_TECHS, tag):
            red = red + e * _s(sh, t)
        red = red + fert_appl.get(g, 0.0)
        if g == "N2O":
            red = red + _e(eff, "AD_AnCh", "N2OAPP") * ad
        L[(g, "Appl")] = base * ro * f.get(f"appl_{g}", 0.0) * (1.0 - red)
    L[("N2", "Appl")] = 0.0


def RUNTOTN_(L):
    """RUNTOTN_ (l. 3348-3350): the total runoff.

    CAPRI's GAMS, RUNTOTN_ (l. 3348-3350):

               RUNTOTN_(RUNR,MAACT)..
               v_emiloss(RUNR,MAACT,"N","Runtot") =E= v_emiLoss(RUNR,MAACT,"N","RunHous") + v_emiLoss(RUNR,MAACT,"N","RunSurf") ;
    """
    L[("N", "RunTot")] = L[("N", "RunHous")] + L[("N", "RunSurf")]


def GASRUNTOTN_(L):
    """GASRUNTOTN_ (l. 3371-3376): every gaseous loss at every stage plus the runoff.

    CAPRI's GAMS, GASRUNTOTN_ (l. 3371-3376):

               GASRUNTOTN_(RUNR,MAACT)..
               v_emiloss(RUNR,MAACT,"N","GasRuntot") =E= SUM(nmat, v_emiLoss(RUNR,MAACT,nmat,"Graz")
                                                                      + v_emiLoss(RUNR,MAACT,nmat,"Hous") + v_emiLoss(RUNR,MAACT,nmat,"Stor")
                                                                      + v_emiLoss(RUNR,MAACT,nmat,"Appl"))
                                                                      + v_emiLoss(RUNR,MAACT,"N","RunHous") + v_emiLoss(RUNR,MAACT,"N","RunSurf");
    """
    tot = 0.0
    for g in NMAT:
        for st in ("Graz", "Hous", "Stor", "Appl"):
            tot = tot + L[(g, st)]
    L[("N", "GasRunTot")] = tot + L[("N", "RunHous")] + L[("N", "RunSurf")]


def losses(f, run_surf, sh, eff, m_runsurf=(1.0, 1.0), m_appl_run=1.0, fert_appl=None):
    """CAPRI's v_emiLoss of one animal activity: {(gas, stage): fraction of excreted N}, stages Graz, Hous, Stor, Appl,
    and ("N", "RunHous"), ("N", "RunSurf"), ("N", "RunTot"), ("N", "GasRunTot"): the cascade's equations in CAPRI's order.
    fert_appl: {gas: sum over the fertiliser options (shares + AECM initial shares) x othImpact <gas>APP} (APPLN_).

    CAPRI's GAMS of each equation: the docstring of its function above.
    """
    fert_appl = fert_appl or {}
    tsg = f.get("tsg", 0.0)
    L = {}
    GRAZN_(L, f, tsg)
    ad = _s(sh, "AD_AnCh")
    HOUSN_(L, f, sh, eff, tsg, ad)
    hous = L[("NH3", "Hous")] + L[("NOX", "Hous")] + L[("N2O", "Hous")]
    STORN_(L, f, sh, eff, tsg, ad, hous)
    stor = sum(L[(g, "Stor")] for g in NMAT)
    hous_all = hous + L[("N2", "Hous")]
    RUNHOUSN_(L, f, sh, eff, tsg, hous, stor)
    graz = L[("NH3", "Graz")] + L[("NOX", "Graz")] + L[("N2O", "Graz")]
    left = 1.0 - tsg - hous_all - stor - L[("N", "RunHous")]
    RUNSURFN_(L, sh, eff, tsg, graz, left, run_surf, m_runsurf)
    ro = 1.0 - run_surf * m_appl_run
    APPLN_(L, f, sh, eff, ad, left, ro, fert_appl)
    RUNTOTN_(L)
    GASRUNTOTN_(L)
    return L


def GASTOTNETF_(L, fr, urea, urea_eff, fert_syn, till_n2o):
    """GASTOTNETF_ (l. 3385-3411): the gaseous losses of mineral N, N2O after NH3 and NOX.

    CAPRI's GAMS, GASTOTNETF_ (l. 3385-3411):

               GASTOTNETF_(RUNR,emmat_N)..
               v_emiloss(RUNR,"NETF",emmat_N,"Gastot") =E= (1 - (v_emiloss(RUNR,"NETF","NH3","Gastot") + v_emiloss(RUNR,"NETF","NOX","Gastot"))
                                                                $ (sameas(emmat_N,"n2o")))
                                                           * sum(R_RAGG(RUNR,MSACT),p_Nemidat(MSACT,"NETF",emmat_N,"LossAppl","AV")
                                                           * (1.
                                                              - (v_Miti(RUNR,"CropMiti","UreaSubst","NH3SYN")
                                                              * (p_ghgMiti(RUNR,"cropMiti","UreaSubst","othImpact","NH3SYN")
                                                              + p_ghgMiti(MSACT,"cropMiti","UreaSubst","othImpact","NH3SYN")
                                                              $ (not p_ghgMiti(RUNR,"cropMiti","UreaSubst","othImpact","NH3SYN")))) $ (sameas(emmat_N,"nh3"))
                                                              - sum(AllTechFert,(v_Miti(RUNR,"CropMiti",AllTechFert,"N2OSYN")
                                                                               + v_Miti(RUNR,"CropMiti",AllTechFert,"N2OSYN2")
                                                                               + p_ghgMiti(RUNR,"cropMiti",AllTechFert,"n2osyn","iniShareAECM"))
                                                              * (( p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NH3SYN")
                                                                 + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","NH3SYN")
                                                                 $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NH3SYN"))) $ (sameas(emmat_N,"nh3"))
                                                                +( p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NOXSYN")
                                                                 + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","NOXSYN")
                                                                 $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NOXSYN"))) $ (sameas(emmat_N,"nox"))
                                                                +( p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","N2OSYN")
                                                                 + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","N2OSYN")
                                                                 $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","N2OSYN"))) $ (sameas(emmat_N,"n2o"))))
                                                             - sum(mitiTechTill,p_ghgMiti(RUNR,"cropMiti",mitiTechTill,"othImpact","n2osyn")
                                                             *     v_Miti(RUNR,"cropMiti",mitiTechTill,"CO2SEQ")) $ (sameas(emmat_N,"n2o"))
                                                            ));
    """
    L["NH3"] = fr.get("netf_NH3", 0.0) * (1.0 - urea * urea_eff - fert_syn.get("NH3", 0.0))
    L["NOX"] = fr.get("netf_NOX", 0.0) * (1.0 - fert_syn.get("NOX", 0.0))
    L["N2O"] = (1.0 - L["NH3"] - L["NOX"]) * fr.get("netf_N2O", 0.0) * (1.0 - fert_syn.get("N2O", 0.0) - till_n2o)


def RUNTOTNETF_(L, gas, run_surf, m_run):
    """RUNTOTNETF_ (l. 3352-3367): the runoff of mineral N, (1 - the gaseous losses) x run_surf x the crop factors.

    CAPRI's GAMS, RUNTOTNETF_ (l. 3352-3367):

               RUNTOTNETF_(RUNR)..
               v_emiloss(RUNR,"NETF","N","Runtot") =E= sum(R_RAGG(RUNR,MSACT),
                                                       (1 - sum(emmat_N, v_emiloss(RUNR,"NETF",emmat_N,"Gastot")))
                                                       * p_Nemidat(RUNR,"NETF","N","Runoff","Surf")
                                                       * (1 - sum(mitiTechCov,p_ghgMiti(RUNR,"catc",mitiTechCov,"othImpact","no3srun")
                                                            * v_Miti(RUNR,"CATC",mitiTechCov,"CO2SEQ"))
                                                            - sum(mitiTechTill,p_ghgMiti(RUNR,"cropMiti",mitiTechTill,"othImpact","no3srun")
                                                            * v_Miti(RUNR,"cropMiti",mitiTechTill,"CO2SEQ"))
                                                            - sum(AllTechFert,(v_Miti(RUNR,"CropMiti",AllTechFert,"N2OSYN") + v_Miti(RUNR,"CropMiti",AllTechFert,"N2OSYN2")
                                                                              + p_ghgMiti(RUNR,"cropMiti",AllTechFert,"n2osyn","iniShareAECM"))
                                                            * (p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NO3SRUN")
                                                            + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","NO3SRUN") $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NO3SRUN")))))
                                                       * (1 - sum(mitiTechBuff, p_ghgMiti(RUNR,"cropMiti",mitiTechBuff,"othImpact","no3srun")
                                                            * v_Miti(RUNR,"cropMiti",mitiTechBuff,"no3syn"))
                                                            - sum(mitiTechBiod, p_ghgMiti(RUNR,"cropMiti",mitiTechBiod,"othImpact","no3run") * v_Miti(RUNR,"cropMiti",mitiTechBiod,"BioDiv"))));
    """
    L["RunTot"] = (1.0 - gas) * run_surf * m_run


def GASRUNTOTNETF_(L, gas):
    """GASRUNTOTNETF_ (l. 3378-3380): the gaseous losses plus the runoff of mineral N.

    CAPRI's GAMS, GASRUNTOTNETF_ (l. 3378-3380):

               GASRUNTOTNETF_(RUNR)..
               v_emiloss(RUNR,"NETF","N","GasRuntot") =E= SUM(emmat_n, v_emiLoss(RUNR,"NETF",emmat_n,"GasTot"))  + v_emiLoss(RUNR,"NETF","N","RunTot");
    """
    L["GasRunTot"] = gas + L["RunTot"]


def netf(fr, run_surf, urea=0.0, urea_eff=0.0, fert_syn=None, till_n2o=0.0, m_run=1.0):
    """CAPRI's v_emiLoss of mineral fertiliser (GASTOTNETF_, RUNTOTNETF_, GASRUNTOTNETF_) as fractions of mineral N.
    fr: netf_NH3, netf_NOX, netf_N2O (n_cascade_region.csv); urea: share of UreaSubst, urea_eff its othImpact NH3SYN;
    fert_syn {gas: sum over fertiliser options of (shares + AECM initial shares) x othImpact <gas>SYN}; till_n2o: sum
    over tillage options of othImpact n2osyn x share; m_run: RUNTOTNETF_'s crop factors.

    CAPRI's GAMS of each equation: the docstring of its function above.
    """
    fert_syn = fert_syn or {}
    L = {}
    GASTOTNETF_(L, fr, urea, urea_eff, fert_syn, till_n2o)
    gas = L["NH3"] + L["NOX"] + L["N2O"]
    RUNTOTNETF_(L, gas, run_surf, m_run)
    GASRUNTOTNETF_(L, gas)
    return L


def LEACHN_B1(wc=0.0, agg=0.0, nmin_sh=0.0, nman_sh=0.0, fert_min=0.0, fert_man=0.0):
    """LEACHN_'s first factor B1 (l. 3416-3442): 1 - winter cover's effect - nminSh x the fertiliser options' effect
    on mineral N - nmanSh x theirs on manure -/+ agg. fert_min / fert_man: sum over the fertiliser options of share x
    effect (mineral N / manure); agg: v_ammoAppLeaAgg (AMMOAGG_), its sign the setting environment.ammapp_sign (FIX-2).

    CAPRI's GAMS of LEACHN_: LEACHN_'s docstring.
    """
    from capri_mod.params import param
    from capri_mod.settings import current as _settings
    sign = 1.0 if _settings().get("environment.ammapp_sign") == "capri" else -1.0
    return 1.0 - param("WINTERCOV_NO3_REDUCTION") * wc - nmin_sh * fert_min - nman_sh * fert_man + sign * agg


def LEACHN_(leach_ini, leach_base, b1_now, b1_ini):
    """v_nitrBalance(RUNR, "Leach") (LEACHN_, l. 3416-3442), the leaching share of the soil surplus, with B2 held at
    CAPRI's ini run: leach_ini x B1 / B1_ini (leach_ini where B1_ini is not positive); without CAPRI's ini share,
    leach_base x B1; None without either (n_leaching_region.csv).

    CAPRI's GAMS, LEACHN_ (l. 3416-3442):

           LEACHN_(RUNR)..
           v_nitrBalance(RUNR,"Leach") =E= sum(R_RAGG(RUNR,MSACT),p_Nemidat(RUNR,"NITF","N","Leach","Surf")
                                           * (1 - sum(mitiTechCov,p_ghgMiti(RUNR,"catc",mitiTechCov,"othImpact","no3lea") * v_Miti(RUNR,"CATC",mitiTechCov,"CO2SEQ"))
                                                - v_nminInputSh(RUNR) * (sum(AllTechFert,(v_Miti(RUNR,"CropMiti",AllTechFert,"N2OSYN") + v_Miti(RUNR,"CropMiti",AllTechFert,"N2OSYN2")
                                                                                         + p_ghgMiti(RUNR,"cropMiti",AllTechFert,"n2osyn","iniShareAECM"))
                                                * (p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NO3SLEA")
                                                + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","NO3SLEA") $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NO3SLEA")))))
                                                - v_nmanInputSh(RUNR) * (sum(AllTechFert,(v_Miti(RUNR,"CropMiti",AllTechFert,"N2OMAN") + v_Miti(RUNR,"CropMiti",AllTechFert,"N2OMAN2")
                                                                                         + p_ghgMiti(RUNR,"cropMiti",AllTechFert,"n2oman","iniShareAECM"))
                                                * (p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NO3MLEA")
                                                + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","NO3MLEA") $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NO3MLEA"))))
                                                + v_ammoAppLeaAgg(RUNR)))
                                            * (1 - v_nminInputSh(RUNR)
                                                 * sum(mitiTechTill,p_ghgMiti(RUNR,"cropMiti",mitiTechTill,"othImpact","no3slea") * v_Miti(RUNR,"cropMiti",mitiTechTill,"CO2SEQ"))
                                                - v_nmanInputSh(RUNR)
                                                 * sum(mitiTechTill,p_ghgMiti(RUNR,"cropMiti",mitiTechTill,"othImpact","no3mlea") * v_Miti(RUNR,"cropMiti",mitiTechTill,"CO2SEQ"))
                                                - v_nminInputSh(RUNR)
                                                 * sum((mitiTechBuff,targNitr),p_ghgMiti(RUNR,"cropMiti",mitiTechBuff,"othImpact","no3slea") * v_Miti(RUNR,"cropMiti",mitiTechBuff,targNitr))
                                                - v_nmanInputSh(RUNR)
                                                 * sum((mitiTechBuff,targNitr),p_ghgMiti(RUNR,"cropMiti",mitiTechBuff,"othImpact","no3mlea") * v_Miti(RUNR,"cropMiti",mitiTechBuff,targNitr))
                                                - sum(mitiTechBiod,p_ghgMiti(RUNR,"cropMiti",mitiTechBiod,"othImpact","no3lea") * v_Miti(RUNR,"cropMiti",mitiTechBiod,"BioDiv"))
                                                - p_ghgMiti(RUNR,"uaarMiti","biochar","othImpact","no3lea") * v_Miti(RUNR,"uaarMiti","biochar","co2seq")
                                                  ));
    """
    li = leach_ini
    if li is None:
        lb = leach_base
        return None if lb is None else max(0.0, lb * b1_now)
    if not b1_ini > 0:
        return li
    return max(0.0, li * b1_now / b1_ini)


def AMMOAGG_(manure):
    """v_ammoAppLeaAgg (AMMOAGG_, l. 3444-3459): the application options' effect on leaching (no3mlea x share), the
    average over the animals weighted by their manure N net of the cascade's losses, N_a (1 - GasRunTot_a). manure:
    [(N_a, RunSurf_a, GasRunTot_a, sum over AmmAppHE and AmmAppLE of no3mlea x share)] (the accounts'
    _leach_animals); 0 without manure N.

    CAPRI's GAMS, AMMOAGG_ (l. 3444-3459):

           AMMOAGG_(RUNR)..
           SUM( MAACT $ p_technFact(RUNR,MAACT,"LEVL","T"),
                         v_actLevl(RUNR,MAACT,"T") * %data%(RUNR,MAACT,"MANN","Y") * (p_technFact(RUNR,MAACT,"MANN","T")+1.)
                       * (1 - v_emiLoss(RUNR,MAACT,"N","GasRunTot"))) * v_ammoAppLeaAgg(RUNR)
           =E=
           SUM( MAACT $ p_technFact(RUNR,MAACT,"LEVL","T"),
                         v_actLevl(RUNR,MAACT,"T") * %data%(RUNR,MAACT,"MANN","Y") * (p_technFact(RUNR,MAACT,"MANN","T")+1.)
                       * (1 - v_emiLoss(RUNR,MAACT,"N","GasRunTot"))
                       * p_ghgMiti(RUNR,MAACT,"AmmAppHE","othImpact","no3mlea") * v_Miti(RUNR,MAACT,"AmmAppHE","NH3APP")
                       + v_actLevl(RUNR,MAACT,"T") * %data%(RUNR,MAACT,"MANN","Y") * (p_technFact(RUNR,MAACT,"MANN","T")+1.)
                       * (1 - v_emiLoss(RUNR,MAACT,"N","GasRunTot"))
                       * p_ghgMiti(RUNR,MAACT,"AmmAppLE","othImpact","no3mlea") * v_Miti(RUNR,MAACT,"AmmAppLE","NH3APP"))
    ;
    """
    w = sum(n * (1.0 - gr) for n, _, gr, _ in manure)
    return sum(n * (1.0 - gr) * ag for n, _, gr, ag in manure) / w if w > 0 else 0.0


def GASTOTNETF_fertSyn(fert_syn, othImpact, v_Miti):
    """The fertiliser options' term of GASTOTNETF_ (l. 3385-3411: the sum over AllTechFert of the share x othImpact on
    NH3SYN, NOXSYN or N2OSYN), accumulated over the options: fert_syn + othImpact x v_Miti (netf's fert_syn; othImpact
    = 1 - (1 - lit)(1 + NMIN), ghgMiti.gms l. 552-563, supply/n_leaching.py fert_effect). CAPRI's GAMS: GASTOTNETF_'s
    docstring."""
    return fert_syn + othImpact * v_Miti


def RUNTOTNETF_fertRun(srun, othImpact, v_Miti):
    """The fertiliser options' term of RUNTOTNETF_'s crop factor (l. 3352-3367: the sum over AllTechFert of the share x
    othImpact NO3SRUN), accumulated over the options: srun + othImpact x v_Miti. CAPRI's GAMS: RUNTOTNETF_'s
    docstring."""
    return srun + othImpact * v_Miti


def RUNTOTNETF_cropFactor(wc_red, v_Miti_catc, srun=0):
    """RUNTOTNETF_'s crop factor (l. 3352-3367), netf's m_run: 1 - winter cover's runoff reduction x its share - the
    fertiliser options' NO3SRUN term (RUNTOTNETF_fertRun); the tillage, buffer strip and biodiversity terms are options
    the model does not have. CAPRI's GAMS: RUNTOTNETF_'s docstring."""
    return 1 - wc_red * v_Miti_catc - srun
