"""The purchased feed bulks' prices as CAPRI's (register DEP-14, KNOWN_ISSUES K197): the 2030 baseline's (CAPRI's 2030
UVAG of the bulk over its 2017 one over the deflator; projection/prices.py ration_bulk_price_index) and a scenario's
change from it (arm/set_prices.gms, the Laspeyres version; market/equations/set_prices.py, MarketModule.
feed_bulk_uvag_ratio)."""
from pathlib import Path

import pandas as pd
import pytest

from capri_mod.market.equations.set_prices import DATA_UVAG_FEED_TRD_Y
from capri_mod.projection.prices import FEED_BULKS, ration_bulk_price_index

ROOT = Path(__file__).resolve().parents[2]
TRAJ = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "trajectories"


def test_the_laspeyres_statement_is_capris():
    """set_prices.gms l. 394-412: UVAG(TRD) x [1 + (sum r w / sum w - 1) x min(1, FOOD / GROF)]; unchanged where
    FOOD at the trend point or in the simulation is below 0.1, or GROF or the weights are zero."""
    w, r = [200.0, 100.0], [1.2, 0.9]
    las = (1.2 * 200 + 0.9 * 100) / 300
    assert DATA_UVAG_FEED_TRD_Y(250.0, w, r, 80.0, 81.0, 100.0) == pytest.approx(250.0 * (1 + (las - 1) * 0.8))
    assert DATA_UVAG_FEED_TRD_Y(250.0, w, r, 120.0, 81.0, 100.0) == pytest.approx(250.0 * las)     # MIN(1, ...)
    assert DATA_UVAG_FEED_TRD_Y(250.0, w, [1.0, 1.0], 80.0, 81.0, 100.0) == 250.0
    for food_trd, food_y, grof in ((0.05, 1.0, 1.0), (1.0, 0.05, 1.0), (1.0, 1.0, 0.0)):
        assert DATA_UVAG_FEED_TRD_Y(250.0, w, r, food_trd, food_y, grof) == 250.0
    assert DATA_UVAG_FEED_TRD_Y(250.0, [0.0, 0.0], r, 1.0, 1.0, 1.0) == 250.0


def test_the_2030_bulk_prices_are_capris_2030_unit_values():
    """CAPRI's 2030 reference holds every EU member state's bulk prices at their 2017 values (no bulk price in the
    trend, load_base_data_and_trends.gms l. 693): the index is 1 / deflator there; Norway's moves (its trend has them)."""
    pr = pd.read_csv(TRAJ / "capri_price_ratios_2030.csv", keep_default_na=False)
    ratio = {(r.ms, r.product): float(r.real_ratio) for r in pr.itertuples()}
    rb = ration_bulk_price_index(ratio)
    d = float(pr["deflator"].iloc[0])
    for b in FEED_BULKS:
        for ms in ("DE000000", "FR000000", "PL000000", "BL000000"):
            assert rb[(ms, b)] == pytest.approx(1.0 / d, rel=1e-5), (ms, b)
    assert rb[("NO000000", "FCER")] > 1.0
    b = pr[pr["product"].isin(FEED_BULKS)]
    assert len(b) == 173 and (b["uvag_2017"] > 0).all()


def test_the_supply_sides_bulk_price_follows_its_ingredients():
    """MarketModule.feed_bulk_uvag_ratio: 1 at the trend point; the ingredients' change weighted by their values, times
    the share of the bulk they cover (DE's FENE: FENI covers 72% of CAPRI's GROF, MOLA has no market)."""
    from capri_mod.model import CAPRIModel
    m = CAPRIModel(data_dir=str(ROOT / "capri_data"), verbose=False)
    mm = m.market_module
    fb = mm._feed_bulk_params()
    assert mm.feed_bulk_uvag_ratio("DE000000", "FCER", {}) == pytest.approx(1.0, abs=1e-14)
    d = fb["bulks"][("DE000000", "FENE")]
    cover = float(d["q0"].sum()) / d["grof"]
    assert 0.70 < cover < 0.74
    assert mm.feed_bulk_uvag_ratio("DE000000", "FENE", {"FENI": 1.1}) == pytest.approx(1.0 + 0.1 * cover, rel=1e-12)
    d = fb["bulks"][("DE000000", "FCER")]
    want = 1.0 + 0.2 * float(d["s"][list(d["comm"]).index("BARL")]) * min(1.0, float(d["q0"].sum()) / d["grof"])
    assert mm.feed_bulk_uvag_ratio("DE000000", "FCER", {"BARL": 1.2}) == pytest.approx(want, rel=1e-12)
