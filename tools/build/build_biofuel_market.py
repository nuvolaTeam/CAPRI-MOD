"""CAPRI's biofuel markets: feedstock demand, biofuel supply and biofuel demand, per CAPRI market region.

CAPRI's market model (arm/market_model.gms) holds first-generation biofuel processing inside the market. Its
four feedstock equations hold in every run:

  biofFeedCost_    mu_f   = Arm1 price of feedstock f - PRCBY_f x by-product price  (per t of feedstock)
  biofFeedCostAgg_ mu_b   = CES aggregate of the mu_f of the feedstocks of biofuel b  (per t of biofuel)
  Biof_            q_f    = dpCES_f x X_b x (mu_b / mu_f)^rho_b      (every feedstock but the numeraire)
  prodBiof_        X_b    = sum_f q_f x PRCB_f                         (fixes the numeraire's quantity)

with rho_b = 4 (arm/market1.gms p_rhoBioFuel). With endogenous biofuel markets (BIOF_M = ON, the star 3.0 GUI
default; arm/prep_market.gms p_endoBioMarket = 1) biofuels are traded market products and X_b is endogenous:

  SupplyBiof_   X_b = scale x PR + exp(alfa + beta log(PR + 0.01)) x SIGMOID(slope (PR - turn)),
                PR = biofPriceRel = producer price / mu_b                   (biofPriceRel_)
  MaprBiof_     production = X_b + NAGR + SECG + EXOG                       (non-agricultural, second
                                                                              generation, exogenous: fixed)
  biofDemShare_ share = QUTS + MAX x SIGMOID(Slope (consumer price / fossil fuel price - Turn))
  biofDem_      BIOF = share / oilEqu_b x fossil fuel use (HCON, oil equivalents)
  Cpri_         consumer price = Arm1 price + CTAX + CMrg - CSE              (additive margins)

calibrated to the reference point as biofuel/def_biofuel_params.gms does:
  supply  turn = 0.9 PR0; slope = 8 / PR0 in the member states with a supply model (RMSSUP = NUTS0: EU,
          UK, Norway, Western Balkans, Turkey), 5 / PR0 elsewhere and where X0 < 50 kt, 5 / PR0 for German
          biodiesel, 1 / PR0 for Japanese ethanol; beta = 0.5; scale = min(0.1, 0.1 X0 / PR0); alfa so that
          X(PR0) = X0
  demand  CalShare = BIOF oilEqu_b / (HCON oilEqu_f); CalShare-Quot = CalShare - QUTS;
          MAX = min(1, max(0.02 + CSQ, 1.1 CSQ)) (Brazilian ethanol: 1 - QUTS); 90% of MAX (at least
          1.03 CSQ / MAX) at a price relation of min(0.5, 0.5 PriceRel) (biodiesel: min(0.3, 0.3 PriceRel));
          Slope and Turn solved so the sigmoid runs through (PriceRel, CSQ)
  p_oilEqu: DISL, GASL 1.027; BIOD 0.884; BIOE 0.645 toe per t (arm/market_model.gms)

Non-fuel use of ethanol (PROC) follows CAPRI's processing function ProcNQ_:
  PROC = cnst + sum_y p_hessNQProc(b, y) (Arm1 price_y - PRCA_y) / INPE price
with only the own term for BIOE in CAPRI's Hessian (elas_2_1730defaulta p_hessNQProc, CAL); INPE's price 1.277
(dump PPRI INPE). Columns proc_kt, proc_hess, inpe.

DDGS output = sum over the cereal feedstocks of BIOF x PRCBY (prodQuantBiofBy_); checked against CAPRI's PROD DDGS.

Source, per market year: CAPRI's market data of the year (dataOut of the market model's calibration point) -
2017: market_base_1717 (base year 2017 calibrated from data), with p_hessNQProc of elas_2_1717defaulta;
2030: the 2030 Green Deal reference market results (markmarket_greendeal_1730et_base_1717), with elas_2_1730defaulta.
Until 30 October 2026 only the 2030 files existed and a 2017 market ran with CAPRI's 2030 biofuel output (Argentina's
biodiesel 1,862 kt against 2,819 in 2017; KNOWN_ISSUES K106). Every CAPRI market region (RMS): BIOF (feedstock to biofuels; biofuel use), PRCB, PRCBY, ARM1P, PPRI, CPRI, PROD,
NAGR, SECG, EXOG, QUTS (%), BiofFeedCost, HCOM of gasoline and diesel, CPRI of gasoline and diesel.
The dump's HCOM of the fossil fuels is the FOSSIL part; CAPRI's HCON in the calibration is total fuel use
(fossil + biofuel in fossil equivalents): HCON = HCOM + BIOF oilEqu_b / oilEqu_f, which reproduces CAPRI's
data_market_1730defaulta HCON (CAL) and its HCOS share. The rows used are kept as
capri_data/sources/market/biofuel_dataout_<YEAR>.csv.xz.

Feedstock -> model market commodity: WHEA -> SWHE, BARL -> BARL, MAIZ -> CORN, RYEM, OATS, OCER as themselves,
SUGA -> SUGR, TWIN -> WINE, RAPO/SUNO/SOYO -> themselves; palm oil PLMO and other vegetable oils OTHO -> themselves
(markets since October 2026; before, no model market and the price held at the 2030 reference). By-products: DDGS at the region's DDGS producer price, glycerine 600 EUR/t
(arm/store_prices.gms); both held at the reference (no DDGS market in the model; REGISTERED).

CAPRI market regions -> model trade regions: EU member states -> EU27 (CAPRI's trade block EU27yr19);
the regions of tools/build/recalibrate_trade_2017.REGION_MAP by name; the rest -> ROW. CAPRI's trade-only blocks
(EU27yr19, URUPAR, WBA, MER_OTH, MED) and reporting aggregates carry no functions of their own.

Outputs (capri_data/2017/market/, one set per market year <YEAR>)
  biofuel_feedstock_<YEAR>.csv   ms (CAPRI region), region (model), biofuel, feedstock, commodity, biof_kt, prcb,
                          prcby, byproduct, feed_price, byproduct_price, rho, numeraire
  biofuel_use_share_<YEAR>.csv   commodity, biof_kt, use_kt, share  (EU27: use = HCOM + FEDM + INDM + BIOF + LOSM of
                          the group, CAPRI's EU aggregate EU27yr19 in the same dump)
  biofuel_market_<YEAR>.csv      ms, region, biofuel, rmssup, prod_kt, x0_kt, fixed_kt, ppri, pmrk, bfc, pr0,
                          sup_scale, sup_alfa, sup_beta, sup_slope, sup_turn, biof_kt, cpri, arm1p,
                          fossil_cpri, hcon_kt, oil_eq, oil_eq_fossil, quts, cal_share, dem_max, dem_slope,
                          dem_turn

    python tools/build/build_biofuel_market.py --year 2017 --dump market_base_1717.txt --elas elas_2_1717defaulta.csv
    python tools/build/build_biofuel_market.py --year 2030 --dump markmarket_greendeal_1730et_base_1717.txt \
        --elas elas_2_1730defaulta.csv
"""
from __future__ import annotations
import argparse, math, re, subprocess, sys
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "capri_data" / "sources" / "market"
DEST = ROOT / "capri_data" / "2017" / "market"
FUEL = {"BIOE": ("WHEA", "BARL", "MAIZ", "RYEM", "OATS", "OCER", "SUGA", "TWIN"),
        "BIOD": ("RAPO", "SUNO", "SOYO", "PLMO", "OTHO")}
FOSSIL = {"BIOE": "GASL", "BIOD": "DISL"}                                    # arm_sets.gms fuelMatch
OIL_EQ = {"DISL": 1.027, "GASL": 1.027, "BIOD": 0.884, "BIOE": 0.645}       # market_model.gms p_oilEqu
BYPROD = {**{f: "DDGS" for f in ("WHEA", "BARL", "MAIZ", "RYEM", "OATS", "OCER")},
          **{f: "GLYC" for f in ("RAPO", "SUNO", "SOYO", "PLMO", "OTHO")}}          # sets.gms STOCK_TO_BY
COMMODITY = {"WHEA": "SWHE", "BARL": "BARL", "MAIZ": "CORN", "RYEM": "RYEM", "OATS": "OATS", "OCER": "OCER",
             "SUGA": "SUGR", "TWIN": "WINE", "RAPO": "RAPO", "SUNO": "SUNO", "SOYO": "SOYO",
             "PLMO": "PLMO", "OTHO": "OTHO"}
GROUPS = {"SWHE": ("SWHE",), "BARL": ("BARL",), "CORN": ("MAIZ",), "OCER": ("OCER",), "RYEM": ("RYEM",), "OATS": ("OATS",),
          "SUGR": ("SUGA",), "WINE": ("TWIN",), "RAPO": ("RAPO",), "SUNO": ("SUNO",), "SOYO": ("SOYO",),
          "PLMO": ("PLMO",), "OTHO": ("OTHO",)}
GLYC_PRICE = 600.0                           # arm/store_prices.gms
RHO = 4.0                                    # arm/market1.gms: p_rhoBioFuel(RMS,XXBioF) = 4
ITEMS = ("BIOF", "PRCB", "PRCBY", "ARM1P", "PPRI", "PMRK", "UVAP", "CPRI", "PROD", "NAGR", "SECG", "EXOG",
         "QUTS", "HCOM", "BiofFeedCost", "PROC", "FEDM", "INDM", "LOSM")
PRODS = set(BYPROD) | {"BIOE", "BIOD", "DDGS", "GLYC", "SUGA", "TWIN", "GASL", "DISL", "INPE", "SWHE"}

#: CAPRI's trade-only blocks (aggregates of market regions) - no behavioural functions of their own
TRADE_BLOCKS = {"EU27yr19", "URUPAR", "WBA", "MER_OTH", "MED"}
#: aggregates in CAPRI's 2017 market data that recalibrate_trade_2017.AGGREGATES does not list (RW: the rest of the
#: world, reported with world-scale biofuel output)
MORE_AGGREGATES = {"RW"}
EU_MS = {"BL000000", "SE000000", "DK000000", "DE000000", "EL000000", "ES000000", "FR000000", "IR000000",
         "IT000000", "NL000000", "AT000000", "PT000000", "FI000000", "CY000000", "EE000000", "LV000000",
         "LT000000", "MT000000", "PL000000", "SK000000", "BG000000", "CZ000000", "HU000000", "SI000000",
         "RO000000", "HR000000"}


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def extract(dump: Path, year: str) -> pd.DataFrame:
    pat = re.compile(r"^'([^']+)'\.''\.'(" + "|".join(ITEMS) + r")'\.'([A-Z]+)'\.'" + year + r"'\s+([-\d.Ee+]+)")
    txt = subprocess.run(["grep", "-E", r"^'[^']+'\.''\.'(" + "|".join(ITEMS) + r")'\.'(" + "|".join(sorted(PRODS))
                          + r")'\.'" + year + "'", str(dump)], capture_output=True, text=True).stdout
    rows = []
    for line in txt.splitlines():
        m = pat.match(line)
        if m and m.group(3) in PRODS:
            rows.append({"region": m.group(1), "item": m.group(2), "product": m.group(3), "value": float(m.group(4))})
    return pd.DataFrame(rows)


def is_rms(r: str, aggregates) -> bool:
    """A CAPRI market region with its own behavioural functions (not a NUTS2 region, aggregate or trade block)."""
    if r in aggregates or r in TRADE_BLOCKS or r in MORE_AGGREGATES or r.startswith(("EU0", "EU_", "A_EU")) or r == "EU":
        return False
    return not (len(r) == 8 and r[2:].isalnum() and not r.endswith("000000"))


def model_region(r: str, region_map) -> str:
    return "EU27" if r in EU_MS else region_map.get(r, "ROW")


def calibrate_supply(ms, fuel, X0, PR0, rmssup):
    """biofuel/def_biofuel_params.gms 'Calibrate biofuel supply system'."""
    turn = 0.9 * PR0
    slope = (8.0 if rmssup else 5.0) / PR0
    if X0 < 50:
        slope = 5.0 / PR0
    if ms == "DE000000" and fuel == "BIOD":
        slope = 5.0 / PR0
    if ms == "JAP" and fuel == "BIOE":
        slope = 1.0 / PR0
    beta = 0.5
    scale = min(0.1, 0.1 * X0 / PR0)
    alfa = math.log((X0 - scale * PR0) / sigmoid(slope * (PR0 - turn))) - beta * math.log(PR0 + 1e-2)
    test = scale * PR0 + math.exp(alfa + beta * math.log(PR0 + 1e-2)) * sigmoid(slope * (PR0 - turn))
    assert abs(test - X0) < 1e-6 * max(1.0, X0), (ms, fuel, test, X0)
    return dict(sup_scale=scale, sup_alfa=alfa, sup_beta=beta, sup_slope=slope, sup_turn=turn)


def calibrate_demand(ms, fuel, cal_share, quts, price_rel):
    """biofuel/def_biofuel_params.gms 'Calibrate biofuel demand system' (sigmoid part above QUTS)."""
    csq = cal_share - quts
    if csq <= 0 or price_rel <= 0:
        return dict(dem_max=0.0, dem_slope=0.0, dem_turn=0.0)
    mx = min(1.0, max(0.02 + csq, 1.10 * csq))
    if ms == "BRA" and fuel == "BIOE":
        mx = 1.0 - quts
    pom = max(0.9, csq / mx * 1.03)
    prm = min(0.5, price_rel * 0.5) if fuel == "BIOE" else min(0.3, price_rel * 0.3)
    slope = (math.log(1.0 / (csq / mx) - 1.0) - math.log(1.0 / pom - 1.0)) / (prm - price_rel)
    turn = (math.log(1.0 / (csq / mx) - 1.0) + price_rel * slope) / slope
    test = quts + sigmoid(slope * (price_rel - turn)) * mx
    assert abs(test - cal_share) < 1e-9, (ms, fuel, test, cal_share)
    return dict(dem_max=mx, dem_slope=slope, dem_turn=turn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["2017", "2030"])
    ap.add_argument("--dump", type=Path, required=True)
    ap.add_argument("--elas", type=Path, required=True)
    a = ap.parse_args()
    SRC = SRC_DIR / f"biofuel_dataout_{a.year}.csv.xz"
    HESS = SRC_DIR / f"biofuel_proc_hessian_{a.year}.csv"
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    from recalibrate_trade_2017 import REGION_MAP, AGGREGATES
    if a.dump.exists():
        src = extract(a.dump, a.year)
        # the market regions, and the EU aggregate EU27yr19 for the EU's use of the feedstocks (biofuel_use_share)
        src = src[src.region.map(lambda r: is_rms(r, AGGREGATES)) | (src.region == "EU27yr19")]
        SRC.parent.mkdir(parents=True, exist_ok=True)
        src.to_csv(SRC, index=False)
        print(f"extracted {len(src)} rows -> {SRC.relative_to(ROOT)}")
    if a.elas.exists():
        # p_hessNQProc rows of the biofuels (own and cross terms, CAL)
        txt = open(a.elas, errors="ignore").read()
        i = txt.index("Parameter p_hessNQProc")
        j = txt.index("Parameter ", i + 10)
        pat = re.compile(r"^'([^']+)'\.'(BIOE|BIOD)'\.'([^']+)'\.'CAL'\s+([-\d.Ee+]+)", re.M)
        hrows = [dict(region=m.group(1), product=m.group(2), price_of=m.group(3), value=float(m.group(4)))
                 for m in pat.finditer(txt[i:j])]
        pd.DataFrame(hrows).to_csv(HESS, index=False)
        print(f"extracted {len(hrows)} p_hessNQProc rows -> {HESS.relative_to(ROOT)}")
    hs = _read_csv(HESS)
    assert (hs["product"] == hs["price_of"]).all(), "cross terms in CAPRI's biofuel processing Hessian: extend the model"
    hess = {(r.region, r.product): r.value for r in hs.itertuples()}
    src = _read_csv(SRC)
    v = {(r.region, r.item, r.product): r.value for r in src.itertuples()}
    regions = sorted({r for r in src.region if is_rms(r, AGGREGATES)})

    # ---- feedstock groups (biofFeedCost_, biofFeedCostAgg_, Biof_, prodBiof_)
    frows, checks, x0 = [], [], {}
    for ms in regions:
        for fuel, stocks in FUEL.items():
            recs = []
            for f in stocks:
                q, prcb = v.get((ms, "BIOF", f), 0.0), v.get((ms, "PRCB", f), 0.0)
                if not (q > 0 and prcb > 0):                  # CAPRI: DATA(BIOF) $ DATA(PRCB)
                    continue
                by = BYPROD.get(f)
                # DDGS: CAPRI's producer price; glycerine: fixed at 600 EUR/t in CAPRI itself
                # (arm/store_prices.gms PPRI.GLYC = 600, v_prodPrice.fx in arm/set_start_val.gms)
                pby = (GLYC_PRICE if by == "GLYC" else v.get((ms, "PPRI", by), 0.0)) if by else 0.0
                recs.append({"ms": ms, "region": model_region(ms, REGION_MAP), "biofuel": fuel, "feedstock": f,
                             "commodity": COMMODITY.get(f, ""), "biof_kt": q, "prcb": prcb,
                             "prcby": v.get((ms, "PRCBY", f), 0.0) if by else 0.0,
                             "byproduct": by or "", "feed_price": v.get((ms, "ARM1P", f), float("nan")),
                             "byproduct_price": pby, "rho": RHO})
            if not recs:
                continue
            top = max(recs, key=lambda r: r["biof_kt"])        # def_biofuel_params.gms BIOF_NUM: largest BIOF
            for r in recs:
                r["numeraire"] = int(r is top)
            mu = [r["feed_price"] - r["prcby"] * r["byproduct_price"] for r in recs]
            if any(not (m > 0) for m in mu):                 # no CES without positive feedstock costs
                # CAPRI's data never have it (biofFeedCost_ needs it); until 30 October 2026 such a group was left
                # out without a word: a data inconsistency to look at, not a group to drop
                raise ValueError(f"{ms} {fuel}: a feedstock cost net of its by-product is not positive "
                                 f"({', '.join(r['feedstock'] for r, m in zip(recs, mu) if not m > 0)})")
            frows += recs
            X = sum(r["biof_kt"] * r["prcb"] for r in recs)
            mub = sum(r["biof_kt"] * m for r, m in zip(recs, mu)) / X
            x0[(ms, fuel)] = (X, mub)
            checks.append((ms, fuel, X, mub, v.get((ms, "BiofFeedCost", fuel))))
    fs = pd.DataFrame(frows)
    fs.to_csv(DEST / f"biofuel_feedstock_{a.year}.csv", index=False)

    eu = fs[fs.region == "EU27"]
    us = []
    for c, grp in GROUPS.items():
        # the EU's use of the group: CAPRI's EU aggregate EU27yr19 in the same dump and year
        use = sum(v.get(("EU27yr19", k, x), 0.0) for x in grp for k in ("HCOM", "FEDM", "INDM", "BIOF", "LOSM"))
        q = float(eu.loc[eu["commodity"] == c, "biof_kt"].sum())
        us.append({"commodity": c, "biof_kt": q, "use_kt": use, "share": q / use if use > 0 else 0.0})
    pd.DataFrame(us).to_csv(DEST / f"biofuel_use_share_{a.year}.csv", index=False)

    # ---- biofuel supply and demand functions
    mrows = []
    for ms in regions:
        rmssup = ms.endswith("000000") or ms == "TUR"                      # sets.gms RMSSUP = NUTS0
        for fuel in FUEL:
            prod = v.get((ms, "PROD", fuel), 0.0)
            use = v.get((ms, "BIOF", fuel), 0.0)
            proc = v.get((ms, "PROC", fuel), 0.0)
            if prod <= 0 and use <= 0 and proc <= 0:
                continue
            fos = FOSSIL[fuel]
            X0, mub = x0.get((ms, fuel), (0.0, 0.0))
            fixed = sum(v.get((ms, k, fuel), 0.0) for k in ("NAGR", "SECG", "EXOG"))
            ppri = v.get((ms, "PPRI", fuel), 0.0)
            row = dict(ms=ms, region=model_region(ms, REGION_MAP), biofuel=fuel, rmssup=int(rmssup),
                       prod_kt=prod, x0_kt=X0, fixed_kt=fixed, ppri=ppri, pmrk=v.get((ms, "PMRK", fuel), 0.0),
                       bfc=mub, pr0=0.0, sup_scale=0.0, sup_alfa=0.0, sup_beta=0.0, sup_slope=0.0, sup_turn=0.0)
            # SupplyBiof_ needs a biofuel price relation and feedstocks
            if X0 > 0 and ppri > 0 and mub > 0:
                row["pr0"] = ppri / mub
                row.update(calibrate_supply(ms, fuel, X0, row["pr0"], rmssup))
            # biofDem_: fossil fuel use and price
            hcom = v.get((ms, "HCOM", fos), 0.0)
            cpri, cf = v.get((ms, "CPRI", fuel), 0.0), v.get((ms, "CPRI", fos), 0.0)
            hcon = hcom + use * OIL_EQ[fuel] / OIL_EQ[fos]
            cal = use * OIL_EQ[fuel] / (hcon * OIL_EQ[fos]) if hcon > 0 else 0.0
            quts = v.get((ms, "QUTS", fuel), 0.0) / 100.0
            row.update(biof_kt=use, cpri=cpri, arm1p=v.get((ms, "ARM1P", fuel), 0.0), fossil_cpri=cf,
                       hcon_kt=hcon, oil_eq=OIL_EQ[fuel], oil_eq_fossil=OIL_EQ[fos], quts=quts, cal_share=cal)
            row.update(calibrate_demand(ms, fuel, cal, quts, cpri / cf if cf > 0 and cpri > 0 else 0.0)
                       if (use > 0 and hcom > 0) else dict(dem_max=0.0, dem_slope=0.0, dem_turn=0.0))
            # non-fuel processing (ProcNQ_, own term)
            row.update(proc_kt=proc, proc_hess=hess.get((ms, fuel), 0.0) if proc > 0 else 0.0,
                       inpe=v.get((ms, "PPRI", "INPE"), 0.0))
            mrows.append(row)
    mk = pd.DataFrame(mrows)
    mk.to_csv(DEST / f"biofuel_market_{a.year}.csv", index=False)

    print(f"biofuel_feedstock_{a.year}.csv: {len(fs)} rows, {fs.ms.nunique()} CAPRI regions")
    print(f"biofuel_market_{a.year}.csv: {len(mk)} rows; supply functions {int((mk.pr0 > 0).sum())}, "
          f"demand functions {int((mk.dem_slope != 0).sum())}")
    print("by model region (kt): production, of which first generation; use")
    print(mk.groupby(["biofuel", "region"])[["prod_kt", "x0_kt", "biof_kt"]].sum().round(0).to_string())
    # DDGS output (prodQuantBiofBy_) against CAPRI's PROD DDGS
    dd = fs[fs.byproduct == "DDGS"].assign(q=lambda d: d.biof_kt * d.prcby).groupby("ms")["q"].sum()
    worst = max(((abs(q / v[(ms, "PROD", "DDGS")] - 1), ms) for ms, q in dd.items()
                 if v.get((ms, "PROD", "DDGS"), 0.0) > 10), default=(0.0, ""))
    print(f"DDGS output sum BIOF x PRCBY: {dd.sum():.0f} kt, CAPRI PROD {sum(v.get((m, 'PROD', 'DDGS'), 0.0) for m in dd.index):.0f}; "
          f"worst region {worst[1]} {worst[0]:.2%}")
    print(f"non-fuel ethanol processing: {mk.proc_kt.sum():.0f} kt in {int((mk.proc_kt > 0).sum())} regions, "
          f"own-price slope from CAPRI's Hessian in {int((mk.proc_hess != 0).sum())}")
    print("feedstock cost per t biofuel, sum q mu / X vs CAPRI BiofFeedCost (largest producers):")
    for ms, fuel, X, mu, bfc in sorted(checks, key=lambda t: -t[2])[:10]:
        print(f"  {ms} {fuel}: X {X:7.0f} kt  mu {mu:7.1f}  CAPRI {bfc if bfc is None else round(bfc, 1)}")


if __name__ == "__main__":
    main()
