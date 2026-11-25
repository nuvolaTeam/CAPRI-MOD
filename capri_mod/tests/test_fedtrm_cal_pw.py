"""CAPRI's baseline feed calibration's driver and model (capri_mod/feed/equations/fedtrm_cal_pw.py, fedtrm_mod_pw.py:
feed/fedtrm_cal_pw.gms, feed/fedtrm_mod_pw.gms): GAMS's ncpcm, the GAMS variables' bounds, and the regional levels on
CAPRI's region sets. The calibration's solution against CAPRI's: tools/check/check_fedtrm_cal_2030.py."""
import math

from capri_mod.data.definitions import capri_pairs, capri_set
from capri_mod.feed.equations import fedtrm_cal_pw as cal
from capri_mod.feed.equations import fedtrm_mod_pw as mp
from capri_mod.feed.equations import fedtrm_prep as fp


def test_ncpcm_is_gams_smoothed_min():
    """ncpcm(x, y, Z) = x - Z ln(1 + exp((x - y) / Z)) (GAMS's NLPEC manual, equation 11), evaluated without overflow
    far from the kink, where it is min(x, y)."""
    import casadi as ca
    x, y, Z = ca.SX.sym("x"), ca.SX.sym("y"), ca.SX.sym("Z")
    f = ca.Function("f", [x, y, Z], [mp.ncpcm(x, y, Z)])
    for a, b, z in ((3., 1., 2.), (1., 3., 2.), (0., 0., 1.), (5., 5.5, .05)):
        assert abs(float(f(a, b, z)) - (a - z * math.log(1 + math.exp((a - b) / z)))) < 1e-12
    assert abs(float(f(1e5, 10., 2.)) - 10.) < 1e-9
    assert abs(float(f(10., 1e5, 2.)) - 10.) < 1e-9


def test_gams_variable_defaults_and_fx():
    """A POSITIVE VARIABLE's absent bounds are 0 and +inf; .FX sets level and both bounds; a free one is unbounded."""
    v = mp.GamsVar()
    assert (v.lo("k"), v.up("k"), v.l("k")) == (0.0, mp.INF, 0.0) and not v.fixed("k")
    v.fx("k", 2.5)
    assert (v.lo("k"), v.up("k"), v.l("k")) == (2.5, 2.5, 2.5) and v.fixed("k")
    f = mp.free_var()
    assert (f.lo("k"), f.up("k")) == (-mp.INF, mp.INF)


def _state(ms):
    mr = capri_pairs("MAP_RR")
    regs = {ms} | {b for a, b in mr if a == ms}
    ru = {r for m, r in capri_pairs("MS_RU")}
    return fp.FedtrmState(MS=ms, RU=tuple(sorted(r for r in regs if r in ru)),
                          SRNUTS1=tuple(sorted(r for r in regs if r in set(capri_set("SRNUTS1")))),
                          MAP_RR=frozenset((a, b) for a, b in mr if a in regs and b in regs), DATA={}, DATA_TRD={},
                          DATA_BAS={}, v_actLevl_L={}, p_technFact={}, p_animReq={}, p_animProdDays={},
                          p_minFeedShare={}, p_maxFeedShare={})


def test_regional_levels_follow_capris_hierarchy():
    """feed/fedtrm_cal_pw.gms l. 104-135 and 148-210 on CAPRI's sets: Denmark, one regional unit, is solved at "TOP"
    only; Germany at "TOP", then the member state over its NUTS 1 units, then each NUTS 1 unit with NUTS 2 units below
    it over these (Brandenburg, DE400000, a NUTS 1 unit that is its own NUTS 2 unit, is not solved below the member
    state)."""
    dk = _state("DK000000")
    assert [cal.RAGG_of_level(dk, lev) for lev in dk.R_LEVL] == [(), ("TOP",), (), ()]
    assert cal.RUNAGG_RUNR(dk, "TOP", "TOP") == (("DK000000",), ("DK000000",))
    de = _state("DE000000")
    assert cal.RAGG_of_level(de, "TOP") == ("TOP",) and cal.RAGG_of_level(de, "MS") == ("DE000000",)
    runagg, runr = cal.RUNAGG_RUNR(de, "MS", "DE000000")
    assert runagg == ("DE000000",) and set(runr) == set(de.SRNUTS1) and "DE000000" not in runr
    n1 = cal.RAGG_of_level(de, "NUTS1")
    assert "DE400000" in runr and "DE400000" not in n1 and len(n1) == len(runr) - sum(
        1 for r in runr if not any((r, k) in de.MAP_RR for k in de.RU if k != r))
    for ragg in n1:
        _, units = cal.RUNAGG_RUNR(de, "NUTS1", ragg)
        assert units and ragg not in units and all((ragg, u) in de.MAP_RR and u in de.RU for u in units)
