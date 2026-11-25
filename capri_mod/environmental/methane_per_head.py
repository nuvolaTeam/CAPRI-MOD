"""The methane per head of CAPRI's livestock activities at "Y": envind/gascoeff.gms, digestibility.gms and gases.gms
(sections 1 and 2) run in CAPRI's order on a year's data, as CAPRI runs them at "Y" in CAPREG (capreg.gms l. 2299,
2314), in a capmod step with %ghgAbatement% on (capmod.gms l. 778, 1106, 1139) and in the reports at the solution
(reports/sol_simy.gms l. 1669-1716).

The statements are those of capri_mod/environmental/equations/gascoeff.py, capri_mod/supply/equations/digestibility.py
and capri_mod/environmental/equations/gases.py; this module only feeds them in CAPRI's order:

1. gascoeff (l. 526-640): the raw coefficients, the climate shares, the tier 1 factors, the management systems'
   shares and CH4 conversion factors, MCFMS;
2. digestibility (l. 31-170, 197-253), per regional unit and cattle activity: the products' composition and energy,
   the feed bulks' by the member state's feed use, the ration's DE, ASH and GE (technology "T");
3. gases (l. 317-443): NEG, GENE, the gross energy intake, CH4ENT (tier 2, else tier 1), VSER, CH4MAN (tier 2, else
   tier 1) and, with %ghgAbatement% off, the ammonia abatement techniques' factor.

    from capri_mod.environmental.methane_per_head import MethaneInputs, methane_per_head
    out = methane_per_head(MethaneInputs(...))     # {(RU, MAACT, A): {"CH4ENT": ..., "CH4MAN": ..., ...}}
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from capri_mod.environmental.equations import gascoeff as gc
from capri_mod.environmental.equations import gases as gs
from capri_mod.supply.equations import digestibility as dg

EU = "EU000000"


@dataclass
class MethaneInputs:
    """The year's inputs. DATA: {(region, col, row): value} at "Y" of the regional units and their member states (DRMA,
    FIDI and CRPR of the products, FEDM and INTF of the member state, FLEG's LEVL, the rations DATA(RU, MAACT, FEED));
    MS_of: {RU: its member state} (MAP_RR); p_technFact: {(RU, MAACT, A): share} (LEVL) of the regional units and the
    member states; p_animReq: {(RU, MAACT, A, item)} (NEM, ENNE, and GENE where set); p_animReqSubEne: {(RU, MAACT, A,
    SUBENE)}; p_animProdDays: {(RU, MAACT, A)}; p_Nemidat: {(MS, MAACT, gas, item, system)} (MITERRA's); p_nfixRate_gras:
    {MS: rate} with nfix_default for the others (fert/fertpar.gms l. 295, p_nitrFact("RALL", "GRAE", "BioFix"));
    digestpar: {product: {item: value}}, CAPRI's p_digestPar("EU", "DCOL", ...) with the DEF_PRD fill; FEED_TO_O: the
    feed bulks' products; EMISCALC0, p_tier1EmFactManMgt0, p_shareClimZone0, p_manureMgtShare0: CAPRI's raw tables
    (tools/build/build_gascoeff_tables.py); the sets as CAPRI's (capri_data/codes/capri); ghgAbatement: CAPRI's switch
    (off: the ammonia techniques' factor on CH4MAN in gases.gms l. 437-443)."""
    RU: tuple
    MS_of: dict
    MAACT: tuple
    CATACT: tuple
    A: tuple
    DATA: dict
    p_technFact: dict
    p_animReq: dict
    p_animReqSubEne: dict
    p_animProdDays: dict
    p_Nemidat: dict
    p_nfixRate_gras: dict
    nfix_default: float
    digestpar: dict
    FEED_TO_O: tuple
    EMISCALC0: dict
    p_tier1EmFactManMgt0: dict
    p_shareClimZone0: dict
    p_manureMgtShare0: dict
    RS: tuple
    CLIMALL: tuple
    CLIM: tuple
    CLIMCELS: tuple
    CLIMCOOL: tuple
    CLIMTEMP: tuple
    CLIMWARM: tuple
    EUGR: tuple
    ManSys: tuple
    EUGR_TO_MS: tuple
    SUBENE: tuple = ("NEL", "NEM", "NEA", "NEP", "NEG")
    ghgAbatement: bool = False
    log: dict = field(default_factory=dict)


def normalise_nemidat(rows) -> dict:
    """p_Nemidat {(MS, MAACT, GAS, ITEM, SYSTEM): value} from (ms, act, gas, item, system, value) rows: the labels'
    case dropped as GAMS compares them (CAPREG's files write n, liquid, solid)."""
    return {(m, a, g.upper(), i.upper(), s.upper()): float(v) for m, a, g, i, s, v in rows}


def labels_as(codes, spelt) -> tuple:
    """The codes with the spelling of the same labels in spelt: GAMS compares labels without case and writes each in
    the case of its first use, so a set read from one GDX (ManSys: liquid, solid) and CAPRI's tables (Liquid, Solid)
    name the same element differently."""
    by_low = {str(x).lower(): x for x in spelt}
    return tuple(by_low.get(str(c).lower(), c) for c in codes)


def gascoeff_state(m: MethaneInputs) -> dict:
    """gascoeff.gms l. 526-640 at "Y": {"EMISCALC": raw, "p_shareClimZone", "p_tier1EmFactManMgt",
    "p_manureMgtShare", "MCFMS"}. The management systems are named as in CAPRI's tables and gascoeff.gms's
    statements (labels_as)."""
    MS = tuple(sorted(set(m.MS_of.values())))
    m.ManSys = labels_as(m.ManSys, {k[5] for k in m.p_manureMgtShare0} | {"Pasture", "Solid", "Liquid"})
    sh0 = gc.p_shareClimZone0_others(m.p_shareClimZone0)
    emis = gc.EMISCALC_raw(m.EMISCALC0)
    sh = gc.p_shareClimZone(sh0, m.RS, m.CLIM, m.CLIMCELS)
    t1 = gc.p_tier1EmFactManMgt_EUGR_warm(m.p_tier1EmFactManMgt0, m.EUGR, m.MAACT, m.CLIMWARM)
    t1 = gc.p_tier1EmFactManMgt_MS(t1, MS, m.EUGR_TO_MS, m.CLIMALL, m.p_Nemidat)
    mg = gc.p_manureMgtShare_EU_CH4CONV(m.p_manureMgtShare0, m.MAACT, m.CLIMWARM, m.CLIMCOOL, m.CLIMTEMP, m.ManSys)
    mg = gc.p_manureMgtShare_MS_MANAG(mg, MS, m.MAACT, m.CLIMALL, m.p_Nemidat)
    mg = gc.p_manureMgtShare_MS_CH4CONV(mg, MS, m.MAACT, m.CLIMALL)
    mg = gc.p_manureMgtShare_EUGR_MANAG(mg, m.EUGR, m.MAACT, m.CLIMALL, m.ManSys)
    tf_ms = {(r, a, t): v for (r, a, t), v in m.p_technFact.items() if r in MS}
    mg = gc.p_manureMgtShare_A(mg, m.A, MS, tf_ms)
    mcf = gc.EMISCALC_MCFMS(m.RU, m.MS_of, m.MAACT, m.A, m.CLIMCELS, m.ManSys, m.p_technFact, sh, mg, m.EUGR_TO_MS)
    return {"EMISCALC": emis, "p_shareClimZone": sh, "p_tier1EmFactManMgt": t1, "p_manureMgtShare": mg, "MCFMS": mcf}


def _rows_of(FEED_TO_O) -> dict:
    out = defaultdict(list)
    for f, r in FEED_TO_O:
        out[f].append(r)
    return out


def products(m: MethaneInputs, ru: str, act: str) -> tuple:
    """digestibility.gms l. 31-170 for the unit and cattle activity: ({product: {item: value}}, {product: dry
    matter}). The products are the table's, GRAS and OFAR, and those of the feed bulks."""
    D, ms = m.DATA, m.MS_of[ru]
    T = m.digestpar
    rows = set(T) | {"GRAS", "OFAR"} | {r for _, r in m.FEED_TO_O} | {f for f, _ in m.FEED_TO_O}
    DM = {r: dg.p_DryMatterContent(D.get((ru, "DRMA", r)), D.get((ms, "DRMA", r), 0.0)) for r in rows}
    nfix = dg.p_nfixRate_gras_digest(m.p_nfixRate_gras.get(ms, m.nfix_default))
    P = {r: dict(v) for r, v in T.items()}
    graz = gc._nemi(m.p_Nemidat, ms, act, "N", "TypeShare", "GRAZ")
    items = set(T.get("GRPS", {})) | set(T.get("GRSI", {})) | set(T.get("GRHA", {})) | set(T.get("LGPS", {})) \
        | set(T.get("LGSI", {})) | set(T.get("LGHA", {}))
    P["GRAS"] = {it: dg.p_digestPar_GRAS(graz, nfix, *(T.get(r, {}).get(it, 0.0)
                                                      for r in ("GRPS", "LGPS", "GRSI", "LGSI", "GRHA", "LGHA")))
                 for it in items}
    fleg = D.get((ru, "FLEG", "LEVL"), 0.0)
    if fleg:
        P["OFAR"] = {it: dg.p_digestPar_OFAR(P["GRAS"].get(it, 0.0), T.get("LGSI", {}).get(it, 0.0),
                                             T.get("LGHA", {}).get(it, 0.0), fleg)
                     for it in set(P["GRAS"]) | set(T.get("LGSI", {})) | set(T.get("LGHA", {}))}
    for p in P.values():                                               # l. 60
        if p.get("EE", 0.0) >= 1:
            p["FAT"] = dg.p_digestPar_FAT(p["EE"], p.get("FAT"))
    for r, p in P.items():                                             # l. 64-100
        F = dg.p_nutPerDryMt(D.get((ru, "FIDI", r)), DM.get(r))
        C = dg.p_nutPerDryMt(D.get((ru, "CRPR", r)), DM.get(r))
        F, C = dg.p_nutPerDryMt_bounds(F, C, p.get("NDF", 0.0), p.get("CP", 0.0))
        fat, ash, ndicp = p.get("FAT", 0.0), p.get("ASH", 0.0), p.get("NDICP", 0.0)
        p["CP"] = dg.p_digestPar_CP(p.get("CP", 0.0), C, F, fat, ash, ndicp)
        p["NDF"] = dg.p_digestPar_NDF_data(p.get("NDF", 0.0), C, F, fat, ash, ndicp)
        p["NDF"] = dg.p_digestPar_NDF_min(p["NDF"], ndicp, p.get("CAT", 0.0))
    nem = {t: m.p_animReq.get((ru, act, t, "NEM"), 0.0) for t in m.A if m.p_animReq.get((ru, act, t, "NEM"))}
    enne = {t: m.p_animReq.get((ru, act, t, "ENNE"), 0.0) for t in m.A}
    tfa = {t: m.p_technFact.get((ru, act, t), 0.0) for t in m.A}
    ai = dg.p_actualIntake(enne, nem, tfa)                             # l. 150-153
    for r, p in P.items():                                             # l. 104-170
        g = p.get
        cat = g("CAT", 0.0)
        p["TDNFC"] = dg.p_digestPar_TDNFC(g("NDF"), g("NDICP"), g("CP"), g("EE"), g("ASH"), g("PAF"), cat)
        p["TDCP"] = dg.p_digestPar_TDCP(g("CP", 0.0), g("ADICP", 0.0), cat)
        p["TDFA"] = dg.p_digestPar_TDFA(g("FAT"))
        p["TDNDF"] = dg.p_digestPar_TDNDF(g("NDF", 0.0), g("NDICP", 0.0), g("LI", 0.0), cat)
        p["TDN"] = dg.p_digestPar_TDN(p["TDNFC"], p["TDCP"], p["TDFA"], p["TDNDF"], cat)
        p["DE"] = dg.p_digestPar_DE_maintenance(p["TDNFC"], p["TDNDF"], p["TDCP"], p["TDFA"], cat)
        p["GE"] = dg.p_digestPar_GE(g("CP", 0.0), g("FAT", 0.0), g("ASH", 0.0), cat)
        p["DE"], p["GE"] = dg.p_digestPar_DE_GE_oils(r, p["DE"], p["GE"])
        p["DIS"] = dg.p_digestPar_DIS(p["TDN"], cat, ai)
        p["DE"] = dg.p_digestPar_DE_intake(p["DE"], p["DIS"])
    return P, DM


def ration(m: MethaneInputs, ru: str, act: str) -> tuple:
    """digestibility.gms l. 197-253 for the unit and cattle activity: (DE, ASH, GE) of its ration, EMISCALC(RU, act,
    "T", ...), from the products' values and the member state's feed use."""
    D, ms = m.DATA, m.MS_of[ru]
    P, DM = products(m, ru, act)
    rows_of = _rows_of(m.FEED_TO_O)
    vals = {"DE": {}, "GE": {}, "ASH": {}}
    for feed, rows in rows_of.items():
        w = {r: (D.get((ms, "FEDM", r), 0.0) + D.get((ms, "INTF", r), 0.0)) * DM.get(r, 0.0) for r in rows}
        W = sum(w.values())
        sh = [dg.p_digestPar_shFEED(w[r], W) for r in rows]
        for it in vals:
            vals[it][feed] = dg.p_digestPar_FEED([P.get(r, {}).get(it, 0.0) for r in rows], sh)
    rat = {f: D.get((ru, act, f), 0.0) for f in rows_of}
    return dg.EMISCALC_DE_ASH_GE(rat, {f: DM.get(f, 0.0) for f in rows_of}, vals["DE"], vals["GE"], vals["ASH"])


def methane_per_head(m: MethaneInputs) -> dict:
    """gascoeff, digestibility and gases at "Y" (module docstring): {(RU, MAACT, A): {item: value}} of the activities
    and technologies with a share, items DE, GE, ASH (the ration's, cattle "T"), NEG, GENE, GENE_req, CH4ENT, VSER,
    MCFMS, CH4MAN (kg CH4 per head and year)."""
    gcs = gascoeff_state(m)
    E, t1, sh = gcs["EMISCALC"], gcs["p_tier1EmFactManMgt"], gcs["p_shareClimZone"]
    groups = {}
    for g, ms in m.EUGR_TO_MS:
        groups.setdefault(ms, []).append(g)
    reg = {}                                                           # EMISCALC(RU, CATACT, "T", DE | ASH | GE)
    for ru in m.RU:
        for act in m.CATACT:
            if not any(m.p_technFact.get((ru, act, t)) for t in m.A):
                continue
            de, ash, ge = ration(m, ru, act)
            if de:
                reg[(ru, act, "T")] = {"DE": de, "ASH": ash, "GE": ge}
    out = {}
    for ru in m.RU:
        ms = m.MS_of[ru]
        for act in m.MAACT:
            for t in m.A:
                share = m.p_technFact.get((ru, act, t), 0.0)
                if not share:
                    continue
                r = reg.get((ru, act, t), {})

                def eu(item):
                    return E.get((EU, act, t, item), 0.0)

                def own(item):                                 # the region's raw coefficient (CAPRI's are EU rows)
                    return E.get((ru, act, t, item), 0.0)
                de_r, de_eu = r.get("DE", 0.0) or own("DE"), eu("DE")
                neg, neg_eu = gs.EMISCALC_NEG(de_r), gs.EMISCALC_NEG(de_eu)
                gene, gene_eu = gs.EMISCALC_GENE(de_r), gs.EMISCALC_GENE(de_eu)
                days = m.p_animProdDays.get((ru, act, t), 0.0)
                has_ym = bool(own("YM") or eu("YM"))
                if has_ym:
                    sub = {s: m.p_animReqSubEne.get((ru, act, t, s), 0.0) for s in m.SUBENE}
                    gene_req = gs.p_animReq_GENE(sub, neg, neg_eu, gene, gene_eu, de_r, de_eu)
                    ch4ent = gs.EMISCALC_CH4ENT_tier2(own("YM"), eu("YM"), gene_req, days)
                else:
                    gene_req = m.p_animReq.get((ru, act, t, "GENE"), 0.0)
                    ch4ent = 0.0
                ch4ent = gs.EMISCALC_CH4ENT_tier1(ch4ent, own("CH4EN"), eu("CH4EN"), days, True)
                ash_r = r.get("ASH", 0.0) or own("ASH")
                vser = gs.EMISCALC_VSER(gene_req, r.get("GE", 0.0), de_r, de_eu, ash_r, eu("ASH")) if (de_r or de_eu) else 0.0
                mcf = gcs["MCFMS"].get((ru, act, t), 0.0)
                ch4man = gs.EMISCALC_CH4MAN_tier2(vser, own("B0"), eu("B0"), mcf, days)
                cells = m.CLIMCELS
                ch4man = gs.EMISCALC_CH4MAN_tier1(
                    ch4man, {c: t1.get((ms, act, t, c), 0.0) for c in cells},
                    {c: sum(t1.get((g, act, t, c), 0.0) for g in groups.get(ms, ())) for c in cells},
                    {c: sh.get((ru, c), 0.0) for c in cells}, {c: sh.get((ms, c), 0.0) for c in cells}, days, True)
                if not m.ghgAbatement:
                    n = lambda g_, i, s: gc._nemi(m.p_Nemidat, ms, act, g_, i, s)   # noqa: E731
                    ch4man = gs.EMISCALC_CH4MAN_NH3_techs(
                        ch4man, n("CH4", "LossHous", "Solid"), n("CH4", "LossStor", "Solid"), n("N", "TypeShare", "Solid"),
                        n("CH4", "LossHous", "Liquid"), n("CH4", "LossStor", "Liquid"), n("N", "TypeShare", "Liquid"))
                out[(ru, act, t)] = {"DE": de_r, "ASH": r.get("ASH", 0.0), "GE": r.get("GE", 0.0), "NEG": neg,
                                     "GENE": gene, "GENE_req": gene_req, "CH4ENT": ch4ent, "VSER": vser, "MCFMS": mcf,
                                     "CH4MAN": ch4man}
    return out
