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
    stub.seen.yani_state = {"EU27": {"goods": ["calves"], "net": {"calves": 100.0}, "ref": {"calves": 104.0},
                                 "seen": {"calves": 1.2}, "bounds": (-50.0, 50.0)}}
    dP = np.array([0.1])                                    # beef price ratio up 0.1 against what the models saw
    extra = stub._yani_clear("EU27", H, ["BEEF"], ["BEEF"], dP)
    dr = (104.0 - 100.0 - (-10.0) * 0.1) / 40.0             # the calf price change that clears the market
    assert abs(stub.ev.yani_market_now["EU27"]["calves"] - (1.2 + dr)) < 1e-12
    assert abs(float(np.asarray(extra).ravel()[0]) - (-20.0 * dr)) < 1e-12
    stub.seen.yani_state = None
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
        # a baseline alone does not measure it (28 October 2026): the scenario on it does, first thing
        assert not getattr(m, "market_supply_hessian_log", None)
        assert m.market_module.par.supply_hessian is None
        sc = greendeal_scenario(lndscpTarg=10, orgTarg=25, pestRedu=50, surpRedu=50, mineRedu=20)
        m.run(custom_scenario=sc, regions=regs, max_outer_iter=3)
        base, scen = (dict(d) for d in m.market_supply_hessian_log[-2:])
        assert len(m.market_supply_hessian_log) == 2
        assert base.get("source") in ("computed", "cache") and "at_iteration" not in base, base
        assert scen.get("source") in ("computed", "cache") and scen.get("at_iteration") == 2, scen
        assert "scenario_error" not in scen
        assert scen["file"] != base["file"]


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
        # the verification needs a measured Hessian, not the cache: the verify mode's file is removed after the run.
        # A scenario on the baseline measures it (a world-price shock is a scenario), first thing in its run
        m.run(scenario="BASELINE", regions=regs, max_outer_iter=2)
        m.run(world_price_shock={"SWHE": 0.05}, regions=regs, max_outer_iter=1)
        info = dict(m.market_supply_hessian_log[0])
        if info.get("source") == "computed":
            assert info.get("verified", 0) > 0, info
            assert info.get("verify_mismatch") == [], info
            os.remove(info["file"])
        else:
            assert info.get("source") == "cache", info


def test_milk_price_held_above_zero_unless_the_scenario_allows_negative_prices():
    """CAPRI's negProdPriceAllowed(rms, "MILK") (greendeal_scenarios.gms l. 66-67): with it a member state's raw milk
    price may go below zero; without it the price is held at its positive lower bound (the milk market then does not
    clear, recorded), the fat and protein balances still hold. The Green Deal group sets it."""
    import numpy as np
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    from capri_mod.policy.greendeal import farm_to_fork_scenario, greendeal_2030_scenario
    from capri_mod.policy.policy_module import PolicyScenario
    assert farm_to_fork_scenario().negative_milk_price and greendeal_2030_scenario().negative_milk_price
    assert not PolicyScenario(name="x", description="").negative_milk_price
    m = MarketModule(load_all_data("capri_data"))
    prm = m._dairy_params()["ms"]
    cls = type(m)
    p = prm["PT000000"]
    zt = np.zeros(p["G"].shape[1])
    # a glut: three times the base milk delivered drives the free price below zero
    z = cls._dairy_solve_ms(p, zt, 3.0)
    assert 1.0 + z[p["iM"]] < 0.0
    za = cls._dairy_solve_ms_at(p, zt, cls.MILK_PRICE_FLOOR)
    assert abs(1.0 + za[p["iM"]] - cls.MILK_PRICE_FLOOR) < 1e-15
    assert abs(float(p["rowF"] @ za)) < 1e-9 and abs(float(p["rowP"] @ za)) < 1e-9
    # through the block: held and recorded without the switch, free with it
    m.negative_milk_price = False
    m.dairy_block({}, {"PT000000": 3.0})
    assert "PT000000" in m._milk_floor_hits and m._milk_floor_hits["PT000000"] < 0.0
    m.negative_milk_price = True
    m.dairy_block({}, {"PT000000": 3.0})
    assert m._milk_floor_hits == {}


def test_moved_market_attributes_fail_loudly():
    """Refactor stage 2b moved the market's state into par/ev/sv/seen; a read or a write of an old name raises
    (RuntimeError: getattr(obj, name, default) cannot hide it), naming the new place."""
    import pytest
    from capri_mod.market.market_module import MarketModule
    from capri_mod.market.state import MOVED
    m = MarketModule.__new__(MarketModule)
    with pytest.raises(RuntimeError, match="ev.dairy_last"):
        getattr(m, "_dairy_last", None)
    with pytest.raises(RuntimeError, match="par.supply_hessian"):
        m.supply_hessian = None
    assert getattr(m, "no_such_attribute", 1) == 1
    assert "base_production" in MOVED and "last_market_solver" in MOVED


def test_dairy_processing_follows_capri_procnq_and_balances_fat_and_protein():
    """Audit M9: the dairy products' processing is CAPRI's ProcNQ_ per member state (37 own-price terms; cheese,
    casein, butter, fresh milk products), falling as the product's price rises, kept positive by ProcFudge_; it enters
    each member state's FatsProtBal_, so fat and protein still balance: raw milk's = sum (production - processing)."""
    import numpy as np
    from capri_mod.model import CAPRIModel
    m = CAPRIModel(data_dir="capri_data", verbose=False, regions=["DE110000"])
    mm = m.market_module
    dp = mm._dairy_params()
    tr = {k: 1.0 for k in mm.DAIRY_TRADED}
    base = mm.dairy_block(dict(tr), 1.0)
    assert max(abs(v) for v in base["processing_change"].values()) < 1e-9       # at base prices: base processing
    tr["CHES"] = 1.10
    res = mm.dairy_block(dict(tr), 1.0)
    assert res["processing_change"]["CHES"] < 0                                   # dearer cheese: less processed
    n_checked = 0
    for ms, prm in dp["ms"].items():
        z = res["ms_z"][ms]
        Q = prm["Q0"] + prm["G"] @ z
        part = prm["parts"][0]
        dproc, _, _ = mm._dairy_proc_change(prm, z)
        net = Q - part["proc0"] - dproc
        iM = prm["iM"]
        for c in ("f", "r"):
            w = part[c]
            milk_side = w[iM] * Q[iM]
            prod_side = sum(w[i] * net[i] for i in range(len(net)) if i != iM)
            base_milk = w[iM] * prm["Q0"][iM]
            base_prod = sum(w[i] * (prm["Q0"][i] - part["proc0"][i]) for i in range(len(net)) if i != iM)
            # FatsProtBal_ in changes: the change of the milk side equals the change of the product side
            assert abs((milk_side - base_milk) - (prod_side - base_prod)) < 1e-6 * max(1.0, abs(base_milk))
        if abs(dproc).sum() > 0:
            n_checked += 1
    assert n_checked >= 5                                                       # member states with dairy processing


def test_eu_fish_and_other_oils_supply_as_capri_prodnq():
    """Programme step D: the EU supply of other vegetable oils and the fish products is CAPRI's ProdNQ_ per member
    state (p_hessNQSupp x PPRI0 / INPE, summed per EU market region), linear in the price ratios against base; at
    the calibration prices it gives CAPRI's own p_elasSupp (about 0.98 for France's other oils)."""
    import numpy as np
    import pandas as pd
    from capri_mod.csvio import read_csv
    from capri_mod.model import CAPRIModel
    m = CAPRIModel(data_dir="capri_data", verbose=False, regions=["DE110000"])
    mm = m.market_module
    P = mm._eu_market_supply_nq_params()
    assert set(x for (x, _) in P["EU27"]) == set(mm.EU_MARKET_SUPPLY)
    cols = list(mm.commodities)
    sup = mm.par.base_production.reindex(columns=cols).fillna(0.0).copy()
    r = np.ones(len(cols)); r[cols.index("FFIS")] = 1.10
    mm._eu_market_supply_nq(sup, cols, lambda rg: r)
    q0 = float(mm.par.base_production.at["EU27", "FFIS"])
    own = sum(h for (x, y), h in P["EU27"].items() if x == "FFIS" and y == "FFIS")
    assert abs(float(sup.at["EU27", "FFIS"]) - (q0 + own * 0.10)) < 1e-9
    assert float(sup.at["EU27", "OTHO"]) == float(mm.par.base_production.at["EU27", "OTHO"])    # its prices unchanged
    t = read_csv("capri_data/2017/market/eu_market_supply_nq.csv")
    fr = t[(t.ms == "FR000000") & (t.x == "OTHO") & (t.y == "OTHO")].iloc[0]
    assert abs(fr.h * fr.ppri_y / fr.inpe - fr.h_ratio) < 1e-9 and abs(fr.inpe - 1.019 ** 13) < 1e-3
