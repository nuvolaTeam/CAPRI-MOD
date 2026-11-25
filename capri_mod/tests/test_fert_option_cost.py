"""The fertiliser options' cost base in the regional NLP form (CapriRegionalNLP._abatement_block; KNOWN_ISSUES K175)."""
import numpy as np
import pytest


def test_option_cost_on_the_purchases_times_capris_need_factor():
    """CAPRI's GHG_Mit_Cost_ (supply_model.gms l. 5062-5068) charges the mineral-fertiliser options per t of crop N need
    met by mineral N: cost x (- v_netPutQuant(NITF)) x (1 + sum (NMIN + EmiCalMin) x share). The NLP form's term on the
    purchases is cost x (1 + sum (NMIN + EmiCalMin) x share); at the base (every IniShare 0) it and its derivative are
    the cost's own. ES420000's options: NITR_INH NMIN 0.0892, EmiCalMin 0.0058; PRECFARM 0.5354, 0."""
    import casadi as ca
    from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
    nlp = CapriRegionalNLP.__new__(CapriRegionalNLP)
    nlp._pv = lambda v: ca.DM(float(v)) if np.ndim(v) == 0 else ca.DM(np.asarray(v, float))
    techs = [("NITR_INH", 0.0892, 17.2, 131.3, 0.655), ("PRECFARM", 0.5354, 0.0, 686.7, 0.3521)]
    ec = {"NITR_INH": 0.0058}
    spec = {"fert_tech": {"techs": techs, "crops": [(0, 100.0)], "ecap": 0.146, "emical": ec}}
    X0 = ca.SX.sym("x", 1)
    X, _ = nlp._abatement_block(spec, X0, X0, 0, [], [], [], [], [])
    phi = X[1:]
    f = ca.Function("c", [phi], [nlp._fert_tech_pending[0]])
    s = np.array([0.241, 0.232])
    cost = sum(a * s_ + 0.5 * b * s_ * s_ for (_, _, a, b, _), s_ in zip(techs, s))
    fac = 1.0 + sum((nm + ec.get(n, 0.0)) * s_ for (n, nm, _, _, _), s_ in zip(techs, s))
    assert fac == pytest.approx(1.1471, abs=1e-4)
    assert float(f(s)) == pytest.approx(cost * fac, rel=1e-12)
    # the base: zero cost and the cost's own marginal (the calibration's linear terms unchanged)
    g = ca.Function("g", [phi], [ca.gradient(nlp._fert_tech_pending[0], phi)])
    assert float(f(np.zeros(2))) == 0.0
    assert np.allclose(np.asarray(g(np.zeros(2))).ravel(), [17.2, 0.0], atol=1e-12)
    # at the Green Deal's shares the marginal cost carries the factor and cost x (NMIN + EmiCalMin)
    gs = np.asarray(g(s)).ravel()
    assert gs[1] == pytest.approx(686.7 * s[1] * fac + cost * 0.5354, rel=1e-12)


def test_manure_inhibitor_cost_on_capris_base():
    """CAPRI's GHG_Mit_Cost_ charges the fertiliser options aimed at applied manure (targFertMan: the nitrification
    inhibitor on manure, target N2OMAN) on ManureNPK x (1 + incEmiAppl) x (1 + NMAN x share) (supply_model.gms
    l. 5144-5149, InclEmiAppl_ l. 975-1022): the manure N at the tail (excreted less the housing and storage losses).
    The NLP form charges it on the fertilisation block's manure N pool through GHG_Mit_Cost_targFertMan (KNOWN_ISSUES
    K183; until 19 November 2026 on the excreted manure N, 13-38% more in FR52: dairy cows' tail 0.76 of excretion,
    sows' 0.62); without a fertilisation block on the excreted N, as before."""
    import casadi as ca
    from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
    from capri_mod.supply.equations.supply_model.mitigation import GHG_Mit_Cost_targFertMan
    # the equation: 2,500 t of manure N at the tail, share 0.4, cost terms 12 and 30 EUR per t, NMAN 0.11 -> kEUR
    assert GHG_Mit_Cost_targFertMan(2500.0, 0.4, 12.0, 30.0, 0.11) == pytest.approx(
        2.5 * (1.0 + 0.11 * 0.4) * (12.0 * 0.4 + 0.5 * 30.0 * 0.16), rel=1e-12)
    assert GHG_Mit_Cost_targFertMan(2500.0, 0.0, 12.0, 30.0, 0.11) == 0.0

    def block(spec):
        nlp = CapriRegionalNLP.__new__(CapriRegionalNLP)
        nlp._pv = lambda v: ca.DM(float(v)) if np.ndim(v) == 0 else ca.DM(np.asarray(v, float))
        nlp.xb = np.array([50.0])
        X0 = ca.SX.sym("x", 1)
        X, obj = nlp._abatement_block(spec, X0, X0, 0, [], [], [], [], [])
        return nlp, X, obj

    mni = {"w": [(0, 80.0)], "nman": 0.11, "smax": 0.8, "S0": 12.0, "slope": 30.0, "vtax": 0.0}
    # with the fertilisation block's N pool: the cost waits for it (_fert_block adds it on the pool)
    nlp, X, obj = block({"mni": dict(mni), "npk": {"nutrients": {"N": {}}}})
    assert nlp._mni_cost_pending is not None and float(ca.DM(obj)) == 0.0
    s_m, S0m, slope_m, nman_m = nlp._mni_cost_pending[:4]
    assert (S0m, slope_m, nman_m) == (12.0, 30.0, 0.11)
    # without it: on the excreted manure N (80 t per unit x the level, kt), the former form
    nlp2, X2, obj2 = block({"mni": dict(mni)})
    assert nlp2._mni_cost_pending is None and nlp2._mni_base == pytest.approx(80.0 * 50.0 / 1000.0)
    f = ca.Function("c", [X2], [obj2])
    assert float(f([50.0, 0.4])) == pytest.approx(80.0 * 50.0 / 1000.0 * (12.0 * 0.4 + 15.0 * 0.16), rel=1e-12)


def test_fertiliser_option_calibration_leaves_capris_relsubs0():
    """CAPRI calibrates a fertiliser option's linear term so that its initial share (0) is optimal with a hypothetical
    subsidy relSubs0 x costParLin (envind/ghgMiti.gms l. 731, l. 1048-1071): with the saving at its value, the
    first-order condition at zero is + relSubs0 x costParLin, the subsidy early adopters need (l. 900-906). DEP-30 values
    the saving at the regional model's own marginal value of N; the calibration leaves CAPRI's relSubs0 x costParLin at
    zero (KNOWN_ISSUES K196). Before 21 November 2026 it made the condition zero where the option would leave zero, so
    the options moved at any rise of the value of N; that form (cal_relsubs0 False) remains for the urea
    substitution."""
    from capri_mod.supply.equations.ghgmiti import pmpParlin_fertTech_DEP30
    # NITR_INH: costParLin 86, relSubs0 0.2 -> S0 17.2 EUR/t; the model's value of the saving 71 EUR/t at the base
    S0, V0 = 17.2, 71.0
    r = S0 - V0                                    # the residual per t of the option's base at zero, c1 - V0
    b = pmpParlin_fertTech_DEP30(S0, r, True)
    assert b == pytest.approx(V0)                  # c1 = S0 + b = relSubs0 costParLin + V0
    assert (S0 + b) - V0 == pytest.approx(S0)      # the condition at zero: + relSubs0 costParLin
    # the former form: zero at the base
    b0 = pmpParlin_fertTech_DEP30(S0, r, False)
    assert (S0 + b0) - V0 == pytest.approx(0.0)
    # an option worth less than its subsidy at the base: left alone before, relSubs0 costParLin + V0 now
    assert pmpParlin_fertTech_DEP30(S0, S0 - 5.0, False) is None
    assert S0 + pmpParlin_fertTech_DEP30(S0, S0 - 5.0, True) == pytest.approx(S0 + 5.0)
    # relSubs0 0 (an option already adopted, maxShare < 1: CAPRI's 0.8 / 0): the condition zero at the base, as before
    assert pmpParlin_fertTech_DEP30(0.0, -40.0, True) == pytest.approx(40.0)


def test_manure_inhibitor_nman_restriction_and_shadow_value():
    """CAPRI's restriction of the inhibitor on manure's efficiency gain (restMitFert, envind/ghgMiti.gms l. 531-543) and
    p_manureShadVal (l. 871-876) take v_nutAvailFactExcr, the availability of excreted manure N at the calibration point
    (until 21 November 2026 the model took its marginal manure substitution for the restriction)."""
    from capri_mod.supply.equations.ghgmiti import othImpact_NMAN_restMitFert, p_manureShadVal
    nman = (1.0 / 0.9 - 1.0) ** 1.1
    assert nman == pytest.approx(0.089194, abs=1e-6)
    # FR520000: x 1.0, mark-up 0.1, availability 0.4229: no restriction
    assert othImpact_NMAN_restMitFert(nman, 1.0, 0.1, 0.4229, 1.1) == nman
    # availability above x + mark-up: none
    assert othImpact_NMAN_restMitFert(nman, 1.0, 0.1, 1.1, 1.1) == 0.0
    # within the band: ((x + m) / a - 1) ** e
    assert othImpact_NMAN_restMitFert(nman, 1.0, 0.1, 1.05, 1.1) == pytest.approx((1.1 / 1.05 - 1.0) ** 1.1)
    assert p_manureShadVal(1161.308188, 0.422861) == pytest.approx(1161.308188 * 0.422861)
