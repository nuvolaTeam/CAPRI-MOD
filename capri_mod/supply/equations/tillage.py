"""CAPRI's conservation and no tillage options (ConsTill, NoTill; target CO2SEQ) as envind/tillage.gms sets them up
(CAPRI star 3.0): the initial shares from the SAPM 2016 survey, and the calibration of the cost function per ha of
tillage area (l. 605-849, %ghgTechcali% off as in CAPRI's Green Deal runs; premCapMitTech off, so the agri-environment
blocks l. 331-361 and 775-808 do not apply).

Used by tools/build/build_tillage_options.py. The cost function per ha of tillage area and per share m,

    (costParLin + pmpParLin) m + 0.5 pmpParSqr m^2,

is CAPRI's GHG_Mit_Cost_ on its tillage base (supply/supply_model.gms l. 5078-5081: the tillage area sum of the
arable crops' levels): equations/supply_model/mitigation.py.
"""
from __future__ import annotations


def p_tillageCover_shares(cover: dict) -> dict:
    r"""p_tillageCover(SRNUTS2, Till) as tillage.gms makes it a share of the three tillage practices (l. 316-321).

    CAPRI's GAMS (envind/tillage.gms l. 316-321):

      p_tillageCover(SRNUTS2,Till) = max(0,p_tillageCover(SRNUTS2,Till));

      * make sure that the shares of tillage practices add up to 1
      p_tillageCover(SRNUTS2,Till) $ sum(till1,p_tillageCover(SRNUTS2,Till1))
          = p_tillageCover(SRNUTS2,Till) / sum(till1,p_tillageCover(SRNUTS2,Till1));

    In this project's notation, c_t the survey's value of practice t in {ConvTill, ConsTill, NoTill}:
        share_t = max(0, c_t) / sum_t' max(0, c_t')   (unchanged where the sum is 0).
    cover: {practice: value} of one region (practices missing count as 0). Departures from CAPRI: none."""
    till = ("ConvTill", "ConsTill", "NoTill")
    c = {t: max(0.0, float(cover.get(t, 0.0) or 0.0)) for t in till}
    s = sum(c.values())
    return {t: (c[t] / s if s else c[t]) for t in till}


def IniShare_till(shares: dict) -> dict:
    r"""p_ghgMiti(ru, cropMiti, tech, co2seq, IniShare) of ConsTill, NoTill and noc (l. 329, 363-367; premCapMitTech
    off).

    CAPRI's GAMS (envind/tillage.gms l. 329, 363-367):

      p_ghgMiti(ru,"cropMiti",MitiTechTill,"co2seq","IniShare") = sum(map_TillTech(TillCov,MitiTechTill),p_tillageCover(ru,TillCov));
      ...
      p_ghgMiti(ru,"cropMiti","noc","co2seq","IniShare") = 1 - sum(mitiTechTill,p_ghgMiti(ru,"cropMiti",mitiTechTill,"co2seq","IniShare"));

      p_ghgMiti(ru,"cropMiti","noc","co2seq","IniShare") $ ((not p_ghgMiti(ru,"cropMiti","noc","co2seq","IniShare"))
                                                        and (not sum(mitiTechTill,p_ghgMiti(ru,"cropMiti",mitiTechTill,"co2seq","IniShare"))))
                                                         = 1;

    map_TillTech: ConvTill.noc, ConsTill.ConsTill, NoTill.NoTill (l. 306-311). shares: p_tillageCover_shares' output.
    Returns {"ConsTill", "NoTill", "noc"}. Departures from CAPRI: none."""
    out = {"ConsTill": float(shares.get("ConsTill", 0.0)), "NoTill": float(shares.get("NoTill", 0.0))}
    noc = 1.0 - out["ConsTill"] - out["NoTill"]
    if not noc and not (out["ConsTill"] + out["NoTill"]):
        noc = 1.0
    out["noc"] = noc
    return out


def MaxIncrease_till(MaxShare, IniShare):
    r"""p_ghgMiti(rs, cropMiti, tech, co2seq, MaxIncrease) (l. 640-644).

    CAPRI's GAMS (envind/tillage.gms l. 640-644):

      p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","MaxIncrease")
        $ p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","MaxShare")
        = max(1.E-4, (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","MaxShare")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","IniShare"))
                   /  p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","MaxShare"));

    Departures from CAPRI: none."""
    if not MaxShare:
        return 0.0
    return max(1e-4, (MaxShare - IniShare) / MaxShare)


def relSubs_till(costParLin, costsaving0, IniShare, MaxIncrease, cropyld=1.0, sensFac=1.0):
    r"""(relSubs0, relSubs1, case) of a tillage option (l. 664-750): the four cases by the sign of the full unit cost
    kappa = costParLin - costsaving0 and whether the initial share is positive.

    CAPRI's GAMS (envind/tillage.gms l. 671-750):

      *     -- case 1: unit cost and observed shares are positive
      p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","relSubs1")
        $ (  (  ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) gt 0)
             or (p_ghgMiti(rs,"cropMiti",MitiTechTill,"othImpact","cropyld") ne 1))
           $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","IniShare") gt 0)
           $ mitiTech_map(rs,"cropMiti",MitiTechTill,"co2seq") )
         = (0.8 $ ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) gt 0)
           -0.8 $ ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) lt 0))
         * %sensFac%
         * p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","MaxIncrease")
         ;

      *     -- case 2: full unit cost is negative and observed share is positive, but < MaxShare
      p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","relSubs1")
        $ (  ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0"))  lt 0)
          $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"othImpact","cropyld") eq 1)
          $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","IniShare") gt 0)
          $ mitiTech_map(rs,"cropMiti",MitiTechTill,"co2seq") )
        = -0.2
        * %sensFac%
        * p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","MaxIncrease")
        ;

      *     -- case 3: unit cost is positive and observed share is zero
      p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","relSubs1")
        $ (  (  ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) gt 0)
             or (p_ghgMiti(rs,"cropMiti",MitiTechTill,"othImpact","cropyld") ne 1))
           $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin") lt 0)
           $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","IniShare") eq 0)
          $ mitiTech_map(rs,"cropMiti",MitiTechTill,"co2seq") )
         = (1.2 $ ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) gt 0)
           -1.2 $ ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) lt 0))
          * %sensFac%
          ;
      p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","relSubs0")
        $ (  (  ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) gt 0)
             or (p_ghgMiti(rs,"cropMiti",MitiTechTill,"othImpact","cropyld") ne 1))
           $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","IniShare") eq 0)
           $ mitiTech_map(rs,"cropMiti",MitiTechTill,"co2seq") )
         = (0.2 $ ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) gt 0)
           -0.2 $ ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) lt 0))
           * %sensFac%;

      *     -- case 4: unit cost is negative, but observed share is nonetheless zero
      p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","relSubs1")
        $ (  ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) lt  0)
          $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"othImpact","cropyld") eq 1)
          $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin") lt 0)
          $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","IniShare") eq 0)
          $ mitiTech_map(rs,"cropMiti",MitiTechTill,"co2seq") )
        = -0.5
        * %sensFac%
                            ;
      p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","relSubs0")
        $ (  ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) lt  0)
          $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"othImpact","cropyld") eq 1)
          $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin") lt 0)
          $ (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","IniShare") eq 0)
          $ mitiTech_map(rs,"cropMiti",MitiTechTill,"co2seq") )
         = -0.1
         * %sensFac%
                            ;

    The statements run in this order, so a later case overwrites an earlier one where both conditions hold (case 3's
    relSubs1 over case 1's never: their IniShare conditions exclude each other). kappa = costParLin - costsaving0; the
    GAMS 'gt 0' / 'lt 0' leave kappa = 0 in no case. cropyld 1: the Green Deal's NoYieldEffect 1 resets it (l. 504-526).
    Returns (relSubs0, relSubs1, case), 0 / 0 / None where no case applies. Departures from CAPRI: none."""
    kappa = costParLin - costsaving0
    r0 = r1 = 0.0
    case = None
    sgn = (1.0 if kappa > 0 else -1.0 if kappa < 0 else 0.0)
    if (kappa > 0 or cropyld != 1) and IniShare > 0:
        r1 = 0.8 * sgn * sensFac * MaxIncrease; case = 1
    if kappa < 0 and cropyld == 1 and IniShare > 0:
        r1 = -0.2 * sensFac * MaxIncrease; case = 2
    if (kappa > 0 or cropyld != 1) and costParLin < 0 and IniShare == 0:
        r1 = 1.2 * sgn * sensFac; case = 3
    if (kappa > 0 or cropyld != 1) and IniShare == 0:
        r0 = 0.2 * sgn * sensFac
        case = case or 3
    if kappa < 0 and cropyld == 1 and costParLin < 0 and IniShare == 0:
        r1 = -0.5 * sensFac; case = 4
    if kappa < 0 and cropyld == 1 and costParLin < 0 and IniShare == 0:
        r0 = -0.1 * sensFac
    return r0, r1, case


def Subs_till(relSubs, costParLin, costsaving0):
    r"""Subs0 or Subs1 of a tillage option (l. 757-773 and 810-818: the same statement for each): the relative subsidy
    times the full unit cost, or times the accounting cost where that is larger, or times costParLin where kappa < 0.

    CAPRI's GAMS (envind/tillage.gms l. 765-773; Subs1 l. 810-818 the same with relSubs1):

        p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","Subs0")
        = p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","relSubs0")
        * (max( (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")),
              abs(p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")))
          $ ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) gt 0)
          + p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")
          $ ((p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")) lt 0)
           );

    Departures from CAPRI: none."""
    kappa = costParLin - costsaving0
    base = (max(kappa, abs(costParLin)) if kappa > 0 else 0.0) + (costParLin if kappa < 0 else 0.0)
    return relSubs * base


def pmpParsqr_till(Subs0, Subs1, MaxShare, IniShare):
    r"""gamma = pmpParsqr of a tillage option (l. 825-831).

    CAPRI's GAMS (envind/tillage.gms l. 825-831):

        p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","pmpParsqr")
                $ (mitiTech_map(rs,"cropMiti",MitiTechTill,"co2seq") and (NOT p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParsqr"))
                and (NOT p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","pmpParsqr"))
                and (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","MaxShare")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","IniShare")))
          = (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","Subs1") - p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","Subs0"))
          / (p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","MaxShare")-p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","IniShare"))
        ;

    Departures from CAPRI: none (costParsqr and a prior pmpParsqr are empty for the tillage options)."""
    d = MaxShare - IniShare
    return (Subs1 - Subs0) / d if d else 0.0


def pmpParlin_till(Subs0, costParLin, costsaving0, pmpParSqr, IniShare):
    r"""beta = pmpParlin of a tillage option (l. 836-842): the first-order condition costParLin - costsaving0 - Subs0 +
    beta + gamma m0 = 0 at the initial share.

    CAPRI's GAMS (envind/tillage.gms l. 834-842):

      *     beta  = subs0-costparlin+sav0-gamma*m0
      *     NOTE: For beta we have to add the endogenous cost in the initial point "costsaving0", otherwise calibration is impossible
        p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","pmpParlin")
                $ (mitiTech_map(rs,"cropMiti",MitiTechTill,"co2seq") and (NOT p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","pmpParlin")))
          = p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","Subs0")
           - p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costParLin")
           + p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","costsaving0")
           - p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","pmpParSqr")
           * p_ghgMiti(rs,"cropMiti",MitiTechTill,"co2seq","iniShare")
        ;

    Departures from CAPRI: none here. In the regional model the linear term is calibrated again at the base with the
    model's own marginal value of the share in place of costsaving0 (CapriRegionalNLP.calibrate, DEP-30's rule: the
    first-order condition at the initial share Subs0)."""
    return Subs0 - costParLin + costsaving0 - pmpParSqr * IniShare
