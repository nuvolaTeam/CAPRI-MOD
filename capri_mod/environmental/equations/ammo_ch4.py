r"""MITERRA's management shares and CH4 losses of CAPRI's animal activities, p_Nemidat(MS, AACT, gas, item, system)
as envind/ammo.gms sets them with %storgrazInv% off (capmod/set_global_variables.gms l. 61, capreg/
set_global_variables.gms l. 120), for a MITERRA scenario year ScenYear (capmod/create_sim_ini_gdx.gms l. 176-186: 2020
for a simulation year after 2010; envind/Miterra/scenario_settings.gms l. 90: 2000 in CAPREG): the grazing share, the
liquid and solid shares, the shares of the housing and storage measures and the CH4 losses they bring, and their copy to
the high and low yield activities. Used by the methane per head (capri_mod/environmental/methane_per_head.py: gascoeff's
management shares, gases' ammonia techniques' factor).

The inputs are MITERRA's (capri_data/2017/abatement/ammonia: RCEmissions, bNumAniRAINS, ControlStrategies,
reducEmHouse, reducEmStorage; tools/build/build_ammonia_tech_inputs.py) and CAPRI's sets (capri_data/codes/capri:
pact_to_atModel, manuType_to_atModel, ms_to_country, ani_Liq, atGrazingExtra, POULTRY, MDACT, DACT_TO_PACT). Labels
are compared without case, as GAMS compares them (the inputs write NOx, LowEm; CAPRI's code NOX, lowEm). The keys of
p_Nemidat returned: (MS, AACT, GAS, ITEM, SYSTEM) upper-case, as methane_per_head.normalise_nemidat writes them.
Not ported (not used by the methane): the N, NH3, NOx, N2O and N2 losses, the biofiltration, the runoff.
"""
from __future__ import annotations


def _u(x) -> str:
    return str(x).upper()


def FracToepHouse(ControlStrategies, ScenYear):
    r"""FracToepHouse(country, atModel, ht): the shares of the housing types in percent, low-emission housing at
    MITERRA's stable adaptation of the year, normal housing the rest (l. 514-515). Returns {(country, atModel, HT): %}
    with HT upper-case.

    CAPRI's GAMS (envind/ammo.gms l. 513-515):

        * Stable adaption
         FracToepHouse(country,atModel,'normal')= 100-ControlStrategies(country,atModel,'SA','%ScenYear%');
         FracToepHouse(country,atModel,'lowEm')= ControlStrategies(country,atModel,'SA','%ScenYear%');

    ControlStrategies: {(country, atModel, strategy, year): %}. Departures from CAPRI: none."""
    out = {}
    pairs = {(c, a) for (c, a, _s, _y) in ControlStrategies}
    for c, a in pairs:
        sa = float(ControlStrategies.get((c, a, "SA", str(ScenYear)), 0.0) or 0.0)
        out[(c, a, "NORMAL")] = 100 - sa
        out[(c, a, "LOWEM")] = sa
    return out


def FracToepStorage(ControlStrategies, ScenYear):
    r"""FracToepStorage(country, atModel, stt): the shares of the storage covers in percent, the high and low
    efficiency covers at MITERRA's control strategies of the year, the uncovered storage the rest (l. 522-527).
    Returns {(country, atModel, STT): %} with STT upper-case.

    CAPRI's GAMS (envind/ammo.gms l. 521-527):

        * Covered storage
         FracToepStorage(country,atModel,'highem')= ControlStrategies(country,atModel,'CS_high','%ScenYear%');

         FracToepStorage(country,atModel,'lowem')= ControlStrategies(country,atModel,'CS_low','%ScenYear%');

         FracToepStorage(country,atModel,'normal')= 100 - FracToepStorage(country,atModel,'highem')-
                          FracToepStorage(country,atModel,'lowem');

    Departures from CAPRI: none."""
    out = {}
    pairs = {(c, a) for (c, a, _s, _y) in ControlStrategies}
    for c, a in pairs:
        hi = float(ControlStrategies.get((c, a, "CS_high", str(ScenYear)), 0.0) or 0.0)
        lo = float(ControlStrategies.get((c, a, "CS_low", str(ScenYear)), 0.0) or 0.0)
        out[(c, a, "HIGHEM")] = hi
        out[(c, a, "LOWEM")] = lo
        out[(c, a, "NORMAL")] = 100 - hi - lo
    return out


def p_Nemidat_GRAZ(MS, AACT, ms_to_country, pact_to_atModel, atGrazingExtra, ani_Liq, POULTRY, RCEmissions):
    r"""p_Nemidat(MS, AACT, "N", "TypeShare", "GRAZ"): the share of the manure dropped at grazing, the part of the year
    outside the housing days, less the extra time in the stable for milking, of the solid MITERRA type; poultry none
    (l. 604-613, %storgrazInv% off).

    CAPRI's GAMS (envind/ammo.gms l. 603-615):

        $else
            p_Nemidat(MS,AACT,"N","TypeShare","GRAZ") = SUM( (ms_to_country(ms,country),atGrazingExtra) $ (pact_to_atModel(AACT,atGrazingExtra) $

        *                    only pick solid type (Note: Emmission factor liquid = solid here. And we do not want to add coefficients liquid + solid here.)
                                                     (NOT ani_Liq(atGrazingExtra))),
        *                                         Grazing season = summer
                                                     (1-RCemissions(country,atGrazingExtra,'HD')/365.)
        *                                             but less extra time spent in stable for milking
                                                      *(1-RCemissions(country,atGrazingExtra,'Et')/100.) );

            p_Nemidat(MS,AACT,"N","TypeShare","GRAZ") $ POULTRY(AACT) = 0.;

        $endif

    RCEmissions: {(country, atModel, item): value} (HD days, Et percent). Returns {(MS, AACT, "N", "TYPESHARE",
    "GRAZ"): share} where not 0. Departures from CAPRI: none."""
    liq, graz, poul = {_u(x) for x in ani_Liq}, {_u(x) for x in atGrazingExtra}, set(POULTRY)
    countries = {}
    for m, c in ms_to_country:
        countries.setdefault(m, []).append(c)
    types = {}
    for p, t in pact_to_atModel:
        types.setdefault(p, []).append(t)
    out = {}
    for ms in MS:
        for act in AACT:
            if act in poul:
                continue
            v = sum((1 - float(RCEmissions.get((c, t, "HD"), 0.0) or 0.0) / 365.)
                    * (1 - float(RCEmissions.get((c, t, "Et"), 0.0) or 0.0) / 100.)
                    for c in countries.get(ms, ()) for t in types.get(act, ())
                    if _u(t) in graz and _u(t) not in liq)
            if v:
                out[(ms, act, "N", "TYPESHARE", "GRAZ")] = v
    return out


def p_Nemidat_Liquid_Solid(MS, AACT, MDACT, ms_to_country, atModel_to_PACT, bNumAniRAINS, ScenYear):
    r"""p_Nemidat(MS, AACT, "N", "TypeShare", "Liquid" | "Solid"): the liquid share of the dairy cows, the other cattle
    and the pigs, MITERRA's animals in liquid systems over those in liquid and solid systems of the year; the solid
    share the rest, for every animal activity of MDACT of a member state with a MITERRA country (l. 710-737,
    %storgrazInv% off).

    CAPRI's GAMS (envind/ammo.gms l. 707-738):

        $else
        *   Shares of manure systems as projected for RAINS

            p_Nemidat(MS,AACT,"N","TypeShare","Liquid") $ atModel_to_PACT('DAICOW_L',AACT)
                                                      = SUM(MS_to_country(MS,country)
                                                               $ (   bNumAniRAINS(country,'DAICOW_l','%ScenYear%')
                                                                   + bNumAniRAINS(country,'DAICOW_S','%ScenYear%')),
                                                                       bNumAniRAINS(country,'DAICOW_l','%ScenYear%')
                                                                     /(bNumAniRAINS(country,'DAICOW_l','%ScenYear%')+
                                                                       bNumAniRAINS(country,'DAICOW_S','%ScenYear%'))      );



            p_Nemidat(MS,AACT,"N","TypeShare","Liquid") $ atModel_to_PACT('OCOW_L',AACT)
                                                      = SUM(MS_to_country(MS,country)
                                                              $ ((  bNumAniRAINS(country,'OCOW_l','%ScenYear%')
                                                                  + bNumAniRAINS(country,'OCOW_S','%ScenYear%'))),
                                                                       bNumAniRAINS(country,'OCOW_l','%ScenYear%')
                                                                     /(bNumAniRAINS(country,'OCOW_l','%ScenYear%')+
                                                                       bNumAniRAINS(country,'OCOW_S','%ScenYear%'))      );

            p_Nemidat(MS,AACT,"N","TypeShare","Liquid") $ atModel_to_PACT('PIGS_L',AACT)
                                                      = SUM(MS_to_country(MS,country)
                                                                      $ (   bNumAniRAINS(country,'PIGS_l','%ScenYear%')
                                                                          + bNumAniRAINS(country,'PIGS_S','%ScenYear%')),
                                                                       bNumAniRAINS(country,'PIGS_l','%ScenYear%')
                                                                     /(bNumAniRAINS(country,'PIGS_l','%ScenYear%')+
                                                                       bNumAniRAINS(country,'PIGS_S','%ScenYear%'))      );
        *
            p_Nemidat(MS,MDACT,"N","TypeShare","Solid") $ SUM(MS_to_country(MS,country),1.)
                                                          = 1. - p_Nemidat(MS,MDACT,"N","TypeShare","Liquid");
        $endif;

    atModel_to_PACT: {(atModel, activity)}; bNumAniRAINS: {(country, atModel, year): 1000 head}. Returns {(MS, AACT,
    "N", "TYPESHARE", "LIQUID" | "SOLID"): share} where not 0. Departures from CAPRI: none."""
    countries = {}
    for m, c in ms_to_country:
        countries.setdefault(m, []).append(c)
    of = {}
    for t, p in atModel_to_PACT:
        of.setdefault(_u(t), set()).add(p)
    y = str(ScenYear)
    out = {}
    for ms in MS:
        cs = countries.get(ms, ())
        liq = {}
        for L, S in (("DAICOW_L", "DAICOW_S"), ("OCOW_L", "OCOW_S"), ("PIGS_L", "PIGS_S")):
            v = 0.0
            for c in cs:
                nl = float(bNumAniRAINS.get((c, L, y), 0.0) or 0.0)
                ns = float(bNumAniRAINS.get((c, S, y), 0.0) or 0.0)
                if nl + ns:
                    v += nl / (nl + ns)
            for act in of.get(L, ()):
                if act in AACT:
                    liq[act] = v
        for act, v in liq.items():
            if v:
                out[(ms, act, "N", "TYPESHARE", "LIQUID")] = v
        if cs:
            for act in MDACT:
                s = 1. - liq.get(act, 0.0)
                if s:
                    out[(ms, act, "N", "TYPESHARE", "SOLID")] = s
    return out


def p_Nemidat_CH4_LossHous(MS, AACT, ManuType, ms_to_country, pact_to_atModel, manuType_to_atModel, ReducEmHouse,
                           FracToepHouse_):
    r"""p_Nemidat(MS, AACT, "CH4", "LossHous", ManuType): the housing measures' effect on the manure's CH4, the
    measures' CH4 reductions weighted by their shares (l. 809-814; negative where a measure raises the CH4).

    CAPRI's GAMS (envind/ammo.gms l. 807-814):

        *   Correction factor for methane emissions due to abatement measures during housing (Franz Weiss)

            p_Nemidat(MS,AACT,"CH4","LossHous",ManuType) = SUM((ms_to_country(ms,country),atModel,ht) $ (pact_to_atModel(aact,atModel) $
                                                                                           manuType_to_atModel(manuType,atModel)),
        *                                                               percentage abatement with stable adaptation
                                                                       ReducEmHouse(country,atModel,"CH4",ht)/100.*
        *                                                              Share of particular abatement measures in housing
                                                                       FracToepHouse(country,atModel,ht)/100.);

    ReducEmHouse: {(country, atModel, gas, ht): %}; FracToepHouse_: FracToepHouse's result. Returns {(MS, AACT, "CH4",
    "LOSSHOUS", MANUTYPE): fraction} where not 0. Departures from CAPRI: none."""
    return _ch4_loss(MS, AACT, ManuType, ms_to_country, pact_to_atModel, manuType_to_atModel, ReducEmHouse,
                     FracToepHouse_, "LOSSHOUS")


def p_Nemidat_CH4_LossStor(MS, AACT, ManuType, ms_to_country, pact_to_atModel, manuType_to_atModel, ReducEmStorage,
                           FracToepStorage_):
    r"""p_Nemidat(MS, AACT, "CH4", "LossStor", ManuType): the storage covers' effect on the manure's CH4, the covers'
    CH4 reductions weighted by their shares (l. 870-874).

    CAPRI's GAMS (envind/ammo.gms l. 869-874):

        *   Correction factor for methane emissions due to abatement measures during storage (Franz Weiss)
            p_Nemidat(MS,AACT,"CH4","LossStor",ManuType) = SUM((ms_to_country(ms,country),atModel,stt) $ (pact_to_atModel(aact,atModel) $
                                                                                           manuType_to_atModel(manuType,atModel)),
                                                                          ReducEmStorage(country,atModel,"CH4",stt)/100.*
        *                                                                 Shares of storage cover types
                                                                          FracToepStorage(country,atModel,stt)/100.);

    Returns {(MS, AACT, "CH4", "LOSSSTOR", MANUTYPE): fraction} where not 0. Departures from CAPRI: none."""
    return _ch4_loss(MS, AACT, ManuType, ms_to_country, pact_to_atModel, manuType_to_atModel, ReducEmStorage,
                     FracToepStorage_, "LOSSSTOR")


def _ch4_loss(MS, AACT, ManuType, ms_to_country, pact_to_atModel, manuType_to_atModel, reduc, frac, item):
    countries = {}
    for m, c in ms_to_country:
        countries.setdefault(m, []).append(c)
    types = {}
    for p, t in pact_to_atModel:
        types.setdefault(p, set()).add(_u(t))
    of_mt = {}
    for mt, t in manuType_to_atModel:
        of_mt.setdefault(_u(mt), set()).add(_u(t))
    red = {}
    for (c, t, g, k), v in reduc.items():
        if _u(g) == "CH4":
            red.setdefault((c, _u(t)), {})[_u(k)] = float(v)
    fr = {}
    for (c, t, k), v in frac.items():
        fr.setdefault((c, _u(t)), {})[_u(k)] = float(v)
    out = {}
    for ms in MS:
        for act in AACT:
            for mt in ManuType:
                ts = types.get(act, set()) & of_mt.get(_u(mt), set())
                v = sum(r / 100. * fr.get((c, t), {}).get(k, 0.0) / 100.
                        for c in countries.get(ms, ()) for t in ts for k, r in red.get((c, t), {}).items())
                if v:
                    out[(ms, act, "CH4", item, _u(mt))] = v
    return out


def p_Nemidat_split_activities(p_Nemidat, DACT_TO_PACT, MACT):
    r"""p_Nemidat(MS, MACT, ...) of the high and low yield activities: the data activity's (DCOW to DCOL and DCOH, BULF,
    HEIF; l. 1145).

    CAPRI's GAMS (envind/ammo.gms l. 1144-1145):

        * transfers numbers for DCOW, BULF, HEIF to the respective high and low yield activities (needed in gascoeff.gms and gases.gms)
          p_Nemidat(MS,MACT,allmat,NemiFact,ALLTYPE) = sum(DACT_TO_PACT(DACT,MACT),p_Nemidat(MS,DACT,allmat,NemiFact,ALLTYPE));

    DACT_TO_PACT: {(data activity, activity)}; MACT: CAPRI's split animal activities (sets.gms l. 2308: DCOL, DCOH,
    BULL, BULH, HEIL, HEIH). Returns p_Nemidat with them. Departures from CAPRI: none."""
    out = dict(p_Nemidat)
    to = {p: [] for p in MACT}
    for d, p in DACT_TO_PACT:
        if p in to:
            to[p].append(d)
    for p, ds in to.items():
        for k in [k for k in out if k[1] == p]:
            del out[k]
        for (m, a, g, i, s), v in p_Nemidat.items():
            if a in ds:
                out[(m, p, g, i, s)] = out.get((m, p, g, i, s), 0.0) + v
    return out


def ScenYear(SIMY):
    r"""%ScenYear%, the MITERRA scenario year of a capmod run: 2000, 2020 for a simulation year after 2010
    (create_sim_ini_gdx.gms l. 176-178; the five-year steps of %finEC4MACS%, l. 183-192, are off). CAPREG's is 2000
    (envind/Miterra/scenario_settings.gms l. 90).

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 176-178):

        $SetGlobal ScenYear   2000
        $eval after2010 %simy% > 2010
        $if %after2010%==1 $setglobal scenYear 2020

    Departures from CAPRI: none."""
    return 2020 if int(SIMY) > 2010 else 2000
