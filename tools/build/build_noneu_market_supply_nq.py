"""CAPRI's market supply functions of the regions outside the EU (arm/market_model.gms ProdNQ_, l. 1529-1572): the
normalised-quadratic supply of every non-EU CAPRI market region, own and cross-price terms, from CAPRI's own terms
(market audit, programme step D: "non-EU supply in CAPRI's NQ form", KNOWN_ISSUES K54-3).

ProdNQ_: v_prodQuant(RMS, x) = p_cnstNQSupp + sum_y p_hessNQSupp(RMS, x, y) x v_prodPrice(RMS, y) / v_prodPrice(RMS,
"INPE") (+ the feed-bulk price terms, which CAPRI's 2030 Hessian does not carry for any region). The change from the
calibration point is sum_y h_xy x (the change of y's producer price) / INPE. The producer price moves with the market
price by CAPRI's relative margin (PPri_, l. 3046-3060; the support items PSEi, PSEd, AREP are not in CAPRI's 2030
calibration data for these regions, so the margin is the whole price), so the change of y's producer price is
PPRI0_y x (y's price ratio - 1) and each term is written as h_xy x PPRI0_y / INPE: kt per unit change of y's price
ratio, the form of the EU's other oils and fish (build_eu_market_supply_nq.py) and of the market supply Hessian.
INPE is the price of the non-agricultural good in 2030 (1.2772 in every region, CAPRI's 2030 market dump, as
build_eu_market_supply_nq.py takes it); it does not move in a simulation.

Columns kept: the prices the model has for the region: its market products (the bilateral market's product map,
build_bilateral_market.MODEL), raw milk (the region's dairy block, capri_mod/market/dairy.py) and the rents of the land
inputs of CAPRI's market land use (TCRP land for temporary crops, FRUN for permanent crops, FODFAL fodder and fallow:
xx1Land, arm/arm_sets.gms l. 140-150), under their own codes, the land market's (build_land_market below; since
4 November 2026, before held at calibration). The young animals carry only a placeholder own term (1) in CAPRI's
export, no cross terms. Rows: every model market product, raw milk and the land types (their land demand, the rows'
sign turned as arm/market1.gms l. 593 does with supremaMrk on: the Hessian's rows were netputs); the FEDE row and the
young animals are left out. The feed energy price FEDE (CAPRI's
FeedBal_, market audit M3) is a column with model code FEDE and its CAPRI price at CAL from
tools/build/build_feed_energy.py (arm/market1.gms l. 406: not in Data_CAL's export); until 29 October 2026 held, written
with h_ratio 0.

The Hessian is completed as CAPRI's market model completes it on loading (tools/lib/_capri_nq.py, arm/market1.gms
l. 539-574): tiny cross terms deleted, products without ProdNQ_ deleted (for the regions with supply models in CAPRI,
here Norway, the UK, Turkey and the Western Balkans, also FPRI, FENI, FEDE), and made symmetric (the export stores
each cross term once, under one of the two products).

For the UK, Turkey and the Western Balkans CAPRI's supply is its supply models' (RMSSUP), the market's function being
recalibrated to them each iteration; the model has no supply models there (a registered difference), so their
function stays at CAPRI's calibration point, as for the regions without supply models.

Sources: CAPRI's NQ supply Hessian at the calibration point (elas_2_1730defaulta.csv: p_hessNQSupp at CAL), the
regions' producer prices and production there (data_market_1730defaulta.csv: Data_CAL PPRI, PROD at CAL), the 2030
price of the non-agricultural good (markmarket_greendeal_1730et_base_1717.txt: PPRI INPE 2030), CAPRI's market
regions (capri_data/shared/rms_to_rm.csv) and the model's trade regions (the market's grouping step,
tools/lib/_market_regions.py).

Output: capri_data/2017/market/noneu_market_supply_nq.csv
    trade_region, rms, x, y, capri_x, capri_y, h, ppri_y, inpe, h_ratio      (x, y model codes; y empty: held)
and the land market (build_land_market): capri_data/2017/market/noneu_land_market.csv, noneu_land_mnl.csv

    python tools/build/build_noneu_market_supply_nq.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from paths import EXPORTS  # noqa: E402  (CAPRI's material outside the repository)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from capri_mod.csvio import read_csv, to_csv  # noqa: E402

from _capri_nq import read_supply_hessian  # noqa: E402

UP = EXPORTS
ELAS = UP / "elas_2_1730defaulta.csv"
DATA = UP / "data_market_1730defaulta.csv"
DUMP = UP / "markmarket_greendeal_1730et_base_1717.txt"
RMS_TO_RM = ROOT / "capri_data" / "shared" / "rms_to_rm.csv"
UNITS = ROOT / "capri_data" / "sources" / "intermediate" / "capri_res" / "gd2030_endotech_ini_nbalance.csv"
OUT = ROOT / "capri_data" / "2017" / "market" / "noneu_market_supply_nq.csv"
FEED_ENERGY = ROOT / "capri_data" / "2017" / "market" / "noneu_feed_energy.csv"
LAND_OUT = ROOT / "capri_data" / "2017" / "market" / "noneu_land_market.csv"
MNL_OUT = ROOT / "capri_data" / "2017" / "market" / "noneu_land_mnl.csv"
#: CAPRI's land types of the MNL land supply (luEla, arm/arm_sets.gms) and the market's agricultural ones (luAgrMrk)
LU_ELA = ("FORE", "ARTIF", "OLND", "TCRP", "FODFAL", "FRUN")
#: CAPRI's EU market regions (trade blocks): their member states' supply is the supply models'
EU_RM = ("A_EU_WEST", "A_EU_EAST", "EU27yr19")


def num(s: str) -> float:
    s = s.rstrip(",").strip()
    return 0.0 if s.lower() in ("eps", "na", "undf", "") else float(s)


def read_param(path: Path, name: str, pat: re.Pattern, keep) -> list:
    out, cur = [], None
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            if line.startswith("Parameter"):
                cur = line.split("(")[0].split()[1]
                continue
            if cur != name or not line.startswith("'"):
                continue
            m = pat.match(line)
            if m and keep(m):
                out.append(m.groups())
    return out


def main():
    from _market_regions import model_region  # the market's grouping step (tools/lib/_market_regions.py)
    from build_bilateral_market import CAPRI as CAPRI_TO_MODEL       # CAPRI product -> model commodity
    to_model = dict(CAPRI_TO_MODEL)
    to_model["MILK"] = "MILK"                                        # raw milk: the region's dairy block
    # CAPRI's land types in ProdNQ_ (xx1Land: land demand as rows, rents as columns; the market's land block,
    # LndSupplyEqualsDemand_ and rentFromProdpriceLand_, stage 7 of the market move): kept under their own codes
    LAND = ("TCRP", "FODFAL", "FRUN")
    to_model.update({x: x for x in LAND})
    rm_of = dict(read_csv(RMS_TO_RM)[["rms", "rm"]].itertuples(index=False))
    noneu = {r for r, m in rm_of.items() if m not in EU_RM}

    # CAPRI's regions with supply models (RMSSUP) outside the EU: the countries of its supply-model units in the Green
    # Deal 2030 run (Norway, the UK, Turkey, the Western Balkans; Turkey's units TR..., its market region TUR)
    ctry = {str(u)[:2] for u in read_csv(UNITS)["region"].unique()}
    rmssup = {r for r in noneu if (r.endswith("000000") and r[:2] in ctry) or (r == "TUR" and "TR" in ctry)}
    hess = read_supply_hessian(ELAS, lambda r: r in noneu, rmssup)
    terms = sorted((r, x, y, h) for (r, x, y), h in hess.items() if x in to_model and y != "INPE")
    ep = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'CAL'\s+(\S+)")
    elas = {(r, x, y): num(v) for r, x, y, v in read_param(ELAS, "p_elasSupp", ep, lambda m: m.group(1) in noneu)}
    stored = {(r, x, y) for r, x, y, _ in read_param(ELAS, "p_hessNQSupp", ep, lambda m: m.group(1) in noneu)}
    dp = re.compile(r"^'([^']*)'\.'(PPRI|PROD)'\.'([^']*)'\.'CAL'\s+(\S+)")
    data = {(r, it, p): num(v) for r, it, p, v in read_param(DATA, "Data_CAL", dp, lambda m: m.group(1) in noneu)}
    inpe = {}
    p3 = re.compile(r"^'([^']+)'\.''\.'PPRI'\.'INPE'\.'2030'\s+(\S+)")
    with open(DUMP, encoding="latin-1") as fh:
        for line in fh:
            if "'PPRI'.'INPE'" in line:
                m = p3.match(line)
                if m:
                    inpe[m.group(1)] = num(m.group(2))

    # the feed energy price FEDE of the regions with CAPRI's feed energy balance (FeedBal_, audit M3;
    # tools/build/build_feed_energy.py: arm/market1.gms l. 406, not in Data_CAL's export)
    fede = {}
    if FEED_ENERGY.exists():
        fede = {t.rms: float(t.fede_price) for t in read_csv(FEED_ENERGY).itertuples(index=False)}
    rows, missing = [], set()
    held = defaultdict(float)
    for r, x, y, h in terms:
        if not inpe.get(r):
            missing.add((r, "INPE 2030"))
            continue
        p = data.get((r, "PPRI", y), 0.0) if y != "FEDE" else fede.get(r, 0.0)
        if not p:
            # a price CAPRI's calibration data does not carry for the region (FEDE: the feed energy balance's
            # shadow price; young animals priced at RM level): such a column is held, its term not usable
            held[y] += 0.0
            rows.append((model_region(rm_of[r]), r, to_model[x], "", x, y, h, 0.0, inpe[r], 0.0))
            continue
        ym = to_model.get(y, "") if y != "FEDE" else "FEDE"
        if x in LAND:
            # the land rows are input demands: CAPRI turns their sign on loading (arm/market1.gms l. 593, supremaMrk on;
            # the Hessian's rows were netputs in the elasticity calibration), after making the Hessian symmetric
            h = -h
        rows.append((model_region(rm_of[r]), r, to_model[x], ym, x, y, h, p, inpe[r], h * p / inpe[r]))
        if not ym:
            held[y] += abs(h * p / inpe[r])
    if missing:
        raise SystemExit(f"no CAPRI 2030 INPE for {sorted(missing)[:10]}")
    out = pd.DataFrame(rows, columns=["trade_region", "rms", "x", "y", "capri_x", "capri_y", "h", "ppri_y", "inpe",
                                      "h_ratio"]).sort_values(["trade_region", "rms", "x", "capri_y"])
    to_csv(out, OUT, index=False)

    # checks: the terms give CAPRI's p_elasSupp at the calibration point (h x PPRI_y / INPE / PROD_x, CAPRI's elasticity definition)
    worst, n = 0.0, 0
    for t in out.itertuples(index=False):
        if (t.rms, t.capri_x, t.capri_y) not in stored:
            continue                                       # a term completed from its transpose (_capri_nq step 3)
        e = elas.get((t.rms, t.capri_x, t.capri_y))
        q = data.get((t.rms, "PROD", t.capri_x), 0.0)
        if e is None or not q > 0 or not t.ppri_y:
            continue
        n += 1
        worst = max(worst, abs(t.h_ratio / q - e) / max(abs(e), 1e-3))
    used = out[out.y != ""]
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} terms, {out.rms.nunique()} CAPRI regions, "
          f"{out.trade_region.nunique()} trade regions; {len(used)} on model prices "
          f"({int((used.x == used.y).sum())} own-price, {int((used.x != used.y).sum())} cross)")
    print(f"  p_elasSupp reproduced on {n} terms: worst relative deviation {worst:.2e}")
    tot = float(out.h_ratio.abs().sum())
    print("  held at calibration (no model price): " + ", ".join(
        f"{y} {v / tot:.2%}" for y, v in sorted(held.items(), key=lambda kv: -kv[1]) if v > 0)
          + f"; without a CAPRI price: {sorted(y for y, v in held.items() if v == 0.0)}")
    build_land_market(data, rm_of, noneu - rmssup, model_region)


def build_land_market(data: dict, rm_of: dict, regions: set, model_region) -> None:
    """CAPRI's market land block per non-EU market region without supply models (arm/market_model.gms l. 1696-1790,
    supremaMrk on): the MNL land supply of the six land types out of ARTO - INLW (LandSupplyMNL_; in a simulation its
    asymmetric form NumeraireLand_ / LandSupplyRatio_, the same function when no LEVL_1 commitment area is given, as
    here: p_useSymmetricMNL has no records in sim_ini_21730), with the constants v_aLU fixed at p_aLU "CUR"
    (capmod/set_start_val.gms l. 236) and the rents of FORE, ARTIF, OLND fixed (v_rentPerHa bounds); the rents of the
    agricultural types TCRP, FODFAL, FRUN free, each equal to the land's producer price (rentFromProdpriceLand_; no
    PSEd on land in the data), with supply equal to the land demand of ProdNQ_ (LndSupplyEqualsDemand_).

    Sources: sim_ini_21730 (p_aLU, p_bLu, v_land, v_rentPerHa, DATA ARTO and INLW LEVL CUR), the market data
    (Data_CAL PROD and PPRI of the land types). Checks: the MNL reproduces v_land at v_rentPerHa, the agricultural
    land equals PROD at CAL and the rents PPRI at CAL plus PSEd (the land types' or LAND's, arm/prep_market.gms
    l. 134: Switzerland's 1116.43 EUR/ha). In the change form the model uses, PSEd drops out (a constant).

    Outputs: noneu_land_market.csv (trade_region, rms, lu, land_kha, rent, alu, endogenous, avail_kha) and
    noneu_land_mnl.csv (rms, lu, lu1, b: p_bLu "CUR", per EUR/ha)."""
    import numpy as np
    from paths import REFERENCE
    sim = REFERENCE / "simini" / "simini_21730"
    alu = read_csv(sim / "p_aLU.csv.gz", keep_default_na=False)
    blu = read_csv(sim / "p_bLu.csv.gz", keep_default_na=False)
    vl = read_csv(sim / "v_land.csv.gz", keep_default_na=False)
    vr = read_csv(sim / "v_rentPerHa.csv.gz", keep_default_na=False)
    sym = read_csv(sim / "p_useSymmetricMNL.csv.gz", keep_default_na=False)
    D = read_csv(sim / "DATA.csv.gz", keep_default_na=False, usecols=["d0", "d1", "d2", "d3", "value"])
    D = D[(D.d3 == "CUR") & (((D.d2.isin(("LEVL", "LEVL_1"))) & D.d1.isin(LU_ELA + ("ARTO", "INLW")))
                             | ((D.d1 == "PSED") & D.d2.isin(("LAND",) + LU_ELA)))]
    lev = {(t.d0, t.d1): float(t.value) for t in D.itertuples(index=False) if t.d2 == "LEVL"}
    # the support to land (PSEd), the land types' own or else LAND's (arm/prep_market.gms l. 134-135)
    pse = {(t.d0, t.d2): float(t.value) for t in D.itertuples(index=False) if t.d1 == "PSED"}
    if any(t.d2 == "LEVL_1" for t in D.itertuples(index=False)):
        raise SystemExit("LEVL_1 commitment areas in DATA: the asymmetric MNL differs from the symmetric one")
    A = {(t.d0, t.d1): float(t.value) for t in alu[alu.d2 == "CUR"].itertuples(index=False)}
    B = {(t.d0, t.d1, t.d2): float(t.value) for t in blu[blu.d3 == "CUR"].itertuples(index=False)}
    L = {(t.d0, t.d1): float(t.level) for t in vl.itertuples(index=False)}
    Rt = {(t.d0, t.d1): (float(t.level), float(t.lower) != float(t.upper)) for t in vr.itertuples(index=False)}
    rms_all = sorted({r for r, _ in A} & regions)
    rows, mnl, worst_l, worst_d, worst_p = [], [], 0.0, 0.0, 0.0
    for r in rms_all:
        lus = [u for u in LU_ELA if (r, u) in A]
        avail = lev.get((r, "ARTO"), 0.0) - lev.get((r, "INLW"), 0.0)
        rent = np.array([Rt.get((r, u), (0.0, False))[0] for u in lus])
        b = np.array([[B.get((r, u, u1), 0.0) for u1 in lus] for u in lus])
        z = np.array([A[(r, u)] for u in lus]) + b @ rent
        sh = np.exp(z - z.max())
        land = avail * sh / sh.sum()
        for i, u in enumerate(lus):
            l0 = L.get((r, u), 0.0)
            worst_l = max(worst_l, abs(land[i] - l0) / max(l0, 1.0))
            free = Rt.get((r, u), (0.0, False))[1]
            if free:
                worst_d = max(worst_d, abs(data.get((r, "PROD", u), 0.0) - l0) / max(l0, 1.0))
                ps = pse.get((r, u), pse.get((r, "LAND"), 0.0))
                # rentFromProdpriceLand_: rent = producer price + PSEd
                worst_p = max(worst_p, abs(data.get((r, "PPRI", u), 0.0) + ps - rent[i]) / max(abs(rent[i]), 1.0))
            rows.append((model_region(rm_of[r]), r, u, l0, rent[i], A[(r, u)], int(free), avail))
            for j, u1 in enumerate(lus):
                if b[i, j]:
                    mnl.append((r, u, u1, b[i, j]))
    out = pd.DataFrame(rows, columns=["trade_region", "rms", "lu", "land_kha", "rent", "alu", "endogenous", "avail_kha"])
    to_csv(out.sort_values(["trade_region", "rms", "lu"]), LAND_OUT, index=False)
    to_csv(pd.DataFrame(mnl, columns=["rms", "lu", "lu1", "b"]).sort_values(["rms", "lu", "lu1"]), MNL_OUT, index=False)
    print(f"wrote {LAND_OUT.relative_to(ROOT)}: {len(rms_all)} CAPRI regions, {int(out.endogenous.sum())} free rents "
          f"(p_useSymmetricMNL records: {len(sym)}); {MNL_OUT.relative_to(ROOT)}: {len(mnl)} terms")
    print(f"  MNL at v_rentPerHa reproduces v_land: worst relative deviation {worst_l:.2e}; agricultural land against "
          f"PROD at CAL {worst_d:.2e}; rents against PPRI + PSEd at CAL {worst_p:.2e}")
    if max(worst_l, worst_d, worst_p) > 1e-6:
        raise SystemExit("the land market does not reproduce CAPRI's calibration point")


if __name__ == "__main__":
    main()
