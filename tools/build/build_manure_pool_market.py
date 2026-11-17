"""The terms of CAPRI's manure pool market (manuremarket/m_mPoolMarket) per region and nutrient, from CAPRI's fertiliser
distribution results of its 2030 Green Deal baseline (priFertDist_<MS>1730defaulta.gdx, results/fert; the raw dataset
nuvolaTeam/capri-mod-raw, capri/results/fert/priFertDist_<MS>1730defaulta/, as Parquet).

Per CAPRI region r and FOUT (MANN, MANP, MANK; sets.gms FOUT_T_N: NITF, PHOF, POTF), as CAPRI computes them
(manuremarket/declare_manure_market.gms l. 466-505):
  supply_t        sum over the fertiliser groups of p_priFertDist(r, "postMode", "EXCR", FNUT, NGRP, 2030): the manure
                  nutrient distributed to the crops, t (v_fertDist is in t, supply_model.gms fertDistExcr_)
  dual_cal_eur_t  p_dualValueManureCal(r, FOUT): ManureNPK_.M at the calibration point, EUR (CAPRI's 2030 money) per t
  slope_capri     p_mPoolSupSlope = p_manPointSupElas x supply_t / dual_cal_eur_t, p_manPointSupElas = 0.01 (l. 496):
                  CAPRI's number, used by CAPRI with the excess supply in kt (v_netPutQuant, v_manureExports: 1000 t,
                  supply_model.gms e_netMTrade) and prices in EUR per t - so its excess supply responds 1000 times more
                  than the elasticity 0.01 written (supply in t, quantities in kt; docs/dev/MANURE_POOL_PORT.md)
  es_slope        slope_capri in the model's units: excess supply in t per EUR 1000 (the model's 2017 money) per t,
                  slope_capri x 1000 (kt to t) x 1000 (EUR to EUR 1000) x deflator(2030) (tools/lib/_money.py, K108)
  dual_cal        dual_cal_eur_t in the model's units, EUR 1000 (2017 money) per t: the market model's fall-back value
  base_net_export_kt  p_priorMTrade(r, "postMode", FOUT, 2030): the region's net manure export at the calibration point,
                  kt (CAPRI's p_excessSupplyFromSupMod, l. 274-275); summed by pool it gives the links CAPRI's calibration
                  uses (from the pools that export to those that import)
  base_export_kt, base_import_kt  p_manureExports, p_manureImports(r, FOUT, 2030): the region's gross manure exports and
                  imports at the calibration point, kt (the lower bounds of the regional model's trade changes: a region
                  can cut its exports or imports to zero)
  sell_slope, buy_slope  p_manureSellCostSlope, p_manureBuyCostSlope (supply/define_manure_trade_costs.gms l. 66-71:
                  50 / (GROF / 100), EUR per t per kt traded) in the model's units: EUR 1000 (2017 money) per t per t
  open_export, open_import  for a region that does not export (import) at the calibration point, what its first t of
                  exports (imports) costs beyond its manure value at the calibration point, in the model's units
                  (EUR 1000, 2017 money, per t): CAPRI's calibrated constant p_manureSellCostConst (BuyCostConst),
                  MAX(10, the pool price less (more) the region's dual) for such a region (FINALIZE, l. 160-185),
                  less the gap it closes, p_manurePoolPrice - p_dualValueManureCal (the reverse for imports); zero where
                  the region trades that way at the calibration point (its constant is calibrated to its trade, l.
                  187-206). An importer with a dual of 297 EUR per t (ES410000, N) starts to export once its manure
                  value falls 307 EUR per t, an exporter's imports respond from the calibration point on
  buffer, buffer_greendeal  p_mTradeAutarkyBuffer of the region's pool in the model's units (EUR 1000, 2017 money, per
                  t): CAPRI's 10 EUR per t, and in the Green Deal group 50,000 for its isolated pools (UK, MT, NO, CS, AL,
                  MO, BA, MK, KO, TUR, CY; l. 401-420), added to the trade cost of the links unused at the calibration
                  point (p_mTradeAddCost, l. 425-436)
CAPRI's trade cost terms (p_manureSellCost*, p_manureBuyCost*) enter the regional NLP (capri_mod/supply/land.py: the
slopes, the opening costs above; the constants of the trade at the calibration point follow from the model's own base
calibration, as CAPRI's FINALIZE takes them from the duals). Not taken from these files: the fixed exports to third countries
(p_manureExportsToThirdCountries, l. 142): the model clears the deviations from CAPRI's base trade, which holds them
(and the files give none by region, only EU totals of 2010-2018).

The rows the builder needs are kept in capri_data/sources/raw/capri/results/fert/manure_pool_inputs_2030.parquet, so
it rebuilds without the raw files.

    python tools/build/build_manure_pool_market.py [--parquet DIR | --download]
        DIR: a copy of the raw dataset's capri/ folder; --download: from the raw dataset (Hugging Face);
        neither: from the kept extract
Output: capri_data/baselines/capri_greendeal_ref/1730/environment/manure_pool_market_2030.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import BASELINE_DATA  # noqa: E402
from _sources_io import read_source, write_source  # noqa: E402  (capri_data/sources: Parquet)
import _money  # noqa: E402

OUT = BASELINE_DATA / "environment" / "manure_pool_market_2030.csv"
KEEP = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "fert" / "manure_pool_inputs_2030.parquet"
#: manuremarket/declare_manure_market.gms l. 496
POINT_SUP_ELAS = 0.01
#: kt to t and EUR to EUR 1000: CAPRI's pool quantities in kt, prices in EUR per t; the model's in t and EUR 1000 per t
KT_TO_T = 1000.0
EUR_TO_KEUR = 1000.0
#: sets.gms FOUT_T_N
FOUT_T_N = {"MANN": "NITF", "MANP": "PHOF", "MANK": "POTF"}
SIMY = "2030"
SYMBOLS = ["p_priFertDist", "p_dualValueManureCal", "p_priorMTrade", "p_manureExports", "p_manureImports",
           "p_manureSellCostConst", "p_manureBuyCostConst", "p_manureSellCostSlope", "p_manureBuyCostSlope",
           "p_manurePoolPrice"]
#: items of the kept extract read from the cost and trade symbols: (symbol, item)
COST_ITEMS = (("p_manureSellCostConst", "sell_const"), ("p_manureBuyCostConst", "buy_const"),
              ("p_manureSellCostSlope", "sell_slope"), ("p_manureBuyCostSlope", "buy_slope"))
#: manuremarket/declare_manure_market.gms l. 418, 420: the autarky buffer (EUR per t, CAPRI's 2030 money), and the
#: isolated pools' in the Green Deal group
AUTARKY_BUFFER = 10.0
AUTARKY_BUFFER_ISOLATED_GREENDEAL = 50000.0
#: l. 404-414: CAPRI's isolated pools (in the Green Deal group), by the regions' code prefix (TUR: TR)
ISOLATED = ("UK", "MT", "NO", "CS", "AL", "MO", "BA", "MK", "KO", "TR", "CY")
REPO = "nuvolaTeam/capri-mod-raw"


def _folders(parquet: Path | None, download: bool):
    if parquet is not None:
        return sorted((parquet / "results" / "fert").glob("priFertDist_*1730defaulta"))
    if not download:
        return []
    from huggingface_hub import snapshot_download
    p = snapshot_download(REPO, repo_type="dataset",
                          allow_patterns=[f"capri/results/fert/priFertDist_*1730defaulta/{s}.parquet" for s in SYMBOLS])
    return sorted((Path(p) / "capri" / "results" / "fert").glob("priFertDist_*1730defaulta"))


def _extract(folders) -> pd.DataFrame:
    """CAPRI's records the builder uses, one row per region, FOUT and item (supply_t, dual_cal_eur_t,
    base_net_export_kt)."""
    rows = []
    for f in folders:
        pf = pd.read_parquet(f / "p_priFertDist.parquet")
        pf = pf[(pf.d2.str.lower() == "postmode") & (pf.d3.str.upper() == "EXCR") & (pf.d6 == SIMY)]
        sup = pf.groupby(["d1", "d4"]).value.sum()
        du = pd.read_parquet(f / "p_dualValueManureCal.parquet")
        pm = pd.read_parquet(f / "p_priorMTrade.parquet")
        pm = pm[(pm.d2 == "postMode") & (pm.d4 == SIMY)]
        net = {(r, fo): float(v) for r, fo, v in zip(pm.d1, pm.d3, pm.value)}
        gross = {}
        for sym, it in (("p_manureExports", "base_export_kt"), ("p_manureImports", "base_import_kt")):
            g_ = pd.read_parquet(f / f"{sym}.parquet")
            g_ = g_[g_.d3 == SIMY]
            gross.update({(r, fo, it): float(v) for r, fo, v in zip(g_.d1, g_.d2, g_.value)})
        cst = {}
        for sym, it in COST_ITEMS:
            c_ = pd.read_parquet(f / f"{sym}.parquet")
            cst.update({(r, fo, it): float(v) for r, fo, v in zip(c_.d1, c_.d2, c_.value)})
        pp_ = pd.read_parquet(f / "p_manurePoolPrice.parquet")
        # the member state's pool price at the calibration point (one member state per file; Turkey's file names it
        # TU, its regions TR)
        pool = {fo: float(v) for fo, y_, v in zip(pp_.d2, pp_.d3, pp_.value) if y_ == "Y"}
        if len(set(pp_.d1)) != 1:
            raise SystemExit(f"{f.name}: p_manurePoolPrice of {sorted(set(pp_.d1))}, one member state expected")
        for r, fo, v in zip(du.d1, du.d2, du.value):
            rows.append([r, fo, "dual_cal_eur_t", float(v)])
            rows.append([r, fo, "supply_t", float(sup.get((r, FOUT_T_N[fo]), 0.0))])
            rows.append([r, fo, "base_net_export_kt", net.get((r, fo), 0.0)])
            for it in ("base_export_kt", "base_import_kt"):
                rows.append([r, fo, it, gross.get((r, fo, it), 0.0)])
            for _, it in COST_ITEMS:
                if (r, fo, it) not in cst:
                    raise SystemExit(f"{f.name}: no {it} for {r} {fo}")
                rows.append([r, fo, it, cst[(r, fo, it)]])
            if fo not in pool:
                raise SystemExit(f"{f.name}: no p_manurePoolPrice for {fo}")
            rows.append([r, fo, "pool_price_cal", pool[fo]])
    return pd.DataFrame(rows, columns=["capri_region", "fout", "item", "value"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", type=Path, default=None)
    ap.add_argument("--download", action="store_true")
    a = ap.parse_args()
    folders = _folders(a.parquet, a.download)
    if folders:
        ex = _extract(folders)
        KEEP.parent.mkdir(parents=True, exist_ok=True)
        write_source(ex, KEEP, index=False)
        print(f"extracted {len(ex)} rows from {len(folders)} files -> {KEEP.relative_to(ROOT)}")
    src = read_source(KEEP)
    v = {(r, fo, it): float(x) for r, fo, it, x in zip(src.capri_region, src.fout, src["item"], src.value)}
    money = _money.deflator(int(SIMY))
    rows = []
    for (r, fo, it) in sorted(k for k in v if k[2] == "dual_cal_eur_t"):
        d_ = v[(r, fo, it)]
        if not d_:
            # CAPRI aborts on a zero calibration dual (declare_manure_market.gms l. 501-505)
            raise SystemExit(f"{r} {fo}: zero calibration dual, CAPRI's slope undefined")
        s_ = v.get((r, fo, "supply_t"), 0.0)
        b = POINT_SUP_ELAS * s_ / d_
        buf = AUTARKY_BUFFER / EUR_TO_KEUR / money
        buf_gd = (AUTARKY_BUFFER_ISOLATED_GREENDEAL if r[:2] in ISOLATED else AUTARKY_BUFFER) / EUR_TO_KEUR / money
        # the opening cost of a trade direction the region does not use at the calibration point (FINALIZE): its
        # calibrated constant less the gap between the pool price and its dual it closes; zero where it trades so
        ex_, im_ = v[(r, fo, "base_export_kt")], v[(r, fo, "base_import_kt")]
        gap = v[(r, fo, "pool_price_cal")] - d_                    # pool price - dual, EUR per t
        o_e = 0.0 if ex_ > 0 else v[(r, fo, "sell_const")] - gap
        o_i = 0.0 if im_ > 0 else v[(r, fo, "buy_const")] + gap
        if o_e < -1e-6 or o_i < -1e-6:
            raise SystemExit(f"{r} {fo}: a negative opening cost ({o_e:.6g}, {o_i:.6g}): not CAPRI's calibration")
        per_t = KT_TO_T * EUR_TO_KEUR * money                     # EUR per t per kt -> EUR 1000 (2017) per t per t
        rows.append([r, fo, s_, d_, b, b * KT_TO_T * EUR_TO_KEUR * money, d_ / EUR_TO_KEUR / money,
                     v.get((r, fo, "base_net_export_kt"), 0.0), buf, buf_gd, ex_, im_,
                     v[(r, fo, "sell_slope")] / per_t, v[(r, fo, "buy_slope")] / per_t,
                     max(o_e, 0.0) / EUR_TO_KEUR / money, max(o_i, 0.0) / EUR_TO_KEUR / money])
    if not rows:
        raise SystemExit("no records")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["region", "fout", "supply_t", "dual_cal_eur_t", "slope_capri", "es_slope", "dual_cal",
                    "base_net_export_kt", "buffer", "buffer_greendeal", "base_export_kt", "base_import_kt",
                    "sell_slope", "buy_slope", "open_export", "open_import"])
        w.writerows(rows)
    print(f"{OUT.relative_to(ROOT)}: {len(rows)} records (deflator {money:.6f})")


if __name__ == "__main__":
    main()
