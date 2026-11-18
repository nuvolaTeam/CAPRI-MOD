"""The fertiliser options' cost base in the regional NLP form (CapriRegionalNLP._abatement_block; KNOWN_ISSUES K175)."""
import numpy as np
import pytest


def test_option_cost_on_the_purchases_times_capris_need_factor():
    """CAPRI's GHG_Mit_Cost_ (supply_model.gms l. 4945-4950) charges the mineral-fertiliser options per t of crop N need
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
