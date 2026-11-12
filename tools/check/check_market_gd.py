"""The market alone against CAPRI's Green Deal 2030 market: given CAPRI's own supply-model results, does the market
give CAPRI's prices? (claude/gd_market_check.md)

CAPRI's last market solve of a converged run is reproduced with CAPRI's results as the supply side
(capri_data/validation/greendeal_2030/capri_gd_market_2030.csv.xz, tools/build/extract_capri_gd_market.py):

  supply              the EU's member states' production with raw milk delivered, one row per member state as a run
                      passes it (MarketModule.supply_rows_by_member_state, scaled to the market regions' totals);
                      Norway's market-region production with its raw milk delivered
  prices seen         CAPRI's scenario market prices over the reference's per market region (raw milk: its producer
                      price PPRI, CAPRI's PMRK of MILK being a constant of its market data): the prices the supply
                      models saw in a converged run (CAPRI's ProdNQ_ is centred on them, so the market's supply response
                      is zero where the market's prices are CAPRI's)
  feed bulks          per (member state, bulk FCER FPRO FENE FOTH) CAPRI's scenario feed over the reference's; FMIL as the
                      EU's (and Norway's) total

The market is calibrated first at the reference, as a run calibrates it at the baseline (bilateral_solve.py), then
solved. --case ref puts every input at the reference: the control, which must give CAPRI's 2030 market back.

Prints the price changes against the reference, model and CAPRI, in the EU's two market regions, the summary
over all regions (the regions without production of a product apart: the model reports their base price) and the
largest gaps. Writes the cells with --csv. Reports; no pass or fail.

    python tools/check/check_market_gd.py [--case gd|ref] [--csv OUT.csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TABLE = ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_gd_market_2030.csv.xz"
BULKS = ("FCER", "FPRO", "FENE", "FOTH")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", choices=("gd", "ref"), default="gd")
    ap.add_argument("--csv", type=Path)
    a = ap.parse_args()
    t = pd.read_csv(TABLE, keep_default_na=False, na_values=[""], float_precision="round_trip")
    col = "scen" if a.case == "gd" else "ref"
    piv = lambda it, c: t[t["item"] == it].pivot_table(index="region", columns="commodity", values=c, aggfunc="sum")

    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    data = load_all_data(ROOT / "capri_data")
    data["market_year"] = 2030                         # CAPRI's 2030 market (the projection layer sets it in a run)
    mm = MarketModule(data)
    # calibrated at the reference before any scenario input is set (a run calibrates at the baseline and keeps it)
    mm._bilateral_calibrate()
    mm._apply_trq_volumes(mm.par.bilat)
    mm.par.demand_cal_frozen = mm.par.demand_cal.copy()
    cm = list(mm.commodities)

    prod = piv("PROD", col)
    ms_rows = prod.loc[[r for r in prod.index if mm.eu_region_of_ms(r) is not None]]
    exo = mm.supply_rows_by_member_state(ms_rows, {rg: prod.loc[rg] for rg in mm.EU if rg in prod.index})
    for r in getattr(mm, "SUP", ()):
        exo.loc[r] = [float(prod.at[r, c]) if (c in prod.columns and pd.notna(prod.at[r, c])) else 0.0 for c in exo.columns]
        exo.at[r, "MILK"] = float(sum(float(prod.at[m, "MILK"]) for m in mm.SUP_NONEU_MS.get(r, ())
                                      if m in prod.index and pd.notna(prod.at[m, "MILK"])))

    p_ref, p_scn = piv("PMRK", "ref"), piv("PMRK", col)
    # raw milk: CAPRI's PMRK of MILK is a constant of its market data (not traded; unchanged in the scenario), its milk
    # price is the producer price PPRI: its change is taken
    m_ref, m_scn = piv("PPRI", "ref"), piv("PPRI", col)
    if "MILK" in p_ref.columns and "MILK" in m_ref.columns:
        k = [r for r in p_ref.index if r in m_ref.index and pd.notna(m_ref.at[r, "MILK"]) and m_ref.at[r, "MILK"] > 0]
        p_scn.loc[k, "MILK"] = p_ref.loc[k, "MILK"] * (m_scn.loc[k, "MILK"] / m_ref.loc[k, "MILK"])
    held = list(mm.EU) + list(getattr(mm, "SUP", ()))
    seen = (p_scn / p_ref).reindex(index=held, columns=cm)
    seen = seen.where(np.isfinite(seen), 1.0).fillna(1.0)
    mm.seen.eu_price_seen = seen.loc[list(mm.EU)]
    mm.seen.sup_price_seen = {r: seen.loc[r] for r in getattr(mm, "SUP", ())}

    f_ref, f_scn = piv("FEDM", "ref"), piv("FEDM", col)
    fb = mm._feed_bulk_params()
    ratio = lambda f1, f0, ms, b: (float(f1.at[ms, b] / f0.at[ms, b])
                                   if (ms in f0.index and b in f0.columns and f0.at[ms, b] > 0 and ms in f1.index
                                       and pd.notna(f1.at[ms, b])) else 1.0)
    mm.seen.feed_bulk_index = {(ms, b): ratio(f_scn, f_ref, ms, b)
                               for (ms, b) in list(fb.get("bulks") or {}) + list(fb.get("bulks_sup") or {}) if b in BULKS}
    tot = lambda f, mss: float(f.reindex(index=list(mss))["FMIL"].sum()) if "FMIL" in f.columns else 0.0
    eu_ms = sorted({ms for (ms, _b) in (fb.get("bulks") or {})})
    mm.seen.fmil_index = tot(f_scn, eu_ms) / tot(f_ref, eu_ms) if tot(f_ref, eu_ms) > 0 else 1.0
    mm.seen.fmil_index_sup = {rg: (tot(f_scn, v) / tot(f_ref, v) if tot(f_ref, v) > 0 else 1.0)
                              for rg, v in mm.SUP_NONEU_MS.items()}

    eq = mm.solve(exogenous_supply=exo)
    print(f"case {a.case}: market converged {eq.converged}, {eq.iterations} rounds")

    rows = []
    for r in eq.domestic_prices.index:
        for c in cm:
            if r not in p_scn.index or c not in p_scn.columns or pd.isna(p_scn.at[r, c]) or pd.isna(p_ref.at[r, c]):
                continue
            q0 = float(prod.at[r, c]) if (r in prod.index and c in prod.columns and pd.notna(prod.at[r, c])) else 0.0
            rows.append(dict(region=r, commodity=c, p_ref=float(p_ref.at[r, c]), p_capri=float(p_scn.at[r, c]),
                             p_model=float(eq.domestic_prices.at[r, c]), produces=q0 > 0))
    d = pd.DataFrame(rows)
    d["dp_capri"] = 100.0 * (d.p_capri / d.p_ref - 1.0)
    d["dp_model"] = 100.0 * (d.p_model / d.p_ref - 1.0)
    d["gap_pt"] = d.dp_model - d.dp_capri
    if a.csv:
        d.to_csv(a.csv, index=False)
    rel = (d.p_model - d.p_capri).abs() / d.p_capri.abs()
    print(f"{len(d)} prices: largest relative gap to CAPRI {rel.max():.3g}")
    eu = d.region.isin(list(mm.EU))
    for name, m in (("EU market regions", eu), ("other regions, with production", ~eu & d.produces),
                    ("other regions, no production (base price reported)", ~eu & ~d.produces)):
        g = d[m]
        cor = g[["dp_capri", "dp_model"]].corr().iloc[0, 1] if len(g) > 2 and g.dp_capri.std() > 0 else float("nan")
        print(f"  {name}: {len(g)} prices, |gap| mean {g.gap_pt.abs().mean():.3f} points, median "
              f"{g.gap_pt.abs().median():.3f}, 90th percentile {g.gap_pt.abs().quantile(0.9):.3f}; correlation of "
              f"changes {cor:.3f}")
    for r in mm.EU:
        g = d[d.region == r].set_index("commodity")
        print(f"\n{r}: price change, % (CAPRI, model, gap in points)")
        print(g[["dp_capri", "dp_model", "gap_pt"]].round(2).T.to_string())
    print("\nlargest gaps (points):")
    print(d.reindex(d.gap_pt.abs().sort_values(ascending=False).index).head(20)[
        ["region", "commodity", "produces", "dp_capri", "dp_model", "gap_pt"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
