"""G3.1 (claude/g3_plan.md): a captured market solve replays bit for bit (MarketModule._solve_captured,
tools/check/replay_market.py) - the cold first solve and a warm second one at a changed supply."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.slow
def test_captured_market_solves_replay_bit_for_bit(tmp_path):
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    from capri_mod.settings import override
    spec = importlib.util.spec_from_file_location("replay_market", ROOT / "tools" / "check" / "replay_market.py")
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)
    mm = MarketModule(load_all_data(str(ROOT / "capri_data")))
    exo = mm.capri_base_supply_rows()
    exo2 = exo.copy()
    exo2.loc[[r for r in exo2.index if str(r).startswith("FR")], "SWHE"] *= 1.1
    with override({"diagnostics.capture_market_dir": str(tmp_path)}):
        a = mm.solve(exogenous_supply=exo)
        b = mm.solve(exogenous_supply=exo2)
    assert a.converged and b.converged
    files = sorted(tmp_path.glob("market_*.pkl"))
    assert [f.name for f in files] == ["market_000.pkl", "market_001.pkl"]
    for f in files:
        assert rp.replay(f) == [], f.name
    # the replay compares: a changed result is found
    import pickle
    # the data and the blocks' caches stored once: the second solve adds only what changed
    assert files[1].stat().st_size < 5e6
    rec = pickle.loads(files[1].read_bytes())
    rec["result"].world_prices = rec["result"].world_prices * (1 + 1e-12)
    files[1].write_bytes(pickle.dumps(rec))
    assert rp.replay(files[1]) == ["result.world_prices"]
