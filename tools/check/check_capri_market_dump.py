"""Test A (G3, GR Q5.2): the market at CAPRI's own calibration point, against CAPRI's dump of its market model there.

CAPRI writes chk_market_data_<run>.gdx in arm/prep_market.gms (l. 1211, unload_market_data_for_debugging.gms) after
its check solve of m_globMarket at the calibrated point (l. 1207): every parameter of the market model and the levels
of its variables and equations. The copy used is the one the project lead provided for the Green Deal scenario run
(greendeal_greendeal_scenarios), converted to parquet per symbol (the directory given as --dump; read with pandas,
nothing written there). A check only: nothing of the model reads it.

The market module is solved at CAPRI's base supply rows (MarketModule.capri_base_supply_rows, the 2030 market) as
tools/check/check_market_base.py does; its equilibrium is compared with CAPRI's levels per market region (CAPRI's RM;
A_EU_WEST and A_EU_EAST are the model's EU_WEST and EU_EAST; quantities of CAPRI's RMS summed to their RM):

  production   v_prodQuant (RMS, summed)        against the equilibrium's production
  use          v_arm1Quant (RM)                 against its consumption (CAPRI's ArmBal1_ total use)
  human cons.  v_consQuant (RMS, summed)        against the use's human consumption (its base components)
  feed         v_feedQuant (RMS, summed)        against the use's feed
  processing   v_procQuant (RMS, summed)        against the use's processing
  price        v_marketPrice (RM)               against its domestic (market) prices
  Armington    v_arm1Price (RM)                 against the bilateral commodities' Armington price PA0
  flows        v_tradeFlows (importer, exporter) against its trade flows, the domestic sales (the diagonal) out

Prints per family the cells compared, the largest relative gap (scale max(|CAPRI|, 1)) and the counts above 1e-6 and
1e-3, then the worst cells; --csv writes every cell.

    python tools/check/check_capri_market_dump.py --dump DIR [--csv OUT.csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _var(dump: Path, name: str) -> pd.DataFrame:
    d = pd.read_parquet(dump / f"{name}.parquet")
    return d[[c for c in d.columns if c.startswith("d")] + ["level"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, required=True)
    ap.add_argument("--csv", type=Path)
    a = ap.parse_args()
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    data = load_all_data(ROOT / "capri_data")
    data["market_year"] = 2030
    mm = MarketModule(data)
    eq = mm.solve(exogenous_supply=mm.capri_base_supply_rows())
    regions, comms = list(mm.regions), list(mm.commodities)
    m2r = pd.read_parquet(a.dump / "RM_TO_RMS.parquet")
    ours = {rm: (rm[2:] if rm.startswith("A_") else rm) for rm in m2r.d1.unique()}
    rms_to_rm = {rms: ours[rm] for rm, rms in zip(m2r.d1, m2r.d2)}

    def by_rm(df, from_rms):
        df = df.copy()
        df["region"] = df.d1.map(rms_to_rm if from_rms else ours)
        df = df[df.region.isin(regions) & df.d2.isin(comms)]
        return df.groupby(["region", "d2"])["level"].sum() if from_rms else df.set_index(["region", "d2"])["level"]

    rows = []

    def add(kind, capri: pd.Series, model):
        for (rg, c), v in capri.items():
            m = model(rg, c)
            if m is None:
                continue
            rows.append(dict(kind=kind, region=rg, commodity=c, model=float(m), capri=float(v)))
    add("production", by_rm(_var(a.dump, "v_prodQuant"), True),
        lambda rg, c: eq.production.at[rg, c] if (rg in eq.production.index and c in eq.production.columns) else None)
    # raw milk is not in CAPRI's Armington system (not traded; v_arm1Quant MILK 0): its use is the dairies' intake
    add("use", by_rm(_var(a.dump, "v_arm1Quant"), False),
        lambda rg, c: eq.consumption.at[rg, c] if (c != "MILK" and rg in eq.consumption.index
                                                   and c in eq.consumption.columns) else None)
    # the use's base components (demand_response: calibrated base use x the components' shares)
    cal = {c: float(mm._demand_cal_factor(c)) for c in comms}
    comp = mm._use_components()
    B = mm.par.base_consumption

    def component(key):
        def f(rg, c):
            s = comp.get((rg, c))
            if s is None or rg not in B.index or c not in B.columns:
                return None
            return float(B.at[rg, c]) * cal[c] * s[key]
        return f
    add("human cons.", by_rm(_var(a.dump, "v_consQuant"), True), component("hcon"))
    add("feed", by_rm(_var(a.dump, "v_feedQuant"), True), component("feed"))
    add("processing", by_rm(_var(a.dump, "v_procQuant"), True), component("proc"))
    add("price", by_rm(_var(a.dump, "v_marketPrice"), False),
        lambda rg, c: eq.domestic_prices.at[rg, c] if (rg in eq.domestic_prices.index
                                                       and c in eq.domestic_prices.columns) else None)
    pa0 = {}
    for c, sc in (mm.par.bilat or {}).items():
        for i, rg in enumerate(sc.regions):
            pa0[(rg, c)] = float(sc.PA0[i])
    add("Armington", by_rm(_var(a.dump, "v_arm1Price"), False), lambda rg, c: pa0.get((rg, c)))
    tf = _var(a.dump, "v_tradeFlows")
    tf = tf[tf.d1 != tf.d2].copy()
    tf["imp"], tf["exp"] = tf.d1.map(ours), tf.d2.map(ours)
    tf = tf[tf.imp.isin(regions) & tf.exp.isin(regions) & tf.d3.isin(comms)]
    for t in tf.itertuples(index=False):
        k = (t.exp, t.imp)
        q = float(eq.trade_flows.at[k, t.d3]) if (k in eq.trade_flows.index and t.d3 in eq.trade_flows.columns) else 0.0
        rows.append(dict(kind="flows", region=t.imp, partner=t.exp, commodity=t.d3, model=q, capri=float(t.level)))
    d = pd.DataFrame(rows)
    d = d[(d.capri.abs() > 0) | (d.model.abs() > 0)]
    d["rel"] = (d.model - d.capri).abs() / d.capri.abs().clip(lower=1.0)
    if a.csv:
        d.to_csv(a.csv, index=False)
    print(f"market converged {eq.converged} in {eq.iterations} rounds")
    for kind, g in d.groupby("kind", sort=False):
        print(f"{kind:12s}: {len(g):6d} cells, largest relative gap {g.rel.max():.3g}, above 1e-6: "
              f"{int((g.rel > 1e-6).sum())}, above 1e-3: {int((g.rel > 1e-3).sum())}")
    print(d.sort_values("rel", ascending=False).groupby("kind").head(4).to_string(
        index=False, float_format=lambda x: f"{x:.6g}"))


if __name__ == "__main__":
    main()
