r"""CAPRI's rural development declarations (policy/rd_logic.gms, star 3.0): the RD money summed up to the NUTS 1 regions
and member states, the land partition's shares under the policy areas, FADN's agri-environment data completed, the
schemes' ceilings from the year's programme and their split by farm type, the rates of the less-favoured-area,
Natura 2000 and agri-environment payments, the heavy animals' entitlement weights, and the rates scaled to pay 1.5
times the ceiling at the levels.

capri_mod/policy/rd.py (rd_declarations) loops over the regions, schemes, farm types and years and calls these; the
region sets (l. 50-61), the application types (perLevl), the default agri-environment rate (l. 258-260), the copies
(the livestock units as weights, l. 232 and 292-294; Luxembourg's FADN as BL400000's, l. 119) and Sweden's expert
data (l. 351-406: constants and a copy) stay in the caller's loops. Not ported: the technology factors (l. 237-244,
330-334, 392-393: capri_mod/supply/techn_mix.py's prem_diff_share), the debug output and article 68's 2010 payments
(l. 413-425, schemes dp68*, not RD). GAMS's EPS arithmetic: capri_mod/policy/equations/extend_rd_baseline.py.
"""
from __future__ import annotations

from capri_mod.policy.equations._gams import EPS
from capri_mod.policy.equations.extend_rd_baseline import _gsum, _nz


def _mul(x, f):
    """GAMS's product with a value that may be EPS (EPS times a number stays EPS)."""
    if x == EPS:
        return EPS
    return x * f


def p_rdBudget_SRNUTS1(own, srnuts2):
    r"""p_rdBudget(SRNUTS1, rdYear, rdMeasure, rdSpender, rdPlanSpend) of a NUTS 1 region run without its own: the sum of
    its NUTS 2 regions' run (GAMS's sum with EPS terms); None where it has its own or the sum is empty.

    CAPRI's GAMS (policy/rd_logic.gms l. 66-68):

        p_rdBudget(SRNUTS1,rdYear,rdMeasure,rdSpender,rdPlanSpend)
           $ (runr(SRNUTS1) $ (NOT p_rdBudget(SRNUTS1,rdYear,rdMeasure,rdSpender,rdPlanSpend)))
             = SUM(MAP_RR(SRNUTS1,SRNUTS2) $ RUNR(SRNUTS2), p_rdBudget(SRNUTS2,rdYear,rdMeasure,rdSpender,rdPlanSpend));

    Departures from CAPRI: the total public money only (extend_rd_baseline.py)."""
    if _nz(own):
        return None
    return _gsum(srnuts2)


def p_rdBudget_MS(own, srnuts1):
    r"""p_rdBudget(MS, rdYear, rdMeasure, rdSpender, rdPlanSpend) of a member state run without its own: the sum of its
    NUTS 1 regions' run (after p_rdBudget_SRNUTS1); None where it has its own or the sum is empty.

    CAPRI's GAMS (policy/rd_logic.gms l. 73-75):

        p_rdBudget(MS,rdYear,rdMeasure,rdSpender,rdPlanSpend)
           $ (runr(MS) $ (NOT p_rdBudget(MS,rdYear,rdMeasure,rdSpender,rdPlanSpend)))
             = SUM(MAP_RR(MS,SRNUTS1) $ RUNR(SRNUTS1), p_rdBudget(SRNUTS1,rdYear,rdMeasure,rdSpender,rdPlanSpend));

    Departures from CAPRI: the total public money only."""
    if _nz(own):
        return None
    return _gsum(srnuts1)


def p_landPartition_SRNUTS1(srnuts2):
    r"""p_landPartition(srnuts1, lcAgri, lcPolT) of a NUTS 1 region run: its NUTS 2 regions' areas summed (1000 ha; the
    caller drops a zero).

    CAPRI's GAMS (policy/rd_logic.gms l. 96-97):

        p_landPartition(srnuts1,lcAgri,lcPolT) $ runr(srnuts1)
            = SUM(map_rr(srnuts1,srnuts2),p_landPartition(srnuts2,lcAgri,lcPolT));

    Departures from CAPRI: none."""
    return sum(srnuts2)


def DATA_LEVL_nuts1a(srnuts2):
    r"""DATA(nuts1a, MPACT, "LEVL", "Y") of a NUTS 1 region run: its NUTS 2 regions' levels summed (the caller drops a
    zero).

    CAPRI's GAMS (policy/rd_logic.gms l. 99-100):

        DATA(nuts1a,MPACT,"LEVL","Y") $ runr(nuts1a)
            = SUM(map_rr(nuts1a,srnuts2),DATA(srnuts2,MPACT,"LEVL","Y"));

    Departures from CAPRI: a member state without levels at the call takes its NUTS 2 regions' sum too (CAPRI's DATA
    holds the member states' own); the regions' types (l. 88-92) not ported (no farm types)."""
    return sum(srnuts2)


def p_landPartition_MS(srnuts2):
    r"""p_landPartition(ms, lcAgri, lcPolT) of a member state with RD money: its NUTS 2 regions' areas summed (the caller
    drops a zero).

    CAPRI's GAMS (policy/rd_logic.gms l. 103-104):

        p_landPartition(ms,lcAgri,lcPolT) $ rdMS(ms)
            = SUM(map_rr(ms,srnuts2),p_landPartition(srnuts2,lcAgri,lcPolT));

    Departures from CAPRI: none."""
    return sum(srnuts2)


def p_landPartition_share(area, total):
    r"""p_landPartition(runr, lcAgri, lcPol): a policy area's share of the land cover (LFA, N2K, ...); None where the land
    cover has no total.

    CAPRI's GAMS (policy/rd_logic.gms l. 108-109):

        p_landPartition(runr,lcAgri,lcPol) $ p_landPartition(runr,lcAgri,"Total")
            = p_landPartition(runr,lcAgri,lcPol)/p_landPartition(runr,lcAgri,"Total");

    Departures from CAPRI: the shares kept apart from the areas (CAPRI overwrites the areas)."""
    if not total:
        return None
    return area / total


def p_fadn_BL000000(BE, LU):
    r"""p_fadn("BL000000", tf8, fadn_lfa, fadn_ae, fadn_unit): Belgium's and Luxembourg's FADN data summed.

    CAPRI's GAMS (policy/rd_logic.gms l. 117-118):

         p_fadn("BL000000",tf8,fadn_lfa,fadn_ae,fadn_unit) = p_fadn("BE000000",tf8,fadn_lfa,fadn_ae,fadn_unit)
                                                           + p_fadn("LU000000",tf8,fadn_lfa,fadn_ae,fadn_unit);

    Departures from CAPRI: none (the data has no BL000000 of its own)."""
    return BE + LU


def p_fadn_Total(tf8):
    r"""p_fadn(rs, "Total", fadn_lfa, fadn_ae, fadn_unit): the farm types' FADN data summed (the caller drops a zero).

    CAPRI's GAMS (policy/rd_logic.gms l. 121-122):

         p_fadn(rs,"Total",fadn_lfa,fadn_ae,fadn_unit)
           = SUM(tf8 $ (NOT sameas(tf8,"Total")), p_fadn(rs,tf8,fadn_lfa,fadn_ae,fadn_unit));

    Departures from CAPRI: none."""
    return sum(tf8)


def p_fadn_Tot(LFA, NoLFA):
    r"""p_fadn(rs, tf8, "Tot", fadn_ae, fadn_unit): the FADN data in and out of LFA summed (the caller drops a zero).

    CAPRI's GAMS (policy/rd_logic.gms l. 124):

         p_fadn(rs,tf8,"Tot",fadn_ae,fadn_unit) = SUM(fadn_lfa, p_fadn(rs,tf8,fadn_lfa,fadn_ae,fadn_unit));

    Departures from CAPRI: none."""
    return LFA + NoLFA


def p_premDataE_ceilval(spend_plan):
    r"""p_premDataE(runr, rdYear, psdpay_rd, "ceilval"): the scheme's ceiling of the year (million EUR), the public money
    of its measures in the year's programme: each measure's spend, its plan where nothing is spent, plus EPS (so that
    a region without money keeps an EPS ceiling, and a higher level's declaration does not reach it). spend_plan the
    (spend, plan) pairs of the scheme's measures in the year's programmes; None where it has none.

    CAPRI's GAMS (policy/rd_logic.gms l. 139-147):

         p_premDataE(runr,rdYear,psdpay_rd,"ceilval")
            = SUM((RDP,rdMeasure) $ (RDP_SIMYY(RDP,rdYear) AND psDpay_RDP_rdMeasure(psdpay_rd,RDP,rdMeasure)),
                    p_rdBudget(runr,rdYear,rdMeasure,"rdSpendPublic","spend")
                  + p_rdBudget(runr,rdYear,rdMeasure,"rdSpendPublic","plan") $ [NOT p_rdBudget(runr,rdYear,rdMeasure,"rdSpendPublic","spend")]
                  + EPS
              );

    Departures from CAPRI: none."""
    terms = []
    for sp, pl in spend_plan:
        terms.append(sp if _nz(sp) else pl)
        terms.append(EPS)
    return _gsum(terms)


def _share_of(ceil, part, whole):
    """The ceiling times part / whole; None where the share is zero (the record gone)."""
    f = part / whole
    return _mul(ceil, f) if f else None


def p_premDataE_ceilval_ae_fadn(ceil, eur, eur_Total):
    r"""p_premDataE(runr, rdYear, psdpay_ae, "ceilval") split by farm type: the agri-environment ceiling (every AE scheme
    got the whole AE money) times the scheme's farm types' share of the member state's agri-environment euros in FADN
    (eur, eur_Total of p_fadn(ms, tf8, "Tot", "AE", "EUR")); None where the share is zero.

    CAPRI's GAMS (policy/rd_logic.gms l. 155-159):

         loop((ms,runr,psdpay_ae,tf8) $ (map_rr(ms,runr) $ dpae_tf8(psdpay_ae,tf8)),
            p_premDataE(runr,rdYear,psdpay_ae,"ceilval") $ p_fadn(ms,"Total","Tot","AE","EUR")
                = p_premDataE(runr,rdYear,psdpay_ae,"ceilval") * p_fadn(ms,tf8,"Tot","AE","EUR")
                                                            / p_fadn(ms,"Total","Tot","AE","EUR");
         );

    Departures from CAPRI: the farm types' euros summed (CAPRI multiplies by each type's share in turn; one farm type
    per scheme in the data, rd_sets.csv's dpae_tf8: the same)."""
    return _share_of(ceil, eur, eur_Total)


def p_premDataE_ceilval_ae_area(ceil, ha, ha_Total):
    r"""p_premDataE(runr, rdYear, psdpay_ae, "ceilval") of a member state without FADN agri-environment euros: the ceiling
    times the scheme's farm types' share of FADN's hectares outside LFA without agri-environment (ha; ha_Total over the
    farm types but the total); None where the share is zero.

    CAPRI's GAMS (policy/rd_logic.gms l. 166-172):

         LOOP(MS $ ((sum( tf8, p_fadn(ms,tf8,"Tot","AE","EUR")) eq 0) $ rdMS(MS)),

            p_premDataE(runr,rdYear,psdpay_ae,"ceilval") $ (sum(tf8,p_fadn(ms,tf8,"noLFA","NoAE","Ha")) $ map_rr(ms,runr))
               = p_premDataE(runr,rdYear,psdpay_ae,"ceilval")
                   * sum(dpae_tf8(psdpay_ae,tf8), p_fadn(ms,tf8,"noLFA","noAE","HA"))
                                       / sum(tf8 $ (NOT sameas(tf8,"total")), p_fadn(ms,tf8,"noLFA","noAE","HA"));
         );

    Departures from CAPRI: none."""
    return _share_of(ceil, ha, ha_Total)


def p_premDataE_ceilval_ae_levels(ceil, levl, levl_Total):
    r"""p_premDataE(runr, rdYear, psdpay_ae, "ceilval") of a member state without FADN euros or hectares: the ceiling times
    the scheme's farm types' share of the region's crop levels (levl; levl_Total over every farm type's premium groups);
    None where the share is zero.

    CAPRI's GAMS (policy/rd_logic.gms l. 178-186):

         LOOP(MS $ ((sum( tf8, (p_fadn(ms,tf8,"Tot","AE","EUR")+p_fadn(ms,tf8,"noLFA","noAE","HA"))) eq 0) $ rdMS(MS)),

            p_premDataE(runr,rdYear,psdpay_ae,"ceilval")
                   $  (SUM((psgroup,MCACT,tf8_copy) $ (psgroup_tf8(psgroup,tf8_copy) $ psg_to_a(psGroup,mcact)), DATA(runr,Mcact,"Levl","Y")) $ map_rr(ms,runr))

               = p_premDataE(runr,rdYear,psdpay_ae,"ceilval")
                  *   SUM((psgroup,MCACT,dpae_tf8(psdpay_ae,tf8))   $ (psgroup_tf8(psgroup,tf8)      $ psg_to_a(psGroup,mcact)), DATA(runr,Mcact,"Levl","Y"))
                   /  SUM((psgroup,MCACT,tf8_copy)                  $ (psgroup_tf8(psgroup,tf8_copy) $ psg_to_a(psGroup,mcact)), DATA(runr,Mcact,"Levl","Y"));
        );

    Departures from CAPRI: none."""
    return _share_of(ceil, levl, levl_Total)


def p_premDataE_DPRD_LFA(rdMax_LFA, share_LFA):
    r"""p_premDataE(runr, rdyear, "DPRD_LFA", lcAgri) of a region with an LFA ceiling: the LFA payment's maximum (EUR per
    ha) times the land cover's LFA share; None where it is zero.

    CAPRI's GAMS (policy/rd_logic.gms l. 208-209):

         p_premDataE(runr,rdyear,"DPRD_LFA",lcAgri) $ p_premDataE(runr,rdyear,"DPRD_LFA","ceilVal")
             = p_rdMax("LFA") * p_LandPartition(runr,lcAgri,"LFA");

    Departures from CAPRI: none."""
    v = rdMax_LFA * share_LFA
    return v if v else None


def p_premDataE_DPRD_N2K(rdMax_N2K, share_N2K):
    r"""p_premDataE(runr, rdyear, "DPRD_N2K", lcAgri) of a region with a Natura 2000 ceiling, the land covers but
    grassland: the payment's maximum times the land cover's N2K share; None where it is zero.

    CAPRI's GAMS (policy/rd_logic.gms l. 225-227):

         p_premDataE(runr,rdyear,"DPRD_N2K",lcAgri) $ (p_premDataE(runr,rdyear,"DPRD_N2K","ceilVal")
                                                $ (NOT SAMEAS(lcAgri,"PGGRAS")))
            = p_rdMax("N2K") * p_LandPartition(runr,lcAgri,"N2K");

    Departures from CAPRI: none."""
    v = rdMax_N2K * share_N2K
    return v if v else None


def p_premDataE_DPRD_N2K_PGGRZE(rdMax_N2K, share_N2K_PGGRAS):
    r"""p_premDataE(runr, rdyear, "DPRD_N2K", "PGGRZE"): grassland's Natura 2000 payment to the grazing animals, the
    maximum times grassland's N2K share; None where it is zero.

    CAPRI's GAMS (policy/rd_logic.gms l. 229-230):

         p_premDataE(runr,rdyear,"DPRD_N2K","PGGRZE") $ p_premDataE(runr,rdyear,"DPRD_N2K","ceilVal")
            = p_rdMax("N2K") * p_LandPartition(runr,"PGGRAS","N2K");

    Departures from CAPRI: none."""
    v = rdMax_N2K * share_N2K_PGGRAS
    return v if v else None


def p_aeLfa(eur_AE, ha_AE, ha_NoAE):
    r"""p_aeLfa(ms, tf8, fadn_lfa): the expected agri-environment payment per ha of a farm type in or out of LFA, FADN's
    agri-environment euros over the hectares with and without; None where there are no hectares or no euros.

    CAPRI's GAMS (policy/rd_logic.gms l. 255-256):

         p_aeLfa(ms,tf8,fadn_lfa) $ SUM(fadn_AE, p_fadn(ms,tf8,fadn_lfa,fadn_AE,"Ha"))
            = p_fadn(ms,tf8,fadn_lfa,"AE","EUR") / SUM(fadn_AE, p_fadn(ms,tf8,fadn_lfa,fadn_AE,"Ha"));

    Departures from CAPRI: the caller computes it for "Tot" too (not used by the rates)."""
    ha = ha_AE + ha_NoAE
    if not ha:
        return None
    v = eur_AE / ha
    return v if v else None


def p_premDataE_ae(shares_LFA, aeLfa_LFA, aeLfa_NoLFA):
    r"""p_premDataE(runr, rdYear, psdpay_ae, psgroup) of a farm type's premium groups: over the farm type's land covers,
    the LFA share times the expected payment in LFA plus the rest times the one outside (shares_LFA the land covers'
    LFA shares in tf8_lc's order), at most 2000 EUR per ha.

    CAPRI's GAMS (policy/rd_logic.gms l. 267-273):

            p_premDataE(runr,rdYear,psdpay_ae,psgroup) $ (p_premDataE(runr,rdyear,psdpay_ae,"ceilVal")
                                                     $ map_rr(ms,runr) $ psgroup_tf8(psgroup,tf8))

                = min(2000,

                    SUM(tf8_lc(tf8,lcAgri),      p_LandPartition(runr,lcAgri,"LFA")  * p_aeLfa(ms,tf8,"LFA")
                                          + (1 - p_LandPartition(runr,lcAgri,"LFA")) * p_aeLfa(ms,tf8,"NoLFA")));

    Departures from CAPRI: none."""
    return min(2000.0, sum(s * aeLfa_LFA + (1 - s) * aeLfa_NoLFA for s in shares_LFA))


def p_entlWght1_heavy(w):
    r"""p_entlWght1(runr, "DCOH" | "BULH" | "HEIH", psdpay_ae): the heavy dairy cows', bulls' and heifers' agri-environment
    entitlement weight halved (extensification; EPS stays EPS).

    CAPRI's GAMS (policy/rd_logic.gms l. 298-305):

         p_entlWght1(runr,"DCOH",psdpay_ae) $ p_entlWght1(runr,"DCOH",psdpay_ae)
            = 0.50*p_entlWght1(runr,"DCOH",psdpay_ae);

         p_entlWght1(runr,"BULH",psdpay_ae) $ p_entlWght1(runr,"BULH",psdpay_ae)
            = 0.50*p_entlWght1(runr,"BULH",psdpay_ae);

         p_entlWght1(runr,"HEIH",psdpay_ae) $ p_entlWght1(runr,"HEIH",psdpay_ae)
            = 0.50*p_entlWght1(runr,"HEIH",psdpay_ae);

    Departures from CAPRI: none."""
    return _mul(w, 0.5)


def p_scaleRdPpePay_sum(terms):
    r"""p_scaleRdPpePay(RUNR, rdYear, psdpay_rd) before its division: the scheme's payment at the levels (million EUR),
    over its groups with a rate and their activities with a level, the level times the entitlement weight (1 where
    there is none, 0 for EPS) times the rate (0 for EPS) / 1000. terms the (level, weight, rate) triples in that
    order, the levels nonzero.

    CAPRI's GAMS (policy/rd_logic.gms l. 309-313):

         p_scaleRdPpePay(RUNR,rdYear,psdpay_rd) $ p_premDataE(runr,rdYear,psdpay_rd,"ceilval")
            = sum( PSG_TO_A(PSGROUP,MPACT) $ p_premDataE(runr,rdYear,psdpay_rd,psgroup),
                      DATA(runr,mpact,"LEVL","Y")
                         * ( 1. $ (NOT p_entlWght1(runr,mPact,psdpay_rd) ) + p_entlWght1(runr,mPact,psdpay_rd))
                              * p_premDataE(runr,rdYear,psdpay_rd,psgroup)*0.001);

    Departures from CAPRI: none."""
    tot = 0.0
    for lv, w, v in terms:
        tot += lv * (1.0 if not _nz(w) else (0.0 if w == EPS else w)) * (0.0 if v == EPS else v) * 0.001
    return tot


def p_scaleRdPpePay(ceil, tot):
    r"""p_scaleRdPpePay(RUNR, rdYear, psdpay_rd): the factor that makes the scheme's rates pay its ceiling at the levels,
    the ceiling over the payment (p_scaleRdPpePay_sum; EPS for an EPS ceiling); 0 where the payment is not above 0.

    CAPRI's GAMS (policy/rd_logic.gms l. 315-316):

         p_scaleRdPpePay(RUNR,rdYear,psdpay_rd) $ [p_scaleRdPpePay(RUNR,rdYear,psdpay_rd) GT EPS]
           =  p_premDataE(runr,rdYear,psdpay_rd,"ceilval")/p_scaleRdPpePay(RUNR,rdYear,psdpay_rd);

    Departures from CAPRI: 0 where the payment is not above 0 (CAPRI keeps the sum, which is then 0)."""
    if not tot > 0:
        return 0.0
    return EPS if ceil == EPS else ceil / tot


def p_premDataE_scaled(v, f):
    r"""p_premDataE(runr, rdYear, psdpay_rd, psgroup): the rate times the factor (p_scaleRdPpePay) times 1.5, at most 2000
    EUR per ha (prmcut.gms then cuts the payments to the ceiling); EPS where the rate or the factor is EPS and the other
    nonzero, None where the product is zero (the record gone).

    CAPRI's GAMS (policy/rd_logic.gms l. 318-319):

         p_premDataE(runr,rdYear,psdpay_rd,psgroup)
           = MIN(2000,p_premDataE(runr,rdYear,psdpay_rd,psgroup) * p_scaleRdPpePay(RUNR,rdYear,psdpay_rd) * 1.5);

    Departures from CAPRI: none."""
    x = EPS if (f == EPS and _nz(v)) or (v == EPS and f) else ((v * f) if f else 0.0)
    if x == EPS:
        return EPS
    if x:
        return min(2000.0, x * 1.5)
    return None
