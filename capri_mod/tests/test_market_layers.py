"""The market's layer rules (docs/design/ARCHITECTURE_REFACTOR.md): only the data adapter reads files, and a missing
input stops the run with the name of its builder."""
from pathlib import Path

import pytest

MARKET = Path(__file__).resolve().parents[1] / "market"


def test_only_the_data_adapter_reads_files():
    import io
    import tokenize
    offenders = []
    for p in sorted(MARKET.glob("*.py")):
        if p.name == "inputs.py":
            continue
        toks = [t for t in tokenize.generate_tokens(io.StringIO(p.read_text()).readline)
                if t.type not in (tokenize.STRING, tokenize.COMMENT)]
        for a, b in zip(toks, toks[1:]):
            if (a.string in ("read_csv", "open", "read_text", "read_json") and b.string == "(") or \
                    (a.string == "json" and b.string == ".") or a.string in ("__file__",):
                offenders.append(f"{p.name}:{a.start[0]}: {a.line.strip()[:100]}")
    assert offenders == [], offenders


def test_missing_input_names_its_builder(tmp_path):
    from capri_mod.market.inputs import MarketInputs
    inp = MarketInputs(tmp_path, "2017")
    with pytest.raises(FileNotFoundError, match="build_gl_demand.py"):
        inp.csv("gl_demand_goods.csv")
    assert inp.csv("gl_demand_goods.csv", required=False) is None
    assert inp.path("rms_to_rm.csv", "shared") == tmp_path / "shared" / "rms_to_rm.csv"


def test_model_does_not_read_delta_tables():
    """Data formats (ARCHITECTURE_REFACTOR.md): the model reads CSV; Delta Lake is the pipeline's internal format."""
    pkg = MARKET.parent
    offenders = [str(p.relative_to(pkg)) for p in pkg.rglob("*.py")
                 if "pipeline" not in p.relative_to(pkg).parts and "tests" not in p.relative_to(pkg).parts
                 and ("import deltalake" in p.read_text() or "from deltalake" in p.read_text())]
    assert offenders == [], offenders


def test_young_animal_markets_clear_with_the_products():
    """CAPRI's yaniMarket_ inside the market (K75): at given product price changes the young-animal prices solve
    net(now) + H_YP dP + H_YY dr = reference, and the products' supply gets H_PY dr."""
    import numpy as np
    import pandas as pd
    from capri_mod.market import supply as msup
    cls = next(v for k, v in vars(msup).items() if isinstance(v, type) and hasattr(v, "_yani_clear"))
    stub = cls.__new__(cls)
    idx = ["BEEF", "YANI:calves"]
    H = pd.DataFrame([[50.0, -20.0], [-10.0, 40.0]], index=idx, columns=idx)   # dQ per unit price ratio
    stub._yani_state = {"EU27": {"goods": ["calves"], "net": {"calves": 100.0}, "ref": {"calves": 104.0},
                                 "seen": {"calves": 1.2}, "bounds": (-50.0, 50.0)}}
    dP = np.array([0.1])                                    # beef price ratio up 0.1 against what the models saw
    extra = stub._yani_clear("EU27", H, ["BEEF"], ["BEEF"], dP)
    dr = (104.0 - 100.0 - (-10.0) * 0.1) / 40.0             # the calf price change that clears the market
    assert abs(stub._yani_market_now["EU27"]["calves"] - (1.2 + dr)) < 1e-12
    assert abs(float(np.asarray(extra).ravel()[0]) - (-20.0 * dr)) < 1e-12
    stub._yani_state = None
    assert stub._yani_clear("EU27", H, ["BEEF"], ["BEEF"], dP) == 0.0


def test_tariff_change_applies_to_price_plus_transport_of_the_importer():
    """Audit M10: CAPRI's impPrice_ applies the ad valorem tariff to (exporter's market price + transport cost); the
    change lands on the named importer only, and not on flows between that importer's own rows."""
    import numpy as np
    from capri_mod.market.bilateral import BilateralCommodity
    n = 3
    z = np.zeros((n, n))
    a0 = np.array([[0, 100.0, 90.0], [100.0, 0, 95.0], [80.0, 85.0, 0]])
    tc = np.array([[0, 10.0, 20.0], [10.0, 0, 15.0], [5.0, 6.0, 0]])
    sc = BilateralCommodity("X", ["A", "B", "C"], z, a0.copy(), z.copy(), a0, np.ones(n), 8.0, 10.0, tc=tc)
    r = np.array([1.0, 1.2, 1.0])
    p0 = sc.import_prices(r)
    p1 = sc.import_prices(r, [([0], 10.0)])                       # importer A: +10 points
    assert abs((p1 - p0)[0, 1] - (100.0 * 1.2 + 10.0) * 0.10) < 1e-12
    assert abs((p1 - p0)[0, 2] - (90.0 * 1.0 + 20.0) * 0.10) < 1e-12
    assert np.all((p1 - p0)[1:] == 0)                            # other importers unchanged
    p2 = sc.import_prices(r, [([0, 1], 10.0)])                    # A and B as one importer (EU blocks)
    assert (p2 - p0)[0, 1] == 0 and (p2 - p0)[1, 0] == 0          # no tariff between its own rows
    assert abs((p2 - p0)[1, 2] - (95.0 + 15.0) * 0.10) < 1e-12


def test_member_state_milk_responds_to_its_price_in_the_dairy_block():
    """Audit M5: with the member state's raw milk supply responding to its milk price (ProdNQ_ MILK), the dairy block
    clears delivered = dairies' demand at the price it finds; without a response (k = 0) it is the fixed-delivery
    solve, and a positive response lowers the price change of a supply shortfall."""
    import numpy as np
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    m = MarketModule(load_all_data("capri_data"))
    prm = m._dairy_params()["ms"]
    cls = type(m)
    ms, p = prm.get("PT000000") and ("PT000000", prm["PT000000"]) or next(iter(prm.items()))
    n = p["G"].shape[1]
    zt = np.zeros(n)
    z0 = cls._dairy_solve_ms(p, zt, 0.95)
    z1 = cls._dairy_solve_ms_resp(p, zt, 0.95, 0.0, 1.0)
    assert np.allclose(z0, z1)
    k, L = 0.4, 1.0
    z2 = cls._dairy_solve_ms_resp(p, zt, 0.95, k, L)
    mr = 0.95 + k * (1.0 + z2[p["iM"]] - L)
    # the dairies' demand at z2 equals the delivered milk
    assert abs(float(p["G"][p["iM"]] @ z2) - p["Q0"][p["iM"]] * (mr - 1.0)) < 1e-8 * max(1.0, p["Q0"][p["iM"]])
    assert abs(z2[p["iM"]]) < abs(z0[p["iM"]])


def test_market_supply_hessian_measured_at_base_and_at_scenario_state():
    """The market supply Hessian (CAPRI's p_hessNQSupp, supply/calibrate_supply.gms) is built at the baseline and,
    under market.hessian_scenario_iter, measured again at the scenario's state with its own cache key. r131 ran
    without it because building the key raised and the warning was silenced: the metadata must show it."""
    from capri_mod.settings import override
    from capri_mod.model import CAPRIModel
    from capri_mod.policy.greendeal import greendeal_scenario
    regs = ["DE110000", "FR100000"]
    with override({"market.hessian_scenario_iter": 2, "market.market_supply_nq": True}):
        m = CAPRIModel(data_dir="capri_data", verbose=False)
        m.run(scenario="BASELINE", regions=regs, max_outer_iter=2)
        base = dict(m.market_supply_hessian_info or {})
        assert base.get("source") in ("computed", "cache"), base
        sc = greendeal_scenario(lndscpTarg=10, orgTarg=25, pestRedu=50, surpRedu=50, mineRedu=20)
        m.run(custom_scenario=sc, regions=regs, max_outer_iter=3)
        scen = dict(m.market_supply_hessian_info or {})
        assert scen.get("source") in ("computed", "cache") and scen.get("at_iteration") == 2, scen
        assert "scenario_error" not in scen
        assert scen["file"] != base["file"]
        assert [d["file"] for d in m.market_supply_hessian_log[-2:]] == [base["file"], scen["file"]]


def test_hessian_skip_of_unreached_regions_is_exact(monkeypatch):
    """The market supply Hessian with the regions a shock does not reach not re-solved (market.hessian_skip_unchanged)
    equals re-solving every region from the baseline's state: with CAPRI_HESSIAN_SKIP_VERIFY=1 the regions that would be
    skipped are solved and their results must equal the base re-solve's (else the problem fingerprint misses an input)."""
    import glob
    import os
    from capri_mod.settings import override
    from capri_mod.model import CAPRIModel
    monkeypatch.setenv("CAPRI_HESSIAN_SKIP_VERIFY", "1")
    regs = ["DE110000", "NO080000"]
    with override({"market.hessian_skip_unchanged": True, "market.market_supply_nq": True}):
        m = CAPRIModel(data_dir="capri_data", verbose=False)
        # the verification needs a measured Hessian, not the cache: the verify mode's file is removed after the run
        m.run(scenario="BASELINE", regions=regs, max_outer_iter=2)
        info = dict(m.market_supply_hessian_info or {})
        if info.get("source") == "computed":
            assert info.get("verified", 0) > 0, info
            assert info.get("verify_mismatch") == [], info
            os.remove(info["file"])
        else:
            assert info.get("source") == "cache", info
