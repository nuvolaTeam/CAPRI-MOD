r"""CAPRI's coefficients of the methane from manure management (envind/gascoeff.gms l. 520-640, star 3.0): the raw
coefficients, the climate shares, the tier 1 factors, the management systems' shares and their CH4 conversion factors,
and MCFMS, the methane conversion factor of the activity's manure, for gases.gms (capri_mod/environmental/equations/
gases.py).

The raw tables are CAPRI's own, written in envind/create_rawdat_gascoeff_gdx.gms and converted by tools/build/
build_gascoeff_tables.py (capri_data/sources/intermediate/envind: capri_emiscalc0, capri_tier1_manure_ef,
capri_share_clim_zone, capri_manure_mgt_share). The management systems' shares are MITERRA's (p_Nemidat), the branch
CAPRI takes with %storgrazInv% off (capmod/set_global_variables.gms l. 61, capreg/set_global_variables.gms l. 120;
gascoeff.gms l. 595-600); the UNFCCC time series (l. 578-588, CAPREG's time-series run) are not ported.

In this project's notation: s(r, c) the region's percent share of the climate cell c (the member state's where the
region has none), m(sys) the activity's share of its manure in the management system sys, f(c, sys) the system's CH4
conversion factor in the cell (the member state's, else the EU's), so MCFMS = sum_c s(r, c) / 100 sum_sys m(sys)
f(c, sys).

The functions take and return dicts keyed by CAPRI's index tuples; p_Nemidat's keys (MS, MAACT, gas, item, system) are
compared without case, as GAMS compares labels. Not ported (not used by the methane): GHGEFS (l. 539), the crop
residues (l. 560-562), the N2O conversion factors.
"""
from __future__ import annotations


def _nemi(p_Nemidat, ms, act, gas, item, system):
    """p_Nemidat(MS, MAACT, gas, item, system), the labels compared without case as GAMS does."""
    return float(p_Nemidat.get((ms, act, gas.upper(), item.upper(), system.upper()), 0.0) or 0.0)


def p_shareClimZone0_others(p_shareClimZone0):
    r"""p_shareClimZone0 of Turkey and the Western Balkans: Cyprus's, Italy's or Bulgaria's shares (l. 526-533).
    Returns the table with them.

    CAPRI's GAMS (envind/gascoeff.gms l. 526-533):

        p_shareClimZone0("TUR",climall)     =p_shareClimZone0("CY000000",climall);
        p_shareClimZone0("AL000000",climall)=p_shareClimZone0("IT000000",climall);
        p_shareClimZone0("MO000000",climall)=p_shareClimZone0("IT000000",climall);
        p_shareClimZone0("BA000000",climall)=p_shareClimZone0("BG000000",climall);
        p_shareClimZone0("MK000000",climall)=p_shareClimZone0("BG000000",climall);
        p_shareClimZone0("HR000000",climall)=p_shareClimZone0("BG000000",climall);
        p_shareClimZone0("CS000000",climall)=p_shareClimZone0("BG000000",climall);
        p_shareClimZone0("KO000000",climall)=p_shareClimZone0("BG000000",climall);

    Departures from CAPRI: none."""
    out = dict(p_shareClimZone0)
    for dst, src in (("TUR", "CY000000"), ("AL000000", "IT000000"), ("MO000000", "IT000000"), ("BA000000", "BG000000"),
                     ("MK000000", "BG000000"), ("HR000000", "BG000000"), ("CS000000", "BG000000"),
                     ("KO000000", "BG000000")):
        for k in [k for k in out if k[0] == dst]:
            del out[k]
        for (r, c), v in p_shareClimZone0.items():
            if r == src:
                out[(dst, c)] = v
    return out


def EMISCALC_raw(EMISCALC0):
    r"""EMISCALC(Rall, COLS, A, emisParGdx, "Y"): the raw coefficients CH4AN, CH4EN, YM, DE, ASH, B0 and NRET, the EU's
    rows of IPCC 2006 (l. 535). Returns {(region, activity, A, item): value}.

    CAPRI's GAMS (envind/gascoeff.gms l. 535):

           EMISCALC(Rall,COLS,A,emisParGdx,%1)                          = EMISCALC0(Rall,COLS,A,emisParGdx)                             ;

    Departures from CAPRI: none."""
    return dict(EMISCALC0)


def p_shareClimZone(p_shareClimZone0, RS, CLIM, CLIMCELS):
    r"""p_shareClimZone(Rall, CLIMALL): the raw shares (l. 537), a region without a climate zone all "cool", without a
    temperature cell all in cell 10 (l. 543-544).

    CAPRI's GAMS (envind/gascoeff.gms l. 537 and l. 543-544):

           p_shareClimZone(Rall,CLIMALL)                                = p_shareClimZone0(Rall,CLIMALL)                                ;
        ...
           p_shareClimZone(RS,"cool") $ (NOT sum(CLIM,p_shareClimZone(RS,CLIM))) =  100;
           p_shareClimZone(RS,"10") $ (NOT sum(CLIMCELS,p_shareClimZone(RS,CLIMCELS))) =  100;

    GAMS's label "cool" is the set element Cool. Departures from CAPRI: none."""
    out = dict(p_shareClimZone0)
    for r in RS:
        if not sum(float(out.get((r, c), 0.0) or 0.0) for c in CLIM):
            out[(r, "Cool")] = 100.0
        if not sum(float(out.get((r, c), 0.0) or 0.0) for c in CLIMCELS):
            out[(r, "10")] = 100.0
    return out


def p_tier1EmFactManMgt_EUGR_warm(p_tier1EmFactManMgt0, EUGR, MAACT, CLIMWARM):
    r"""p_tier1EmFactManMgt(Rall | EUGR, COLS, A, CLIMALL): the raw factors (l. 536), the warmest cells of an EU group
    at its "Warm" value (l. 549).

    CAPRI's GAMS (envind/gascoeff.gms l. 536 and l. 549):

           p_tier1EmFactManMgt(emisRegGdx,COLS,A,CLIMALL)               = p_tier1EmFactManMgt0(emisRegGdx,COLS,A,CLIMALL)               ;
        ...
           p_tier1EmFactManMgt(EUGR,MAACT,"T",CLIMWARM) = p_tier1EmFactManMgt(EUGR,MAACT,"T","Warm");

    Departures from CAPRI: none."""
    out = dict(p_tier1EmFactManMgt0)
    for g in EUGR:
        for a in MAACT:
            for c in CLIMWARM:
                v = out.get((g, a, "T", "Warm"), 0.0)
                if v:
                    out[(g, a, "T", c)] = v
                else:
                    out.pop((g, a, "T", c), None)
    return out


def p_tier1EmFactManMgt_MS(p_tier1EmFactManMgt, MS, EUGR_TO_MS, CLIMALL, p_Nemidat):
    r"""p_tier1EmFactManMgt(MS, MAACT, "T", CLIMALL) of the hens, poultry fattening and sheep and goats: the member
    state's factor (its EU group's where it has none) less MITERRA's CH4 losses of the solid system in housing and
    storage (l. 553-555), the ammonia abatement techniques' effect. Returns the table with them.

    CAPRI's GAMS (envind/gascoeff.gms l. 553-555):

           p_tier1EmFactManMgt(MS,MAACT,"T",CLIMALL) $ (SAMEAS(MAACT,"HENS") or SAMEAS(MAACT,"POUF") or SAMEAS(MAACT,"SHGM") or SAMEAS(MAACT,"SHGF"))
                                         = (p_tier1EmFactManMgt(MS,MAACT,"T",CLIMALL) + sum(EUGR_TO_MS(EUGR,MS),p_tier1EmFactManMgt(EUGR,MAACT,"T",CLIMALL)) $ (NOT p_tier1EmFactManMgt(MS,MAACT,"T",CLIMALL)))
                                          * (1-p_Nemidat(MS,MAACT,"CH4","LossHous","Solid") - p_Nemidat(MS,MAACT,"CH4","LossStor","Solid"));

    EUGR_TO_MS: {(EU group, member state)}. Departures from CAPRI: none."""
    out = dict(p_tier1EmFactManMgt)
    groups = {}
    for g, m in EUGR_TO_MS:
        groups.setdefault(m, []).append(g)
    for ms in MS:
        for a in ("HENS", "POUF", "SHGM", "SHGF"):
            f = 1 - _nemi(p_Nemidat, ms, a, "CH4", "LossHous", "Solid") - _nemi(p_Nemidat, ms, a, "CH4", "LossStor", "Solid")
            for c in CLIMALL:
                own = float(p_tier1EmFactManMgt.get((ms, a, "T", c), 0.0) or 0.0)
                v = (own + (sum(float(p_tier1EmFactManMgt.get((g, a, "T", c), 0.0) or 0.0) for g in groups.get(ms, ()))
                            if not own else 0.0)) * f
                if v:
                    out[(ms, a, "T", c)] = v
                else:
                    out.pop((ms, a, "T", c), None)
    return out


def p_manureMgtShare_EU_CH4CONV(p_manureMgtShare0, MAACT, CLIMWARM, CLIMCOOL, CLIMTEMP, ManSys):
    r"""p_manureMgtShare(Rall | EUGR, COLS, A, EMISPAR, CLIMALL, ManSys): the raw shares and factors (l. 538); the EU's
    CH4 conversion factors of the warmest cells at its "Warm" value, of the cool and temperate cells at its "Cool" and
    "Temperate" values where the cell has none (l. 568-572).

    CAPRI's GAMS (envind/gascoeff.gms l. 538 and l. 568-572):

           p_manureMgtShare(emisRegGdx,COLS,A,EMISPAR,CLIMALL,ManSys)   = p_manureMgtShare0(emisRegGdx,COLS,A,EMISPAR,CLIMALL,ManSys)   ;
        ...
           p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMWARM,ManSys) = p_manureMgtShare("EU000000",MAACT,"T","CH4CONV","Warm",ManSys);
           p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMCOOL,ManSys) $ (NOT p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMCOOL,ManSys)) =
                                                                    p_manureMgtShare("EU000000",MAACT,"T","CH4CONV","Cool",ManSys);
           p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMTEMP,ManSys) $ (NOT p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMTEMP,ManSys)) =
                                                                    p_manureMgtShare("EU000000",MAACT,"T","CH4CONV","Temperate",ManSys);

    Departures from CAPRI: none."""
    out = dict(p_manureMgtShare0)
    eu = "EU000000"
    for a in MAACT:
        for s in ManSys:
            w = out.get((eu, a, "T", "CH4CONV", "Warm", s), 0.0)
            for c in CLIMWARM:
                if w:
                    out[(eu, a, "T", "CH4CONV", c, s)] = w
                else:
                    out.pop((eu, a, "T", "CH4CONV", c, s), None)
            for cells, zone in ((CLIMCOOL, "Cool"), (CLIMTEMP, "Temperate")):
                z = out.get((eu, a, "T", "CH4CONV", zone, s), 0.0)
                for c in cells:
                    if not out.get((eu, a, "T", "CH4CONV", c, s)) and z:
                        out[(eu, a, "T", "CH4CONV", c, s)] = z
    return out


def p_manureMgtShare_MS_MANAG(p_manureMgtShare, MS, MAACT, CLIMALL, p_Nemidat):
    r"""p_manureMgtShare(MS, MAACT, "T", "MANAG", CLIMALL, Pasture | Solid | Liquid): MITERRA's grazing share, and its
    solid and liquid shares of the rest (l. 596-599: %storgrazInv% off, the branch of capmod and of CAPREG's base
    year).

    CAPRI's GAMS (envind/gascoeff.gms l. 595-600):

        $else
           $$setlocal MgtShareTime OFF
           p_manureMgtShare(MS,MAACT,"T","MANAG",CLIMALL,"Pasture") = p_Nemidat(MS,MAACT,"N","TypeShare","GRAZ");
           p_manureMgtShare(MS,MAACT,"T","MANAG",CLIMALL,"Solid")   = (1. - p_Nemidat(MS,MAACT,"N","TypeShare","GRAZ")) * p_Nemidat(MS,MAACT,"N","TypeShare","Solid");
           p_manureMgtShare(MS,MAACT,"T","MANAG",CLIMALL,"Liquid")  = (1. - p_Nemidat(MS,MAACT,"N","TypeShare","GRAZ")) * p_Nemidat(MS,MAACT,"N","TypeShare","Liquid");
        $endif

    Departures from CAPRI: none."""
    out = dict(p_manureMgtShare)
    for ms in MS:
        for a in MAACT:
            g = _nemi(p_Nemidat, ms, a, "N", "TypeShare", "GRAZ")
            vals = {"Pasture": g,
                    "Solid": (1. - g) * _nemi(p_Nemidat, ms, a, "N", "TypeShare", "Solid"),
                    "Liquid": (1. - g) * _nemi(p_Nemidat, ms, a, "N", "TypeShare", "Liquid")}
            for c in CLIMALL:
                for s, v in vals.items():
                    if v:
                        out[(ms, a, "T", "MANAG", c, s)] = v
                    else:
                        out.pop((ms, a, "T", "MANAG", c, s), None)
    return out


def p_manureMgtShare_MS_CH4CONV(p_manureMgtShare, MS, MAACT, CLIMALL):
    r"""p_manureMgtShare(MS, MAACT, "T", "CH4CONV", CLIMALL, Pasture | Solid | Liquid): the EU's factor for pasture,
    the member state's for the solid and liquid systems where it has one, else the EU's (l. 604-614); the ammonia
    abatement techniques' effect is applied in gases.gms (or the supply model) instead.

    CAPRI's GAMS (envind/gascoeff.gms l. 601-614):

        *  Effects of NH3 abatement technics from Miterra on CH4 emissions
        *  fw: due to the endogenous technologies we have to remove the impact of ammonia abatement techs here and apply it in supply_model.gms and gases.gms
        *  otherwise we get a double counting
           p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Pasture") = p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMALL,"Pasture");
           p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Solid") = (p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Solid")
                                                            + p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMALL,"Solid") $ (NOT p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Solid")))
        *                                                      * (1. - p_Nemidat(MS,MAACT,"CH4","LossHous","Solid") - p_Nemidat(MS,MAACT,"CH4","LossStor","Solid"))
        ;

           p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Liquid")
                                                            = (p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Liquid")
                                                            + p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMALL,"Liquid") $ (NOT p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Liquid")))
        *                                                      * (1. - p_Nemidat(MS,MAACT,"CH4","LossHous","Liquid") - p_Nemidat(MS,MAACT,"CH4","LossStor","Liquid"))
        ;

    Departures from CAPRI: none."""
    out = dict(p_manureMgtShare)
    eu = "EU000000"
    for ms in MS:
        for a in MAACT:
            for c in CLIMALL:
                v = p_manureMgtShare.get((eu, a, "T", "CH4CONV", c, "Pasture"), 0.0)
                vals = {"Pasture": v}
                for s in ("Solid", "Liquid"):
                    own = float(p_manureMgtShare.get((ms, a, "T", "CH4CONV", c, s), 0.0) or 0.0)
                    vals[s] = own + (float(p_manureMgtShare.get((eu, a, "T", "CH4CONV", c, s), 0.0) or 0.0)
                                     if not own else 0.0)
                for s, x in vals.items():
                    if x:
                        out[(ms, a, "T", "CH4CONV", c, s)] = x
                    else:
                        out.pop((ms, a, "T", "CH4CONV", c, s), None)
    return out


def p_manureMgtShare_EUGR_MANAG(p_manureMgtShare, EUGR, MAACT, CLIMALL, ManSys):
    r"""p_manureMgtShare(EUGR, MAACT, "T", "MANAG", CLIMALL, ManSys): an EU group's shares in every climate at its
    "Temperate" values (l. 618).

    CAPRI's GAMS (envind/gascoeff.gms l. 616-618):

        *  The management option and the N2O coefficient factor do not vary with the weather acording to IPCC data (Western Europe data)

           p_manureMgtShare(EUGR,MAACT,"T","MANAG",CLIMALL,MANSYS)    = p_manureMgtShare(EUGR,MAACT,"T","MANAG","Temperate",MANSYS) ;

    Departures from CAPRI: none."""
    out = dict(p_manureMgtShare)
    for g in EUGR:
        for a in MAACT:
            for s in ManSys:
                v = p_manureMgtShare.get((g, a, "T", "MANAG", "Temperate", s), 0.0)
                for c in CLIMALL:
                    if v:
                        out[(g, a, "T", "MANAG", c, s)] = v
                    else:
                        out.pop((g, a, "T", "MANAG", c, s), None)
    return out


def p_manureMgtShare_A(p_manureMgtShare, A, MS, p_technFact_MS):
    r"""p_manureMgtShare(Rall, MAACT, A, EMISPAR, CLIMALL, ManSys) of every technology: the EU's and the EU groups'
    the "T" values, a member state's where its technology has a share (l. 624-627).

    CAPRI's GAMS (envind/gascoeff.gms l. 622-627):

        *   --- copy IPCC calculation factor from standard to all technologies

           p_manureMgtShare("EU000000",MAACT,A,EMISPAR,CLIMALL,MANSYS)     = p_manureMgtShare("EU000000",MAACT,"T",EMISPAR,CLIMALL,MANSYS);
        *
           p_manureMgtShare(EUGR,MAACT,A,EMISPAR,CLIMALL,MANSYS)      = p_manureMgtShare(EUGR,MAACT,"T",EMISPAR,CLIMALL,MANSYS);
           p_manureMgtShare(MS,MAACT,A,EMISPAR,CLIMALL,MANSYS)         $ p_technFact(MS,MAACT,"LEVL",A)    = p_manureMgtShare(MS,MAACT,"T",EMISPAR,CLIMALL,MANSYS);

    p_technFact_MS: {(MS, MAACT, A): share} of the member states (p_technFact(MS, MAACT, "LEVL", A)). The EU groups
    are the table's regions other than EU000000 and the member states. Departures from CAPRI: none."""
    out = dict(p_manureMgtShare)
    ms_set = set(MS)
    base = [(k, v) for k, v in p_manureMgtShare.items() if k[2] == "T"]
    for (r, a, _t, par, c, s), v in base:
        for t in A:
            if t == "T":
                continue
            if r in ms_set and not p_technFact_MS.get((r, a, t)):
                continue
            out[(r, a, t, par, c, s)] = v
    return out


def EMISCALC_MCFMS(RU, MS_of, MAACT, A, CLIMCELS, ManSys, p_technFact, p_shareClimZone, p_manureMgtShare, EUGR_TO_MS):
    r"""EMISCALC(RU, MAACT, A, "MCFMS", "Y"): the methane conversion factor of the activity's manure, kg CH4 emitted per
    kg the manure can produce at most: over the temperature cells of the region (the member state's where the region
    has none) and the management systems, the system's share (the member state's, its EU group's where the member state
    has none in the cell) times its CH4 conversion factor (the member state's, else the EU's "T") (l. 632-640;
    %MgtShareTime% off). Returns {(RU, MAACT, A): MCFMS} where the technology has a share.

    CAPRI's GAMS (envind/gascoeff.gms l. 630-640):

        *    --- MCFMS: kg CH4 emitted in relation to kh CH4 maximally produced from manure

           EMISCALC(RU,MAACT,A,"MCFMS",%1) $ p_technFact(RU,MAACT,"LEVL",A)
                       = SUM((CLIMCELS,MANSYS,MAP_RR(MS,RU)), (p_shareClimZone(RU,CLIMCELS) + p_shareClimZone(MS,CLIMCELS) $ (NOT sum(CLIMCELS1,p_shareClimZone(RU,CLIMCELS1)))) * 0.01 *
        $ifi NOT %MgtShareTime%==ON   (p_manureMgtShare(MS,MAACT,A,"MANAG",CLIMCELS,MANSYS) +
        $ifi     %MgtShareTime%==ON   (p_manureMgtShareTime(MS,MAACT,A,MANSYS, %1) +
                                             sum(EUGR_TO_MS(EUGR,MS),p_manureMgtShare(EUGR,MAACT,"T","MANAG",CLIMCELS,MANSYS)) $ (NOT
        $ifi NOT %MgtShareTime%==ON                                                         sum(MANSYS1,p_manureMgtShare(MS,MAACT,A,"MANAG",CLIMCELS,MANSYS1)))) *
        $ifi     %MgtShareTime%==ON                                                         sum(MANSYS1,p_manureMgtShareTime(MS,MAACT,A,MANSYS1,%1)))) *
                                            (p_manureMgtShare(MS,MAACT,A,"CH4CONV",CLIMCELS,MANSYS) + p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMCELS,MANSYS)
                                                                                          $ (NOT p_manureMgtShare(MS,MAACT,A,"CH4CONV",CLIMCELS,MANSYS))));

    MS_of: {RU: its member state (MAP_RR)}; p_technFact: {(RU, MAACT, A): share}. Departures from CAPRI: none."""
    groups = {}
    for g, m in EUGR_TO_MS:
        groups.setdefault(m, []).append(g)
    out = {}
    for ru in RU:
        ms = MS_of.get(ru)
        if ms is None:
            continue
        sh_ru = {c: float(p_shareClimZone.get((ru, c), 0.0) or 0.0) for c in CLIMCELS}
        use_ms = not sum(sh_ru.values())
        for a in MAACT:
            for t in A:
                if not p_technFact.get((ru, a, t)):
                    continue
                tot = 0.0
                for c in CLIMCELS:
                    sh = sh_ru[c] + (float(p_shareClimZone.get((ms, c), 0.0) or 0.0) if use_ms else 0.0)
                    if not sh:
                        continue
                    own_any = sum(float(p_manureMgtShare.get((ms, a, t, "MANAG", c, s1), 0.0) or 0.0) for s1 in ManSys)
                    for s in ManSys:
                        m = float(p_manureMgtShare.get((ms, a, t, "MANAG", c, s), 0.0) or 0.0)
                        if not own_any:
                            m += sum(float(p_manureMgtShare.get((g, a, "T", "MANAG", c, s), 0.0) or 0.0)
                                     for g in groups.get(ms, ()))
                        if not m:
                            continue
                        f = float(p_manureMgtShare.get((ms, a, t, "CH4CONV", c, s), 0.0) or 0.0)
                        if not f:
                            f = float(p_manureMgtShare.get(("EU000000", a, "T", "CH4CONV", c, s), 0.0) or 0.0)
                        tot += sh * 0.01 * m * f
                out[(ru, a, t)] = tot
    return out
