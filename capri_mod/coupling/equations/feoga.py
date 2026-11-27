r"""CAPRI's report of the policy instruments' budget cost (reports/feoga.gms, star 3.0): the premium outlays per product
(FEOP) and their budget columns (income I4). CAPRI computes them per member state from its regions' premiums and levels
after the supply model's report (capmod/reports.gms l. 94, 188); capri_mod/income/feoga.py calls these statements per
member state from the regional solutions. The export subsidies, intervention stocks and consumption aids (FEOE, FEOS,
FEOC, l. 164 on) are zero or outside the model in the 2030 EU; the WTO boxes are another report.
"""
from __future__ import annotations


def p_budToPsdPay(scheme):
    r"""p_budToPsdPay(psBud, PSDPAY) of a payment by its scheme aggregate (p_aggToPsdPay: "DPPIL1", "DPPIL2" or
    "DPNAT"): the share of the payment each budget pays, {budPil1, budPil2, budNAT, budRestEU, budEU}.

    CAPRI's GAMS (policy/policy_sets.gms l. 1582-1593):

            PARAMETER P_budToPsdPay(psBud,psdPay) "Aggregation from single payments to aggregates of payments";

            p_budToPsdPay("budPil1",PSDPAY) $ p_aggToPsdPay("DPPIL1",PSDPAY) = 1;
            p_budToPsdPay("budPil2",PSDPAY) $ p_aggToPsdPay("DPPIL2",PSDPAY) = 0.5;
            p_budToPsdPay("budNAT",PSDPAY)  $ p_aggToPsdPay("DPPIL2",PSDPAY) = 0.5;
            p_budToPsdPay("budNAT",PSDPAY)  $ p_aggToPsdPay("DPNAT",PSDPAY)  = 1.0;

            p_budToPsdPay("budRestEU",PSDPAY) = 1. - sum(psBud, p_budToPsdPay(psBud,PSDPAY));

            p_budToPsdPay("budEU",PSDPAY) = p_budToPsdPay("budPil1",PSDPAY)
                                          + p_budToPsdPay("budPil2",PSDPAY)
                                          + p_budToPsdPay("budRestEU",PSDPAY);

    In this project's notation: Pillar I 1 to budPil1; Pillar II 0.5 to budPil2 and 0.5 to budNAT; the national
    payments 1 to budNAT; budRestEU the rest; budEU = budPil1 + budPil2 + budRestEU. Departures from CAPRI: the payments
    by their aggregate, not one by one (the model keeps each activity's premium per scheme aggregate,
    premium_scheme_shares_2030.csv: DPPIL1, the Pillar II schemes DPRD_LFA, DPRD_N2K and DPAE, DPNAT); budNatEU, which
    CAPRI's statements leave at zero, not returned."""
    b = {"budPil1": 1.0 if scheme == "DPPIL1" else 0.0,
         "budPil2": 0.5 if scheme == "DPPIL2" else 0.0,
         "budNAT": 0.5 if scheme == "DPPIL2" else (1.0 if scheme == "DPNAT" else 0.0)}
    b["budRestEU"] = 1.0 - sum(b.values())
    b["budEU"] = b["budPil1"] + b["budPil2"] + b["budRestEU"]
    return b


def DATA_MPACT_psBudRows(p_premPaym, p_bud):
    r"""DATA(RUNR, MPACT, psBudRows, SIMY): an activity's premium per unit paid from a budget, its premiums by payment x
    the budget's share of each (sequences over the payments in the same order; EUR per ha or head).

    CAPRI's GAMS (reports/feoga.gms l. 62-64):

         DATA(RUNR,MPACT,psBudRows,"%SIMY%") $ DATA(RUNR,MPACT,"PRME","%SIMY%")
             = sum( (PSDPAY,psBud) $ ( p_budToPsdPay(psBud,PSDPAY) $ sameas(psBudRows,psBud) $ PSDPAY_T_A(MPACT,PSDPAY)),
                                                         p_premPaym(RUNR,MPACT,PSDPAY,"PRME") * p_budToPsdPay(psBud,PSDPAY));

    In this project's notation: B_a,bud = sum_s P_a,s p_bud,s."""
    return float(sum(float(p) * float(b) for p, b in zip(p_premPaym, p_bud)))


def DATA_FEOP_O(PRME, LEVL):
    r"""DATA(MS, "FEOP", O, SIMY) before the idle land's premiums: the premium outlays for a product, the premiums of
    the activities with the product as their main output (PACT_TO_Y) x their levels (sequences over those activities;
    EUR per ha or head x 1000 ha or heads / 1000 = EUR million).

    CAPRI's GAMS (reports/feoga.gms l. 87-98):

         DATA(MS,"FEOP",O,"%SIMY%")
          = SUM(PACT_TO_Y(MPACT,O) $ DATA(MS,MPACT,"LEVL","%SIMY%"),
        *
        * --- premium for activity producing O as the main output
        *
                 ( DATA(MS,MPACT,"PRME","%SIMY%")
        *
        * --- add premiums paid for set-aside to the activity
        *
                 +  DATA(MS,MPACT,"SETR","%SIMY%") * 0.01 * DATA(MS,"OSET","PRME","%SIMY%") $ (DATA(MS,MPACT,"SETR","%SIMY%") gt eps)
                 )
                                        * DATA(MS,MPACT,"LEVL","%SIMY%") )/1000.;

    In this project's notation: FEOP_O = sum_a PRME_a L_a / 1000. The set-aside term is zero: the report sets SETR to
    zero before (reports/sol_simy.gms l. 2617, capmod/reports.gms l. 94 before l. 188), and the model has no obligatory
    set-aside in 2030. Departures from CAPRI: none in the statement."""
    return float(sum(float(p) * float(l_) for p, l_ in zip(PRME, LEVL))) / 1000.0


def DATA_psBudCols_O(B, LEVL):
    r"""DATA(MS, psBudCols, O, SIMY) before the idle land's premiums: a product's premium outlays from a budget
    (sequences over the activities with the product as their main output, B their premium per unit from the budget,
    DATA_MPACT_psBudRows; EUR million).

    CAPRI's GAMS (reports/feoga.gms l. 100-105):

         DATA(MS,psBudCols,O,"%SIMY%") $ DATA(MS,"FEOP",O,"%SIMY%")
            = SUM( (PACT_TO_Y(MPACT,O),psBudRows) $ ( (DATA(MS,MPACT,psBudRows,"%SIMY%") or DATA(MS,"OSET",psBudRows,"%SIMY%")) $ sameas(psBudCols,psBudRows)),
                   ( DATA(MS,MPACT,psBudRows,"%SIMY%")
                   + (DATA(MS,MPACT,"SETR","%SIMY%") * 0.01 * DATA(MS,"OSET",psBudRows,"%SIMY%"))  $ (DATA(MS,MPACT,"SETR","%SIMY%") gt eps)
                   )
                       * DATA(MS,MPACT,"LEVL","%SIMY%"))/1000.;

    In this project's notation: bud_O = sum_a B_a L_a / 1000 (where FEOP_O is not zero; the set-aside term zero, as in
    DATA_FEOP_O)."""
    return float(sum(float(b) * float(l_) for b, l_ in zip(B, LEVL))) / 1000.0


def DATA_FEOP_UAAR(PRME_idle, LEVL_idle, LEVL_crops):
    r"""DATA(MS, "FEOP", "UAAR", SIMY) (and DATA(MS, "FEOP", psBudRows, SIMY) with the budget's premiums): the idle
    land's premiums per 1000 ha of the crops receiving premiums, the premiums of the fallow land and the voluntary
    set-aside (FALL, VSET; the obligatory ISET and TSET where present) x their levels over the area of the crops with a
    premium and a main output (sequences over the idle land's activities, and over the crops; EUR million per 1000 ha).

    CAPRI's GAMS (reports/feoga.gms l. 111-116, the crops' area; l. 120-135, the premiums):

         DATA(MS,"FEOP","UAAR","%SIMY%")    =  SUM( (MCACT,O) $ (DATA(MS,MCACT,"PRME","%SIMY%") $ PACT_TO_Y(MCACT,O)),
                                                                                        DATA(MS,MCACT,"LEVL","%SIMY%"));


         DATA(MS,"FEOP",psBudRows,"%SIMY%") =  SUM( (MCACT,O) $ (DATA(MS,MCACT,psBudRows,"%SIMY%") $ PACT_TO_Y(MCACT,O)),
                                                                                        DATA(MS,MCACT,"LEVL","%SIMY%"));
        *
        *  --- premiums paid to idling land in relation to areas receiving supports (above)
        *
         DATA(MS,"FEOP","UAAR","%SIMY%") $ DATA(MS,"FEOP","UAAR","%SIMY%")
           = ( DATA(MS,"FALL","PRME","%SIMY%")*DATA(MS,"FALL","LEVL","%SIMY%") * 0.001
              +DATA(MS,"VSET","PRME","%SIMY%")*DATA(MS,"VSET","LEVL","%SIMY%") * 0.001
              +(  DATA(MS,"ISET","PRME","%SIMY%")*DATA(MS,"ISET","LEVL","%SIMY%") * 0.001
                + DATA(MS,"TSET","PRME","%SIMY%")*DATA(MS,"TSET","LEVL","%SIMY%") * 0.001)
                  $ ((NOT SUM(MPACT $ (DATA(MS,MPACT,"SETR","%SIMY%") gt eps),1))
                                OR DATA(MS,"OSET","FLOOR","%SIMY%"))) / DATA(MS,"FEOP","UAAR","%SIMY%") ;

        *
         DATA(MS,"FEOP",psBudRows,"%SIMY%") $ DATA(MS,"FEOP",psBudRows,"%SIMY%")
           = ( DATA(MS,"FALL",psBudRows,"%SIMY%")*DATA(MS,"FALL","LEVL","%SIMY%") * 0.001
              +DATA(MS,"VSET",psBudRows,"%SIMY%")*DATA(MS,"VSET","LEVL","%SIMY%") * 0.001
              +( DATA(MS,"ISET",psBudRows,"%SIMY%")*DATA(MS,"ISET","LEVL","%SIMY%") * 0.001
              +  DATA(MS,"TSET",psBudRows,"%SIMY%")*DATA(MS,"TSET","LEVL","%SIMY%") * 0.001)
                  $ ((NOT SUM(MPACT $ (DATA(MS,MPACT,"SETR","%SIMY%") gt eps),1))
                                OR DATA(MS,"OSET","FLOOR","%SIMY%"))) / DATA(MS,"FEOP",psBudRows,"%SIMY%") ;

    In this project's notation: U = 0.001 sum_i PRME_i L_i / sum_c L_c, the crops c with a premium (with the budget's
    premium, for a budget) and a main output. Departures from CAPRI: none in the statement (the model has no ISET and
    TSET)."""
    area = float(sum(float(l_) for l_ in LEVL_crops))
    if not area:
        return 0.0
    return 0.001 * float(sum(float(p) * float(l_) for p, l_ in zip(PRME_idle, LEVL_idle))) / area


def DATA_FEOP_O_idle(FEOP_O, LEVL_crops_O, FEOP_UAAR):
    r"""DATA(MS, "FEOP", O, SIMY) (and DATA(MS, psBudCols, O, SIMY) with the budget's FEOP_UAAR): the product's premium
    outlays with its crops' share of the idle land's premiums, their levels x the outlays per 1000 ha (the crops with a
    premium and the product as their main output; EUR million).

    CAPRI's GAMS (reports/feoga.gms l. 151-159):

         DATA(MS,"FEOP",O,"%SIMY%")   =  DATA(MS,"FEOP",O,"%SIMY%")
        *
                                     + SUM(MCACT $ (DATA(MS,MCACT,"PRME","%SIMY%") $ PACT_TO_Y(MCACT,O)),
                                                     DATA(MS,MCACT,"LEVL","%SIMY%") * DATA(MS,"FEOP","UAAR","%SIMY%"));

         DATA(MS,psBudCols,O,"%SIMY%")   =  DATA(MS,psBudCols,O,"%SIMY%")
        *
                                     + SUM( (MCACT,psBudRows) $ (DATA(MS,MCACT,"PRME","%SIMY%") $ SAMEAS(psbudCols,psbudRows) $ PACT_TO_Y(MCACT,O)),
                                                     DATA(MS,MCACT,"LEVL","%SIMY%") * DATA(MS,"FEOP",psBudRows,"%SIMY%"));

    In this project's notation: FEOP_O + sum_c L_c U."""
    return float(FEOP_O) + float(sum(float(l_) for l_ in LEVL_crops_O)) * float(FEOP_UAAR)
