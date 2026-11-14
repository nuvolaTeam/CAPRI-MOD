"""Test B at CAPRI's converged Green Deal step: the market's response to CAPRI's own supply change, against CAPRI's.

CAPRI's two result files of the project lead's runs (dataOut, converted to parquet per symbol; --results the directory
holding both): the Green Deal baseline res_2_1730greendeal_refdefaulta and the scenario
res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA. The scenario changes the supply side only
(greendeal_scenarios.gms: landscape, organic area, pesticides, mineral fertiliser and surplus targets; diet00, oth00);
its one market setting (negative milk producer prices allowed, negProdPriceAllowed) is the baseline's too. A check
only: nothing of the model reads these files.

The market module is solved twice:
  baseline  at CAPRI's base supply rows (MarketModule.capri_base_supply_rows), the 2030 market calibrated at CAPRI's
            2030 data; CAPRI's baseline production equals that calibration point (DK and FR pork and milk: v_prodQuant
            of chk_market_data equals the baseline's NETF to the last digit);
  scenario  at the same rows, each member state's and Norway's product scaled by CAPRI's scenario/baseline ratio of
            its market production (NETF: gross production less seed and losses, the quantity CAPRI's market takes);
            the EU and Norway's supply anticipated against CAPRI's scenario/baseline market price ratios (the prices
            CAPRI's supply models saw in its last iteration, which its converged market reproduces); their feed
            bulks (seen.feed_bulk_index) at CAPRI's scenario/baseline ratio of each member state's bulk use (FEDM).
Compared: each EU block's and non-EU market region's change scenario/baseline - 1 of the market price (PMRK),
production (NETF for the EU blocks, PROD elsewhere), the EU blocks' domestic use (DOMM: human consumption, feed,
processing, industrial and biofuel use, seed and losses at the market), and every market region's imports and exports
between market regions (IMP, EXP: CAPRI's bilateral ImportQ of the region with each other market region, summed; its
IMPT and EXPT of the EU blocks also hold the trade between the member states of a block, which the model does not
have), ours against CAPRI's; and the baseline levels. Outside the EU CAPRI
reports wheat as WHEA (soft and durum together): ours summed.

    python tools/check/check_capri_gd_market.py --results DIR [--csv OUT.csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

REF = "res_2_1730greendeal_refdefaulta"
GD = "res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA"
EU_BLOCKS = {"A_EU_WEST": "EU_WEST", "A_EU_EAST": "EU_EAST"}
ITEMS_EU = ("PMRK", "NETF", "DOMM", "IMP", "EXP")
ITEMS_W = ("PMRK", "PROD", "IMP", "EXP")


def _data(results: Path, run: str, regions, rm_names) -> pd.Series:
    """CAPRI's 2030 values (region, item, product); IMP and EXP: the bilateral ImportQ between market regions summed
    per importer and per exporter (rm_names: CAPRI's market region -> the model's)."""
    d = pd.read_parquet(results / run / "dataOut.parquet", columns=["d1", "d2", "d3", "d4", "d5", "value"],
                        filters=[("d1", "in", list(regions)), ("d5", "==", "2030")])
    s = d[d.d2 == ""].set_index(["d1", "d3", "d4"])["value"]
    q = pd.read_parquet(results / run / "dataOut.parquet", columns=["d1", "d2", "d3", "d4", "d5", "value"],
                        filters=[("d3", "==", "ImportQ"), ("d5", "==", "2030")])
    q = q[q.d1.isin(rm_names) & q.d2.isin(rm_names) & (q.d1 != q.d2)].copy()
    q["imp"], q["exp"] = q.d1.map(rm_names), q.d2.map(rm_names)
    q = q[q.imp != q.exp]
    imp = q.groupby(["imp", "d4"]).value.sum()
    exp = q.groupby(["exp", "d4"]).value.sum()
    extra = pd.concat([pd.Series(imp.values, index=pd.MultiIndex.from_tuples([(a, "IMP", b) for a, b in imp.index])),
                       pd.Series(exp.values, index=pd.MultiIndex.from_tuples([(a, "EXP", b) for a, b in exp.index]))])
    return pd.concat([s, extra])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--csv", type=Path)
    a = ap.parse_args()
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    data = load_all_data(ROOT / "capri_data")
    data["market_year"] = 2030
    mm = MarketModule(data)
    regions, comms = list(mm.regions), list(mm.commodities)
    # CAPRI's product code of each model commodity (the member-state balance's table; the same code elsewhere)
    b = mm._inp().csv("eu_ms_balance_2030.csv", keep_default_na=False)
    code = {c: c for c in comms}
    code.update({str(c): str(p) for c, p in zip(b["commodity"], b["product"]) if str(c)})
    ms = sorted(set(b["ms"]))
    sup_ms = {r: list(v) for r, v in (mm.SUP_NONEU_MS or {}).items()}
    want = set(ms) | set(EU_BLOCKS) | {m for v in sup_ms.values() for m in v} | set(regions)
    # CAPRI's market regions under the model's names (its EU blocks are A_EU_WEST and A_EU_EAST; EU_WEST and EU_EAST
    # are aggregates of its results, left out)
    rm_names = {r: r for r in regions if r not in EU_BLOCKS.values()}
    rm_names.update(EU_BLOCKS)
    ref, gd = _data(a.results, REF, want, rm_names), _data(a.results, GD, want, rm_names)

    def val(s, rg, it, c):
        for k in (c, code.get(c, c)):
            v = s.get((rg, it, k))
            if v is not None and np.isfinite(v):
                return float(v)
        return None

    def ratio(rg, it, c):
        r0, r1 = val(ref, rg, it, c), val(gd, rg, it, c)
        return r1 / r0 if (r0 is not None and r1 is not None and abs(r0) > 1e-9) else None

    # baseline
    exo0 = mm.capri_base_supply_rows()
    e0 = mm.solve(exogenous_supply=exo0)
    print(f"baseline: market converged {e0.converged} in {e0.iterations} iterations", flush=True)
    # scenario rows: each supply-model country's rows scaled by CAPRI's NETF ratio of its member state
    cty_ms = {cty: m2 + "000000" for cty, m2 in mm._COUNTRY_MS.items()}
    exo1 = exo0.copy()
    n_sc = 0
    for cty in exo1.index:
        msc = cty_ms.get(cty)
        if cty in sup_ms:                                  # Norway's market region: its member states summed
            msl = sup_ms[cty]
        else:
            msl = [msc] if msc else []
        for c in exo1.columns:
            r0 = sum(val(ref, m, "NETF", c) or 0.0 for m in msl)
            r1 = sum(val(gd, m, "NETF", c) or 0.0 for m in msl)
            if r0 > 1e-9:
                exo1.at[cty, c] = float(exo1.at[cty, c]) * r1 / r0
                n_sc += 1
    # the prices CAPRI's supply models saw in its last iteration, as ratios to the baseline's (= the base)
    seen = pd.DataFrame(1.0, index=[r for r in mm.EU], columns=comms)
    for blk, rg in EU_BLOCKS.items():
        if rg in seen.index:
            for c in comms:
                q = ratio(blk, "PMRK", c)
                if q is not None and q > 0:
                    seen.at[rg, c] = q
    mm.seen.eu_price_seen = seen
    sup_seen = {}
    for rg, msl in sup_ms.items():
        s = pd.Series(1.0, index=comms)
        for c in comms:
            q = ratio(msl[0], "PMRK", c) if msl else None
            if q is not None and q > 0:
                s[c] = q
        sup_seen[rg] = s
    if sup_seen:
        mm.seen.sup_price_seen = sup_seen
    # the EU's and Norway's feed demand as their supply models pass it (coupling/feed.py): each member state's feed
    # bulk against its base, here CAPRI's scenario/baseline ratio of the member state's bulk use (FEDM of FCER, FPRO,
    # FENE, FMIL, FOTH)
    fb = mm._feed_bulk_params() or {}
    bix = {}
    for (msb, blk) in list((fb.get("bulks") or {}).keys()) + list((fb.get("bulks_sup") or {}).keys()):
        q = ratio(msb, "FEDM", blk)
        bix[(msb, blk)] = q if (q is not None and q > 0) else 1.0
    mm.seen.feed_bulk_index = bix
    moved = sum(1 for v in bix.values() if abs(v - 1.0) > 1e-9)
    print(f"scenario: {moved} of {len(bix)} feed bulks moved by CAPRI's ratios", flush=True)
    e1 = mm.solve(exogenous_supply=exo1)
    print(f"scenario: {n_sc} supply cells scaled by CAPRI's ratios; market converged {e1.converged} in "
          f"{e1.iterations} iterations", flush=True)

    def ours(e, rg, it, c):
        cs = ["SWHE", "DWHE"] if (c == "WHEA") else [c]
        cs = [x for x in cs if x in comms]
        if not cs or rg not in regions:
            return None
        if it == "PMRK":
            p = e.domestic_prices
            if len(cs) > 1:
                q = e.production.loc[rg, cs].astype(float)
                return float((p.loc[rg, cs] * q).sum() / max(q.sum(), 1e-9))
            return float(p.at[rg, cs[0]])
        if it in ("NETF", "PROD"):
            return float(e.production.loc[rg, cs].sum())
        if it == "DOMM":
            return float(e.consumption.loc[rg, cs].sum())
        if it in ("IMP", "EXP"):
            tf = e.trade_flows                   # index (exporter, importer)
            m = [k for k in tf.index if (k[1] == rg if it == "IMP" else k[0] == rg) and k[0] != k[1]]
            return float(tf.loc[m, [x for x in cs if x in tf.columns]].to_numpy(dtype=float).sum()) if m else None
        return None
    rows = []
    for blk, rg in list(EU_BLOCKS.items()) + [(r, r) for r in regions if r not in EU_BLOCKS.values()]:
        items = ITEMS_EU if blk in EU_BLOCKS else ITEMS_W
        for c in comms + (["WHEA"] if blk not in EU_BLOCKS else []):
            cc = code.get(c, c)
            if blk not in EU_BLOCKS and c in ("SWHE", "DWHE"):
                continue
            for it in items:
                key = rg if it in ("IMP", "EXP") else blk
                c0, c1 = val(ref, key, it, c), val(gd, key, it, c)
                o0, o1 = ours(e0, rg, it, c), ours(e1, rg, it, c)
                if c0 is None and o0 is None:
                    continue
                rows.append(dict(region=rg, commodity=c, capri_code=cc, item=it, capri_ref=c0, capri_gd=c1,
                                 model_ref=o0, model_gd=o1))
    d = pd.DataFrame(rows)
    ok = d.capri_ref.notna() & d.capri_gd.notna() & d.model_ref.notna() & d.model_gd.notna()
    d["capri_chg"] = np.where(ok, d.capri_gd / d.capri_ref.where(d.capri_ref.abs() > 1e-9) - 1.0, np.nan)
    d["model_chg"] = np.where(ok, d.model_gd / d.model_ref.where(d.model_ref.abs() > 1e-9) - 1.0, np.nan)
    d["chg_gap_pts"] = 100.0 * (d.model_chg - d.capri_chg)
    d["level_gap_ref"] = (d.model_ref - d.capri_ref) / d.capri_ref.abs().clip(lower=1.0)
    if a.csv:
        d.to_csv(a.csv, index=False)
    g = d[ok & (d.capri_ref.abs() > 1.0)]
    print("change scenario/baseline - 1, ours against CAPRI's (percentage points): per item, cells, median and 95th "
          "percentile of the absolute gap, largest")
    for it, x in g.groupby("item"):
        ab = x.chg_gap_pts.abs()
        print(f"  {it:5s} {len(x):5d} cells  median {ab.median():6.2f}  p95 {ab.quantile(0.95):6.2f}  max {ab.max():7.2f}")
    for it in ("PMRK", "NETF", "PROD", "IMP", "EXP"):
        x = g[g.item == it].reindex(g[g.item == it].chg_gap_pts.abs().sort_values(ascending=False).index).head(8)
        if len(x):
            print(f"\n{it}: largest gaps")
            print(x[["region", "commodity", "capri_ref", "capri_chg", "model_chg", "chg_gap_pts"]].to_string(
                index=False, float_format=lambda v: f"{v:.4g}"))
    print("\nthe EU blocks' market prices (change in %, CAPRI / ours):")
    x = g[(g.item == "PMRK") & g.region.isin(EU_BLOCKS.values())]
    print(x.assign(capri=100 * x.capri_chg, ours=100 * x.model_chg)[["region", "commodity", "capri", "ours"]]
          .to_string(index=False, float_format=lambda v: f"{v:.2f}"))


if __name__ == "__main__":
    main()
