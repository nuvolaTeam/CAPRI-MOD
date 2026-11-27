"""The mitigation options' items of a region's solution for the income report (income I1), block by block: CAPRI's
accounting cost (the input mitiI in TOIN), revenue (the output mitiO in TOOU) and PMP cost (mitiPmp, kept apart, not
in MGVA), from each block's solved shares and its data's own columns, through CAPRI's report statements
(capri_mod/coupling/equations/sol_simy.py, reports/sol_simy.gms l. 1049-1465).

The subsidy (mitiSubs, added to the premiums) is 0 in the model's runs: CAPRI sets the options' subsidies in
envind/miti_subsidy.gms only with %ghgMitiSubsidy% on (capmod.gms l. 1135), in its subsidy scenarios
(pol_input/ecampa/subs*), neither in its 2030 reference nor in its Green Deal step, and the model has no such setting.

Units: EUR 1000 per region (the income module's), from the data's EUR per t of N.
"""
from __future__ import annotations

from capri_mod.coupling.equations.sol_simy import (p_ghgMiti_emisAll_cost, p_ghgMiti_emisAll_cost_GainsTechFert,
                                                   p_ghgMiti_emisAll_pmpcost_GainsTechFert,
                                                   p_ghgMiti_emisAll_revenue, p_ghgMiti_emisAll_revenue_GainsTechFert)
from capri_mod.data.definitions import capri_ms

#: the inhibitor on manure: its own block (targFertMan), not among the options on mineral N
_MANURE_OPTION = "NITR_INH_MAN"


def _col(row, name) -> float:
    """A data row's value, 0 where the row or the value is missing (CAPRI's empty parameter)."""
    if row is None:
        return 0.0
    v = getattr(row, name, None)
    return float(v) if v is not None and v == v else 0.0


def fert_options_items(region, shares, nmin_saving, N_mineral_t, rows) -> dict:
    """The fertiliser options on mineral N (CAPRI's GainsTechFert on targFertSyn, the model's fert_tech block) of a
    region's solution: their cost, revenue and PMP cost in EUR 1000, CAPRI's per-crop statements
    (p_ghgMiti_emisAll_*_GainsTechFert) summed over the crops, so on the region's mineral N.

    shares: {option: v_miti} (SupplyResult.fert_tech_shares); nmin_saving: {option: CAPRI's othImpact NMIN}
    (SupplyResult.fert_nmin, the options' N saving); N_mineral_t: the mineral N bought at the solution (t; CAPRI's
    NETF(NITF), which the crops' NMIN add up to, calc_fert_dist.gms); rows: {(region, option): data row} of
    fert_options_jul15.csv, the region's row where it has one (VRT_SRUC, VRT_KTBL), else its member state's (the
    statements' "$ (NOT ...)"). The data carry no pmpParLin (0). The quantity passed as NMIN is the region's in kg,
    which the statements' NMIN / 1000 turn into t."""
    ms = capri_ms(region)
    syn, rev, pmp, oth = [], [], [], []
    for opt, v in sorted((shares or {}).items()):
        if opt == _MANURE_OPTION or not v or float(v) <= 0.0:
            continue
        r_r, r_ms = rows.get((region, opt)), rows.get((ms, opt))
        syn.append((_col(r_r, "costParLin"), _col(r_ms, "costParLin"), _col(r_r, "costParSqr"),
                    _col(r_ms, "costParSqr"), float(v)))
        rev.append((_col(r_r, "revenue"), _col(r_ms, "revenue"), float(v)))
        pmp.append((0.0, 0.0, _col(r_r, "pmpParSqr"), _col(r_ms, "pmpParSqr"), float(v)))
        oth.append((float((nmin_saving or {}).get(opt, 0.0) or 0.0), 0.0, float(v)))
    kg = float(N_mineral_t or 0.0) * 1000.0
    return {"mitiI": p_ghgMiti_emisAll_cost_GainsTechFert(syn, kg, oth, [], 0.0, []) / 1000.0,
            "mitiO": p_ghgMiti_emisAll_revenue_GainsTechFert(rev, kg, oth, [], 0.0, []) / 1000.0,
            "mitiPmp": p_ghgMiti_emisAll_pmpcost_GainsTechFert(pmp, kg, oth, [], 0.0, []) / 1000.0}


def manure_inhibitor_items(region, share, nman_saving, N_manure_t, rows) -> dict:
    """The nitrification inhibitor on manure (CAPRI's NITR_INH_MAN, GainsTechFert on targFertMan, the model's mni
    block) of a region's solution: cost, revenue and PMP cost in EUR 1000 on the manure N applied, CAPRI's per-crop
    statements summed over the crops.

    share: v_miti (SupplyResult.fert_tech_shares["NITR_INH_MAN"]); nman_saving: its othImpact NMAN (the block's nman);
    N_manure_t: the manure N applied at the solution (t; the fertiliser distribution's EXCR flows, CAPRI's crops' NMAN
    x level); rows: as fert_options_items's. The data row is the member state's NITR_INH, as the model's block takes
    it (supply/abatement.py _manure_inhibitor_params; envind/ghgMiti.gms l. 110: the inhibitor's data also for
    N2OMAN)."""
    if not share or float(share) <= 0.0:
        return {"mitiI": 0.0, "mitiO": 0.0, "mitiPmp": 0.0}
    r_ms = rows.get((capri_ms(region), "NITR_INH"))
    v = float(share)
    man = [(0.0, _col(r_ms, "costParLin"), 0.0, _col(r_ms, "costParSqr"), v)]
    rev = [(0.0, _col(r_ms, "revenue"), v)]
    pmp = [(0.0, 0.0, 0.0, _col(r_ms, "pmpParSqr"), v)]
    oth = [(float(nman_saving or 0.0), 0.0, v)]
    kg = float(N_manure_t or 0.0) * 1000.0
    return {"mitiI": p_ghgMiti_emisAll_cost_GainsTechFert([], 0.0, [], man, kg, oth) / 1000.0,
            "mitiO": p_ghgMiti_emisAll_revenue_GainsTechFert([], 0.0, [], rev, kg, oth) / 1000.0,
            "mitiPmp": p_ghgMiti_emisAll_pmpcost_GainsTechFert([], 0.0, [], pmp, kg, oth) / 1000.0}


def ammonia_items(amm_subs, levels) -> dict:
    """The ammonia options and anaerobic digestion on the herds (CAPRI's animal options, the model's amm block) of a
    region's solution: their cost and revenue per head of each model animal and in total (EUR 1000), CAPRI's general
    statements (p_ghgMiti_emisAll_cost, p_ghgMiti_emisAll_revenue) per CAPRI sub-activity at its shares, scaled by its
    places per unit (DAYS / 365), weighted by its share of the animal's units.

    amm_subs: SupplyResult.amm_subs, {(animal, sub-activity): {"w", "stock", "techs": {option: (v_miti, CostParLin,
    CostParSqr, revenue)}}} (the combinations' costs as CAPRI adds them, tools/build/build_ammonia_tech_model.py);
    levels: {animal: level, 1000 heads}. The PMP part is not split out here: the model's table keeps the options'
    calibrated slope (CostParSqr + CAPRI's gamma) and threshold, not pmpParLin and pmpParSqr themselves."""
    cost_h, rev_h = {}, {}
    for (a, _key), d in (amm_subs or {}).items():
        w, stock = float(d["w"]), float(d["stock"])
        c = sum(p_ghgMiti_emisAll_cost([(k1, 0.0, k2, 0.0, v, 1.0)], stock) for v, k1, k2, _r in d["techs"].values())
        r = sum(p_ghgMiti_emisAll_revenue([(rv, 0.0, v)], stock) for v, _k1, _k2, rv in d["techs"].values())
        cost_h[a] = cost_h.get(a, 0.0) + w * c
        rev_h[a] = rev_h.get(a, 0.0) + w * r
    lev = {a: float((levels or {}).get(a, 0.0) or 0.0) for a in cost_h}
    return {"mitiI": sum(cost_h[a] * lev[a] for a in cost_h), "mitiO": sum(rev_h[a] * lev[a] for a in rev_h),
            "mitiI_per_head": cost_h, "mitiO_per_head": rev_h}


def winter_cover_items(cover, row) -> dict:
    """The winter cover (CAPRI's catch crops, CATC with v_Miti(CATC, WinterCov, CO2SEQ), the model's catc block) of a
    region's solution: the catch crops' accounting cost in EUR 1000, costParLin (the CATC activity's input cost per
    ha, tools/build/build_winter_cover_option.py) x the CATC level, and the PMP cost, (pmpParLin v + 0.5 pmpParSqr v^2)
    x UAAR.

    CAPRI books the accounting cost in the CATC activity's own inputs (define_greening_limits.gms) and so leaves CATC
    out of mitiI (reports/sol_simy.gms l. 1455-1461, DATA_mitiI); the model has no CATC activity in its margins, so the
    same inputs enter the income here, under "mitiI" for the catch crops. CAPRI's per-level statement
    (p_ghgMiti_emisAll_cost_catc: the cost per ha of UAAR over v) gives the same cost per ha of CATC, costParLin.
    cover: SupplyResult.cover_crops ({"req": the CATC level, 1000 ha; "uaa"; "share": v}); row: the region's row of
    winter_cover_option.csv."""
    if not cover or row is None or not cover.get("endogenous"):
        return {"mitiI": 0.0, "mitiO": 0.0, "mitiPmp": 0.0}
    v, uaa, catc = float(cover.get("share", 0.0) or 0.0), float(cover.get("uaa", 0.0) or 0.0), \
        float(cover.get("req", 0.0) or 0.0)
    return {"mitiI": _col(row, "cost_lin_eur_ha") * catc,
            "mitiO": 0.0,
            "mitiPmp": (_col(row, "pmp_lin") * v + 0.5 * _col(row, "pmp_sqr") * v * v) * uaa}


def tillage_items(shares, tillage_area, rows) -> dict:
    """The conservation and no tillage options (CAPRI's mitiTechTill on cropMiti, the model's till block) of a
    region's solution, EUR 1000: per option its cost per ha of tillage area at its share (CAPRI's general statement
    with PACT cropMiti, p_ghgMiti_emisAll_cost, scaling 1), which every tillage crop takes per ha
    (p_ghgMiti_emisAll_cost_till), times the tillage area; the PMP cost the same on pmpParLin and pmpParSqr.

    shares: {option: v_miti} (SupplyResult.till_shares); tillage_area: the tillage crops' levels at the solution (1000
    ha; CFACTOR_ARAB, DATA(r, c, TILLSET, Y) = 1); rows: {option: the region's row of tillage_options.csv}. The data
    carry no costParSqr (0)."""
    from capri_mod.coupling.equations.sol_simy import p_ghgMiti_emisAll_pmpcost
    cost = pmp = 0.0
    for opt, v in (shares or {}).items():
        r = (rows or {}).get(opt)
        if r is None or not v:
            continue
        cost += p_ghgMiti_emisAll_cost([(_col(r, "cost_lin_eur_ha"), 0.0, 0.0, 0.0, float(v), 1.0)], 1.0)
        pmp += p_ghgMiti_emisAll_pmpcost([(_col(r, "pmp_lin"), 0.0, _col(r, "pmp_sqr"), 0.0, float(v))], 1.0)
    L = float(tillage_area or 0.0)
    return {"mitiI": cost * L, "mitiO": 0.0, "mitiPmp": pmp * L}


def legume_share_items(share, OFAR_level, row) -> dict:
    """The legume share in temporary grassland (CAPRI's LegSh on OFAR, v_Miti(OFAR, LegSh, BioFix), the model's legsh
    block) of a region's solution, EUR 1000: CAPRI's general statement for OFAR (p_ghgMiti_emisAll_cost, a crop:
    scaling 1) times OFAR's level; the PMP cost on pmpParLin and pmpParSqr. row: the region's row of
    legsh_option.csv (no costParSqr: 0)."""
    from capri_mod.coupling.equations.sol_simy import p_ghgMiti_emisAll_pmpcost
    if row is None or not share:
        return {"mitiI": 0.0, "mitiO": 0.0, "mitiPmp": 0.0}
    v, x = float(share), float(OFAR_level or 0.0)
    return {"mitiI": p_ghgMiti_emisAll_cost([(_col(row, "cost_lin_eur_ha"), 0.0, 0.0, 0.0, v, 1.0)], 1.0) * x,
            "mitiO": 0.0,
            "mitiPmp": p_ghgMiti_emisAll_pmpcost([(_col(row, "pmp_lin"), 0.0, _col(row, "pmp_sqr"), 0.0, v)], 1.0) * x}


def urea_substitution_items(share, N_bought_t, crop_levels, row, form="supply_model") -> dict:
    """The urea substitution (CAPRI's UreaSubst on cropMiti, the model's urea block) of a region's solution, EUR 1000.

    form "supply_model" (the default; register FIX-10): the cost per t of N bought at the share, times the N bought,
    the base CAPRI's supply model charges it on (GHG_Mit_Cost_'s UreaSubst base, supply/supply_model.gms l. 5063,
    -v_netPutQuant(NITF); equations/supply_model/mitigation.py GHG_Mit_Cost_ureaSubst). form "capri": CAPRI's report as
    coded (reports/sol_simy.gms l. 1129-1132, p_ghgMiti_emisAll_cost_UreaSubst): the same per-t parameter at the share
    as a cost per unit of every crop mapped to the option, times the crops' levels, which mixes a cost per t of N with
    a cost per ha. The PMP cost the same way on pmpParLin and pmpParSqr.

    share: v_miti (SupplyResult.urea_share); N_bought_t: the mineral N bought (t); crop_levels: {crop: 1000 ha} of the
    crops the option maps to (the caller's: those with mineral N); row: the member state's row of
    urea_subst_option.csv (cost_lin_eur_t; no costParSqr: 0)."""
    from capri_mod.coupling.equations.sol_simy import p_ghgMiti_emisAll_cost_UreaSubst, \
        p_ghgMiti_emisAll_pmpcost_UreaSubst
    if row is None or not share:
        return {"mitiI": 0.0, "mitiO": 0.0, "mitiPmp": 0.0}
    v = float(share)
    c = p_ghgMiti_emisAll_cost_UreaSubst([(_col(row, "cost_lin_eur_t"), 0.0, v)])
    p = p_ghgMiti_emisAll_pmpcost_UreaSubst([(_col(row, "pmp_lin"), _col(row, "pmp_sqr"), v)])
    if form == "capri":
        q = sum(float(x or 0.0) for x in (crop_levels or {}).values())
    elif form == "supply_model":
        q = float(N_bought_t or 0.0) / 1000.0
    else:
        raise ValueError(f"income.urea_cost_base: {form!r} is neither \"supply_model\" nor \"capri\"")
    return {"mitiI": c * q, "mitiO": 0.0, "mitiPmp": p * q}


def histosol_fallow_items(fallow) -> dict:
    """The histosols' fallowing (CAPRI's FALLOW on idlHisAct with rewetting, QEmitt 0; the model's histosol columns)
    of a region's solution: its accounting cost in EUR 1000, costParLin x the area idled (CAPRI's general statement,
    p_ghgMiti_emisAll_cost: the cost per ha of organic soil at v_miti, which its per-level form,
    p_ghgMiti_emisAll_cost_idlHis, turns into the cost per ha idled). costParLin is CAPRI's 216 EUR/ha
    (envind/no_histosols.gms l. 121-131; model_parameters.csv HISTOSOL_FALLOW_COST), inflated in CAPRI to the
    simulation year's money, the base year's in the model's. The PMP cost is not split out here (the model's columns
    keep CAPRI's curvature and a linear term from the base land dual, supply/abatement.py _histosol_columns).

    fallow: SupplyResult.histosol_fallow, {class: 1000 ha idled}."""
    from capri_mod.params import param
    area = sum(float(v or 0.0) for v in (fallow or {}).values())
    return {"mitiI": float(param("HISTOSOL_FALLOW_COST")) * area, "mitiO": 0.0}



def herd_option_items(shift, effects) -> dict:
    """The herd options (CAPRI's breeding options genet_yld and genet_eff, its low-N feeding lowNFeed and the feed
    additives LINE_Tot, Nitr_Tot, 3NOP_Tot; the model's genetics columns, 1000 heads adopting) of a region's solution:
    their accounting cost in EUR 1000 by CAPRI's general statement (p_ghgMiti_emisAll_cost: costParLin x v_miti x the
    scaling, x the activity's level: the cost per head adopting x the heads adopting).

    shift: {(animal, option): 1000 heads adopting} (SupplyResult.genetics_shift); effects: {(animal, option): row}
    of the region's genetics, low-N feed and supplement tables as the run scales them (capri_mod/policy/endotech.py
    cost_eur_head). The cost per head carries CAPRI's scaling already: the breeding options' costs per place times
    the places per head (tools/build/build_genetics_effects.py per_head), the low-N feed's the feed cost per head
    times CAPRI's factor (CAPRI's feed cost per place x DAYS / 365, low_n_feed.gms l. 129-142;
    build_lownfeed_effects.py), the feed additives' the fat fed (DRMA x days / 1000 x ShrOfDM,
    build_supplement_effects.py), so no further days. Revenue: none in CAPRI's data for these options (the extra milk
    of genet_yld is the activity's output, not mitiO)."""
    cost, by_a = 0.0, {}
    for (a, opt), g in (shift or {}).items():
        e = (effects or {}).get((a, opt))
        if e is None or not g:
            continue
        v = float(e.get("cost_eur_head", 0.0) or 0.0) * float(g)
        by_a[a] = by_a.get(a, 0.0) + v
        cost += v
    return {"mitiI": cost, "mitiO": 0.0, "mitiI_by_animal": by_a}
