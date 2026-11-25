"""The methane per head in CAPRI's order (capri_mod/environmental/methane_per_head.py): gascoeff's management shares and
MCFMS, MITERRA's shares and CH4 losses (envind/ammo.gms), the raw tables from CAPRI's code, and Denmark's 2017 values
against CAPREG's (tools/check/check_methane_2017.py)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "check"), str(ROOT / "tools" / "build")]

from capri_mod.environmental.equations import ammo_ch4 as am  # noqa: E402
from capri_mod.environmental.equations import gascoeff as gc  # noqa: E402


def test_mcfms_by_hand():
    """One unit all in cell 10; MITERRA's grazing 0.15 and liquid 0.71 of the rest: MCFMS = 0.15 x 0.01 + 0.85 x 0.29 x
    0.02 + 0.85 x 0.71 x 0.17 (the EU's CH4 conversion factors of cell 10: pasture and solid from "Cool", liquid the
    cell's own)."""
    sh = gc.p_shareClimZone({}, ("DK000000",), ("Cool", "Temperate", "Warm"), ("10", "11"))
    assert sh[("DK000000", "Cool")] == 100.0 and sh[("DK000000", "10")] == 100.0
    raw = {("EU000000", "DCOL", "T", "CH4CONV", "Cool", s): v for s, v in (("Pasture", 0.01), ("Solid", 0.02),
                                                                           ("Liquid", 0.10))}
    raw[("EU000000", "DCOL", "T", "CH4CONV", "10", "Liquid")] = 0.17
    mg = gc.p_manureMgtShare_EU_CH4CONV(raw, ("DCOL",), (), ("10", "11"), (), ("Pasture", "Solid", "Liquid"))
    assert mg[("EU000000", "DCOL", "T", "CH4CONV", "10", "Pasture")] == 0.01
    assert mg[("EU000000", "DCOL", "T", "CH4CONV", "10", "Liquid")] == 0.17          # the cell's own kept
    nemi = {("DK000000", "DCOL", "N", "TYPESHARE", "GRAZ"): 0.15, ("DK000000", "DCOL", "N", "TYPESHARE", "SOLID"): 0.29,
            ("DK000000", "DCOL", "N", "TYPESHARE", "LIQUID"): 0.71}
    climall = ("Cool", "Temperate", "Warm", "10", "11")
    mg = gc.p_manureMgtShare_MS_MANAG(mg, ("DK000000",), ("DCOL",), climall, nemi)
    mg = gc.p_manureMgtShare_MS_CH4CONV(mg, ("DK000000",), ("DCOL",), climall)
    mcf = gc.EMISCALC_MCFMS(("DK000000",), {"DK000000": "DK000000"}, ("DCOL",), ("T",), ("10", "11"),
                            ("Pasture", "Solid", "Liquid"), {("DK000000", "DCOL", "T"): 1.0}, sh, mg, ())
    want = 0.15 * 0.01 + 0.85 * 0.29 * 0.02 + 0.85 * 0.71 * 0.17
    assert mcf[("DK000000", "DCOL", "T")] == pytest.approx(want, rel=1e-14)


def test_miterra_shares_and_ch4_losses_by_hand():
    """Denmark's dairy cows in MITERRA's 2000 (CAPREG's scenario year): grazing (1 - 296.5/365)(1 - 20/100), liquid
    451.56 / (451.56 + 184.44); the solid storage's CH4 -10% under the low-emission covers' share; the copy from DCOW
    to DCOL."""
    rc = {("DK000000", "DAICOW_S", "HD"): 296.5, ("DK000000", "DAICOW_S", "Et"): 20.0,
          ("DK000000", "DAICOW_L", "HD"): 296.5, ("DK000000", "DAICOW_L", "Et"): 20.0}
    g = am.p_Nemidat_GRAZ(("DK000000",), ("DCOW", "HENS"), (("DK000000", "DK000000"),),
                          (("DCOW", "DAICOW_L"), ("DCOW", "DAICOW_S"), ("HENS", "LAYHENS")),
                          ("DAICOW_L", "DAICOW_S"), ("DAICOW_L",), ("HENS",), rc)
    assert g == {("DK000000", "DCOW", "N", "TYPESHARE", "GRAZ"): pytest.approx((1 - 296.5 / 365) * 0.8, rel=1e-15)}
    bn = {("DK000000", "DAICOW_L", "2000"): 451.56, ("DK000000", "DAICOW_S", "2000"): 184.44}
    ls = am.p_Nemidat_Liquid_Solid(("DK000000",), ("DCOW",), ("DCOW",), (("DK000000", "DK000000"),),
                                   (("DAICOW_L", "DCOW"), ("DAICOW_S", "DCOW")), bn, 2000)
    liq = 451.56 / (451.56 + 184.44)
    assert ls[("DK000000", "DCOW", "N", "TYPESHARE", "LIQUID")] == pytest.approx(liq, rel=1e-15)
    assert ls[("DK000000", "DCOW", "N", "TYPESHARE", "SOLID")] == pytest.approx(1 - liq, rel=1e-15)
    cs = {("DK000000", "DAICOW_S", "CS_low", "2000"): 40.0, ("DK000000", "DAICOW_S", "CS_high", "2000"): 10.0}
    fs = am.FracToepStorage(cs, 2000)
    assert fs[("DK000000", "DAICOW_S", "NORMAL")] == 50.0
    red = {("DK000000", "DAICOW_S", "CH4", "LowEm"): -10.0}
    loss = am.p_Nemidat_CH4_LossStor(("DK000000",), ("DCOW",), ("liquid", "solid"), (("DK000000", "DK000000"),),
                                     (("DCOW", "DAICOW_L"), ("DCOW", "DAICOW_S")),
                                     (("liquid", "DAICOW_L"), ("solid", "DAICOW_S")), red, fs)
    assert loss == {("DK000000", "DCOW", "CH4", "LOSSSTOR", "SOLID"): pytest.approx(-0.04, rel=1e-15)}
    split = am.p_Nemidat_split_activities({**ls, **loss}, (("DCOW", "DCOL"), ("DCOW", "DCOH")), ("DCOL", "DCOH"))
    assert split[("DK000000", "DCOL", "CH4", "LOSSSTOR", "SOLID")] == pytest.approx(-0.04, rel=1e-15)
    assert am.ScenYear(2030) == 2020 and am.ScenYear(2010) == 2000


def test_the_reports_rations_by_hand():
    """The report's ration (reports/sol_simy.gms l. 254-257): two technologies of 30% and 70% of 10 heads, 100 and 200
    kg of grass per head, the second without a p_maxFeedShare for maize; the rations of the year's data replaced."""
    from capri_mod.coupling.equations.sol_simy import DATA_FEED_SIMY
    import methane_inputs as mi
    assert DATA_FEED_SIMY({"T1": 100.0, "T2": 200.0}, {"T1": 3.0, "T2": 7.0}, 10.0) == pytest.approx(170.0, rel=1e-15)
    DATA = {("DK000000", "DCOL", "LEVL"): 10.0, ("DK000000", "DCOL", "FGRA"): 999.0}
    fic = {("DK000000", "DCOL", "T1", "FGRA"): 100.0, ("DK000000", "DCOL", "T2", "FGRA"): 200.0,
           ("DK000000", "DCOL", "T1", "FMAI"): 50.0, ("DK000000", "DCOL", "T2", "FMAI"): 80.0}
    mx = {("DK000000", "DCOL", "T1", "FGRA"): 1.0, ("DK000000", "DCOL", "T2", "FGRA"): 1.0,
          ("DK000000", "DCOL", "T1", "FMAI"): 1.0}
    tf = {("DK000000", "DCOL", "LEVL", "T1"): 0.3, ("DK000000", "DCOL", "LEVL", "T2"): 0.7}
    out = mi.with_report_rations(DATA, fic, mx, tf)
    assert out[("DK000000", "DCOL", "FGRA")] == pytest.approx(170.0, rel=1e-15)
    assert out[("DK000000", "DCOL", "FMAI")] == pytest.approx(15.0, rel=1e-15)        # 50 x 0.3 only
    assert out[("DK000000", "DCOL", "FCER")] == 0.0


def test_the_raw_tables_from_capris_code():
    """build_gascoeff_tables reads CAPRI's tables as GAMS does: every value under one header, the counts of the GAMS
    text (EMISCALC0 129: 15 cattle x 7, the pigs' 6 each, hens and poultry 2, sheep 3, other animals 2), the
    management systems' shares of each animal adding up to 1 (to CAPRI's rounding)."""
    import build_gascoeff_tables as bg
    from paths import SOURCES
    f = SOURCES / "gams" / bg.FILE
    if not f.exists():
        pytest.skip("CAPRI's GAMS code is not available")
    lines = bg.gams_lines(f.read_text(errors="ignore"))
    counts = {}
    for sym, (_fname, rn, cn) in bg.TABLES.items():
        recs = [r for _, body in bg.tables_of(lines, sym) for r in bg.parse_table(body, sym)]
        counts[sym] = len(bg.frame(recs, rn, cn, sym))
    assert counts == {"EMISCALC0": 129, "p_tier1EmFactManMgt0": 798, "p_shareClimZone0": 1390}
    recs = []
    for _, body in bg.tables_of(lines, "p_manureMgtShare0"):
        for row, col, v, n in bg.parse_table(body, "p_manureMgtShare0"):
            recs.append((row, col, v, n) if len(row) == 5 else ((row + col[:1]), col[1:], v, n))
    t = bg.frame(recs, bg.MGT[1][:5], bg.MGT[1][5:], "p_manureMgtShare0")
    assert len(t) == 1341
    sums = t[t.par == "MANAG"].groupby(["region", "act", "clim"]).value.sum()
    assert (sums.between(0.999, 1.0011)).all()


@pytest.mark.slow
def test_denmark_2017_equals_capregs():
    """Denmark's 2017 methane per head (CH4ENT from the ration, CH4ENTstd, CH4MAN of every activity with a level) as
    CAPREG's DATA2 at "Y", to 1e-9 (1.4e-14 on 25 November 2026)."""
    import feed_chain_inputs as fci
    if not (fci.CAPREG_BASE / "DK.csv.gz").exists():
        pytest.skip("CAPREG's base year is not available")
    try:
        fci.raw_folder(None)
    except Exception as e:        # no access to the gated raw dataset
        pytest.skip(f"the raw dataset is not available: {e}")
    import check_methane_2017 as chk
    rows = chk.compare("DK", 2000)
    assert len(rows) == 50
    for ru, act, item, mine, ref, _ in rows:
        assert mine == pytest.approx(ref, rel=1e-9), (ru, act, item)
