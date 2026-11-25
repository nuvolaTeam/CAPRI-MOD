"""CAPRI's digestibility and methane per head (capri_mod/supply/equations/digestibility.py, envind/digestibility.gms
l. 64-253; capri_mod/environmental/equations/gases.py, envind/gases.gms l. 317-443) on small cases worked by hand."""
from __future__ import annotations

import math

import pytest

from capri_mod.environmental.equations import gases as g
from capri_mod.supply.equations import digestibility as dg

#: CAPRI's table row of soft wheat (envind/def_digestibility.gms l. 62, NRC 2001)
SWHE = dict(PAF=1.04, DM=89.4, CP=14.2, NDICP=1.7, ADICP=0.2, EE=2.3, NDF=13.4, ADF=4.4, LI=1.7, ASH=2.0, CAT=1)


def test_wheat_through_the_nrc_chain():
    """l. 60, 99-136 on soft wheat: FAT = EE - 1, TDNFC, TDCP of a concentrate, TDNDF, TDN, DE and GE at maintenance."""
    r = SWHE
    fat = dg.p_digestPar_FAT(r["EE"], 0.0)
    assert fat == pytest.approx(1.3)
    ndf = dg.p_digestPar_NDF_min(r["NDF"], r["NDICP"], r["CAT"])
    assert ndf == 13.4
    tdnfc = dg.p_digestPar_TDNFC(ndf, r["NDICP"], r["CP"], r["EE"], r["ASH"], r["PAF"], r["CAT"])
    assert tdnfc == pytest.approx(0.98 * (100 - 13.4 + 1.7 - 14.2 - 2.3 - 2.0) * 1.04, rel=1e-14)
    tdcp = dg.p_digestPar_TDCP(r["CP"], r["ADICP"], r["CAT"])
    assert tdcp == pytest.approx((1 - 0.4 * 0.2 / 14.2) * 14.2, rel=1e-14)
    tdfa = dg.p_digestPar_TDFA(fat)
    tdndf = dg.p_digestPar_TDNDF(ndf, r["NDICP"], r["LI"], r["CAT"])
    assert tdndf == pytest.approx(0.75 * (13.4 - 1.7 - 1.7) * (1 - (1.7 / 11.7) ** 0.667), rel=1e-14)
    tdn = dg.p_digestPar_TDN(tdnfc, tdcp, tdfa, tdndf, r["CAT"])
    assert tdn == pytest.approx(tdnfc + tdcp + 1.3 * 2.25 + tdndf - 7, rel=1e-14)
    de = dg.p_digestPar_DE_maintenance(tdnfc, tdndf, tdcp, tdfa, r["CAT"])
    assert de == pytest.approx((tdnfc + tdndf) / 100 * 4.2 + tdcp / 100 * 5.6 + 1.3 / 100 * 9.4 - 0.3, rel=1e-14)
    assert 3.7 < de < 3.95           # NRC 2001's wheat grain is about 3.8 Mcal DE per kg DM at maintenance
    ge = dg.p_digestPar_GE(r["CP"], fat, r["ASH"], r["CAT"])
    assert ge == pytest.approx(14.2 / 100 * 5.6 + 1.3 / 100 * 9.4 + (100 - 14.2 - 1.3 - 2.0) / 100 * 4.2, rel=1e-14)


def test_the_classes_and_the_oils():
    """l. 108-115: a forage's digestible protein with the exponential, an animal product's the whole CP; no class, no
    value; l. 131-132: an animal product's DE without the fibre; l. 138-143: the oils' INRA values."""
    assert dg.p_digestPar_TDCP(16.8, 1.1, 2) == pytest.approx(16.8 * math.exp(-1.2 * 1.1 / 16.8), rel=1e-14)
    assert dg.p_digestPar_TDCP(34.1, 0.0, 3) == 34.1
    assert dg.p_digestPar_TDCP(10.0, 0.5, 0) == 0.0
    assert dg.p_digestPar_DE_maintenance(50.0, 20.0, 30.0, 1.0, 3) == pytest.approx(0.5 * 4.2 + 0.3 * 5.6 + 0.094 - 0.3)
    assert dg.p_digestPar_DE_maintenance(50.0, 20.0, 30.0, 1.0, 0) == 0.0
    assert dg.p_digestPar_DE_GE_oils("RAPO", 1.0, 2.0) == (8.27, 9.39)
    assert dg.p_digestPar_DE_GE_oils("SWHE", 1.0, 2.0) == (1.0, 2.0)


def test_capris_contents_are_kept_only_both_within_bounds():
    """l. 73-83 in order: a fibre out of bounds goes, and the crude protein goes with it as the second statement reads
    the fibre at 0; both within bounds, both kept and used (l. 86-94) where the shares add to at most 100."""
    F, C = dg.p_nutPerDryMt_bounds(FIDI=40.0, CRPR=14.0, NDF=13.4, CP=14.2)
    assert (F, C) == (0.0, 0.0)
    F, C = dg.p_nutPerDryMt_bounds(FIDI=14.0, CRPR=15.0, NDF=13.4, CP=14.2)
    assert (F, C) == (14.0, 15.0)
    assert dg.p_digestPar_CP(14.2, C, F, 1.3, 2.0, 1.7) == 15.0
    assert dg.p_digestPar_NDF_data(13.4, C, F, 1.3, 2.0, 1.7) == 14.0
    # a product without CAPRI's fibre loses its crude protein too where the table's NDF is above 5
    assert dg.p_nutPerDryMt_bounds(FIDI=0.0, CRPR=14.0, NDF=13.4, CP=14.2) == (0.0, 0.0)
    assert dg.p_nutPerDryMt(DATA_item=0.12, DM=0.894) == pytest.approx(0.12 / 0.894 * 100)
    assert dg.p_nutPerDryMt(DATA_item=0.12, DM=0.0) == 0.0


def test_the_intake_discount():
    """l. 150-170: the intake above maintenance sums the technologies' ratios; the discount for TDN above 60, 1 at or
    below 60, and at most down to a TDN of 60."""
    ai = dg.p_actualIntake({"T": 300.0, "T1": 200.0}, {"T": 100.0, "T1": 100.0}, {"T": 0.6, "T1": 0.4})
    assert ai == pytest.approx(3.0 + 2.0 - 1)
    assert dg.p_actualIntake({"T": 300.0}, {"T": 0.0}, {"T": 1.0}) == 0.0
    dis = dg.p_digestPar_DIS(86.6, 1, 1.5)
    assert dis == pytest.approx((86.6 - (0.18 * 86.6 - 10.3) * 1.5) / 86.6, rel=1e-14)
    assert dg.p_digestPar_DIS(55.0, 2, 1.5) == 1.0
    assert dg.p_digestPar_DIS(70.0, 1, 10.0) == pytest.approx(60 / 70)          # 70 - 2.3 x 10 = 47 < 60
    assert dg.p_digestPar_DIS(86.6, 1, 0.0) == 0.0
    assert dg.p_digestPar_DE_intake(3.8, dis) == pytest.approx(3.8 * dis)
    assert dg.p_digestPar_DE_intake(3.8, 0.0) == 3.8


def test_the_rations_digestibility_ash_and_gross_energy():
    """l. 241-253: weighted by the ration's dry matter, DE as DE/GE in percent and at least 50; a feed without GE does
    not count in DE and GE but its dry matter does in the denominator."""
    ration = {"FGRA": 10000.0, "FCER": 1000.0, "FOTH": 50.0}
    DM = {"FGRA": 0.2, "FCER": 0.88, "FOTH": 0.9}
    DE = {"FGRA": 2.6, "FCER": 3.6}
    GE = {"FGRA": 4.4, "FCER": 4.3}
    ASH = {"FGRA": 9.0, "FCER": 2.0, "FOTH": 5.0}
    de, ash, ge = dg.EMISCALC_DE_ASH_GE(ration, DM, DE, GE, ASH)
    w = {"FGRA": 2000.0, "FCER": 880.0, "FOTH": 45.0}
    tot = sum(w.values())
    assert de == pytest.approx((2.6 / 4.4 * 2000 + 3.6 / 4.3 * 880) / tot * 100, rel=1e-14)
    assert ash == pytest.approx((9 * 2000 + 2 * 880 + 5 * 45) / tot, rel=1e-14)
    assert ge == pytest.approx((4.4 * 2000 + 4.3 * 880) / tot, rel=1e-14)
    de_low, _, _ = dg.EMISCALC_DE_ASH_GE({"FSTR": 1.0}, {"FSTR": 0.9}, {"FSTR": 1.0}, {"FSTR": 4.0}, {})
    assert de_low == 50.0
    assert dg.EMISCALC_DE_ASH_GE({}, DM, DE, GE, ASH) == (0.0, 0.0, 0.0)


def test_enteric_methane_tier_2_and_tier_1():
    """l. 317-359: NEG and GENE from DE, the gross energy intake from the net energy parts, CH4ENT = YM x GE intake x
    days / 55.65 with the EU's YM where the region has none; l. 384-386: tier 1 only where tier 2 gave none."""
    de = 70.0
    neg = g.EMISCALC_NEG(de)
    gene = g.EMISCALC_GENE(de)
    assert neg == pytest.approx(1.164 - 0.001 * 5.16 * 70 + 1.308e-5 * 4900 - 37.4 / 70, rel=1e-14)
    assert gene == pytest.approx(1.123 - 0.001 * 4.092 * 70 + 1.126e-5 * 4900 - 25.4 / 70, rel=1e-14)
    assert g.EMISCALC_NEG(0.0) == 0.0
    sub = {"NEM": 60.0, "NEL": 90.0, "NEG": 10.0}
    ge_req = g.p_animReq_GENE(sub, neg, 0.0, gene, 0.0, de, 0.0)
    assert ge_req == pytest.approx((60 / gene + 90 / gene + 10 / neg) / 0.7, rel=1e-14)
    assert g.p_animReq_GENE(sub, 0.0, neg, gene, 0.0, 0.0, de) == pytest.approx(ge_req, rel=1e-14)
    ch4 = g.EMISCALC_CH4ENT_tier2(0.0, 6.5, ge_req, 365.0)
    assert ch4 == pytest.approx(6.5 * ge_req * 365 / 55.65, rel=1e-14)
    assert g.EMISCALC_CH4ENT_tier1(ch4, 1.5, 0.0, 365.0, True) == ch4
    assert g.EMISCALC_CH4ENT_tier1(0.0, 0.0, 1.5, 180.0, True) == pytest.approx(1.5 / 365 * 180)
    assert g.EMISCALC_CH4ENT_tier1(0.0, 1.5, 0.0, 180.0, False) == 0.0


def test_manure_methane_tier_2_tier_1_and_the_ammonia_techniques():
    """l. 405-443: the volatile solids (18.45 MJ per kg where the ration has no GE), CH4MAN = VSER x B0 x 0.67 x MCFMS x
    days; tier 1 by the climate shares (the member state's where the region has none, the EU group's factor where the
    member state has none); the factor of the ammonia techniques with %ghgAbatement% off."""
    vs = g.EMISCALC_VSER(300.0, 4.4, 70.0, 0.0, 8.0, 0.0)
    assert vs == pytest.approx(300 / (4.4 * 4.184) * (1 - 0.70 + 0.04) * (1 - 0.08), rel=1e-14)
    assert g.EMISCALC_VSER(300.0, 0.0, 0.0, 70.0, 0.0, 8.0) == pytest.approx(300 / 18.45 * 0.34 * 0.92, rel=1e-14)
    ch4 = g.EMISCALC_CH4MAN_tier2(vs, 0.0, 0.24, 0.17, 365.0)
    assert ch4 == pytest.approx(vs * 0.24 * 0.67 * 0.17 * 365, rel=1e-14)
    t1 = g.EMISCALC_CH4MAN_tier1(0.0, {"10": 0.0, "15": 4.0}, {"10": 2.0, "15": 9.0}, {}, {"10": 30.0, "15": 70.0},
                                 365.0, True)
    assert t1 == pytest.approx((2.0 * 30 + 4.0 * 70) * 0.01)
    assert g.EMISCALC_CH4MAN_tier1(ch4, {"10": 2.0}, {}, {"10": 100.0}, {}, 365.0, True) == ch4
    f = g.EMISCALC_CH4MAN_NH3_techs(10.0, 0.05, 0.10, 0.3, 0.02, 0.08, 0.7)
    assert f == pytest.approx(10 * ((1 - 0.15) * 0.3 + (1 - 0.10) * 0.7), rel=1e-14)
