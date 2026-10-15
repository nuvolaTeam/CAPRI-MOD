"""Market parameters of CAPRI's nine dairy products (Sprint 9f: all nine traded, as in CAPRI's market model).

CAPRI trades every product of its dairy block bilaterally (arm/market_model.gms; butter BUTT, skimmed milk powder
SMIP, cheese CHES, whey powder WHEP, fresh milk products FRMI, cream CREM, concentrated milk COCM, whole milk powder
WMIO, casein CASE), with Armington elasticities from special_ch/market1_ch.gms (tools/build_bilateral_market.py,
armington_rho.csv). Their supply comes from the dairy blocks (EU member states: the supply models' milk; the
non-EU regions: CAPRI's raw milk supply functions; capri_mod.market.MarketModule._dairy_*); their demand from
CAPRI's p_ElasDem among the nine products in the regions with a block. This builder writes, per product, the
armington_params.csv row the market uses where a region has no dairy block (Algeria, Egypt, Iran, Saudi Arabia:
consumption only, none of them produces the products in CAPRI's 2030 bilateral data):

  sigma, rho2   CAPRI's p_rhoArm1, p_rhoArm2 (armington_rho.csv)
  eta           CAPRI's own-price p_ElasDem, weighted by human consumption over CAPRI's non-EU market regions
                (dairy_world_demand_elas.csv, dairy_world_processing.csv hcon_kt)
  eps           0: no supply outside the dairy blocks

Model codes: BUTR, SKIM, CHES, WHEY for the first four (the market's names), CAPRI's codes for the others.

    python tools/build_dairy_trade_params.py
"""
from __future__ import annotations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MKT = ROOT / "capri_data" / "2017" / "market"
CODE = {"BUTT": "BUTR", "SMIP": "SKIM", "CHES": "CHES", "WHEP": "WHEY", "FRMI": "FRMI", "CREM": "CREM",
        "COCM": "COCM", "WMIO": "WMIO", "CASE": "CASE"}


def main():
    wp = pd.read_csv(MKT / "dairy_world_processing.csv")
    ee = pd.read_csv(MKT / "dairy_world_demand_elas.csv")
    rho = pd.read_csv(MKT / "armington_rho.csv").set_index("commodity")
    arm = pd.read_csv(MKT / "armington_params.csv", index_col=0)
    own = ee[ee.row == ee.col].set_index(["rms", "row"])["elas"]
    h = wp.set_index(["rms", "item"])["hcon_kt"]
    for k, m in CODE.items():
        num = den = 0.0
        for (r, i), v in h.items():
            if i == k and v == v and v > 0 and (r, k) in own.index:
                num += v * float(own[(r, k)])
                den += v
        eta = num / den
        old = arm.loc[m].to_dict() if m in arm.index else {}
        arm.loc[m, "sigma"] = float(rho.at[m, "rho1"])
        arm.loc[m, "rho2"] = float(rho.at[m, "rho2"])
        arm.loc[m, "eta"] = round(eta, 4)
        if m not in ("BUTR", "SKIM", "CHES", "WHEY"):
            arm.loc[m, "eps"] = 0.0
        print(f"{m}: eta {eta:.4f} (was {old.get('eta')}), sigma {arm.at[m, 'sigma']}, rho2 {arm.at[m, 'rho2']}, "
              f"eps {arm.at[m, 'eps']}")
    arm.to_csv(MKT / "armington_params.csv")


if __name__ == "__main__":
    main()
