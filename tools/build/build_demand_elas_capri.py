"""CAPRI's food demand elasticities of the cereal markets (K24) and of the market products added later.

CAPRI's market model prices human consumption with the calibrated Generalised Leontief demand system; its own-price
elasticities are p_ElasDem(region, product, product) in the calibrated elasticity export elas_2_1717defaulta (the
same export eu_demand_elas_overrides.json was built from). Before this tool the cereals took -0.2 (OCER, CORN,
PARI, RYEM, OATS), -0.205 (BARL) and -0.039 (SWHE) from armington_params.csv's eta column, of unrecorded source,
against CAPRI's ~-0.5 (wheat ~-0.2 to -0.4).

  EU row:            median over the 26 CAPRI member-state codes (EU27; BL = Belgium + Luxembourg), the method of
                     the existing entries of eu_demand_elas_overrides.json (reproduced below as a check)
                     -> capri_data/2017/market/eu_demand_elas_overrides.json (cereal entries added)
  non-EU regions:    the model has one demand elasticity per commodity for all non-EU trade regions (the eta column
                     of armington_params.csv); median over CAPRI's non-EU regions with a value
                     -> capri_data/2017/market/armington_params.csv (eta of the cereals)

Tobacco: in the EU member states CAPRI has no human consumption of tobacco; its use is processing (PROC), priced by
the normalised quadratic processing function p_hessNQProc, which CAPRI sets (arm/trim_elas.gms, "assume elasticity of
0.1 for tobacco") so that the price elasticity of processing demand is -0.1 on a margin of 0.2 x PPRI, i.e. -0.5.
The EU row takes -hess x PPRI / PROC from CAPRI's 1730 calibration (elas_2_1730defaulta with data_market_1730defaulta,
the same vintage on both sides; -0.5 in all 26 member states). Non-EU regions: p_ElasDem as for the other products.
Textile crops (TEXT): the same, with CAPRI's rule for all other processing ("assume elasticity of 0.5"): -0.5 on a
margin of 0.2 x PPRI, i.e. -2.5 (the 9 member states with textile processing).

Model market -> CAPRI product: SWHE <- WHEA, BARL, CORN <- MAIZ, RYEM, OATS, OCER, PARI <- RICE; table grapes TAGR
tobacco TOBA, table olives TABO and textile crops TEXT (markets since October 2026).

    python tools/build/build_demand_elas_capri.py [--elas /mnt/user-data/uploads/elas_2_1717defaulta.csv]
"""
from __future__ import annotations
import argparse, json, re, statistics
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MKT = ROOT / "capri_data" / "2017" / "market"
CEREALS = {"SWHE": "WHEA", "BARL": "BARL", "CORN": "MAIZ", "RYEM": "RYEM", "OATS": "OATS", "OCER": "OCER",
           "PARI": "RICE", "TAGR": "TAGR", "TOBA": "TOBA", "TABO": "TABO", "TEXT": "TEXT",
            "PLMO": "PLMO", "OTHO": "OTHO", "FFIS": "FFIS", "SFIS": "SFIS", "OAQU": "OAQU", "COFF": "COFF",
            "TEAS": "TEAS", "COCO": "COCO"}
EU_MS = ("AT BL BG CY CZ DE DK EE EL ES FI FR HR HU IR IT LT LV MT NL PL PT RO SE SI SK").split()


def read_elas_dem(path: Path) -> dict:
    """p_ElasDem own-price values: product -> {region: value}."""
    out, cur = {}, None
    pat = re.compile(r"^'([^']+)'\.'([^']+)'\.'([^']+)'\.'CAL'\s+([-\d.Ee+]+)")
    for line in open(path, encoding="latin-1"):
        if line.startswith("Parameter"):
            cur = line.split("(")[0].split()[1]
            if cur == "p_elasSupp":
                break
            continue
        if cur != "p_ElasDem":
            continue
        m = pat.match(line)
        if m and m.group(2) == m.group(3):
            out.setdefault(m.group(2), {})[m.group(1)] = float(m.group(4))
    return out


def tobacco_processing_elas(elas_path: Path, market_path: Path, eu_codes, prod: str = "TOBA") -> float:
    """Median over the member states of CAPRI's processing demand elasticity -hess x PPRI / PROC (CAL) of a product
    whose EU use is processing (tobacco; textile crops)."""
    P, Q, H, cur = {}, {}, {}, None
    for line in open(market_path, encoding="latin-1"):
        m = re.match(rf"^'([^']+)'\.'(PPRI|PROC)'\.'{prod}'\.'CAL'\s+([-\d.Ee+]+)", line)
        if m:
            (P if m.group(2) == "PPRI" else Q)[m.group(1)] = float(m.group(3))
    for line in open(elas_path, encoding="latin-1"):
        if line.startswith("Parameter"):
            cur = line.split("(")[0].split()[1]
            continue
        if cur == "p_hessNQProc":
            m = re.match(rf"^'([^']+)'\.'{prod}'\.'{prod}'\.'CAL'\s+([-\d.Ee+]+)", line)
            if m:
                H[m.group(1)] = float(m.group(2))
    codes = eu_codes if eu_codes is not None else [r for r in H if r not in {c + "000000" for c in EU_MS}]
    el = [-H[r] * P[r] / Q[r] for r in codes if r in H and r in P and Q.get(r, 0) > 0]
    print(f"{prod} processing elasticity over {len(el)} regions: min {min(el):.3f}, max {max(el):.3f}")
    return round(statistics.median(el), 3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--elas", type=Path, default=Path("/mnt/user-data/uploads/elas_2_1717defaulta.csv"))
    ap.add_argument("--elas-proc", type=Path, default=Path("/mnt/user-data/uploads/elas_2_1730defaulta.csv"))
    ap.add_argument("--market-proc", type=Path, default=Path("/mnt/user-data/uploads/data_market_1730defaulta.csv"))
    args = ap.parse_args()
    el = read_elas_dem(args.elas)
    eu_codes = [c + "000000" for c in EU_MS]
    med_eu = lambda p: statistics.median(v for r, v in el.get(p, {}).items() if r in eu_codes)
    med_row = lambda p: statistics.median(v for r, v in el.get(p, {}).items() if r not in eu_codes)

    f = MKT / "eu_demand_elas_overrides.json"
    ov = json.load(open(f))
    # check: the existing entries are reproduced by this method
    for k in ("RAPO", "SUNO", "SOYO"):
        if k in ov:
            assert abs(round(med_eu(k), 3) - ov[k]) < 1e-9, (k, med_eu(k), ov[k])
    arm = pd.read_csv(MKT / "armington_params.csv", index_col=0)
    PROC_PRODUCTS = ("TOBA", "TEXT")          # EU use is processing only (p_hessNQProc)
    proc_eu = {p: tobacco_processing_elas(args.elas_proc, args.market_proc, eu_codes, p) for p in PROC_PRODUCTS}
    for mc, p in CEREALS.items():
        e_eu = proc_eu[p] if p in proc_eu else round(med_eu(p), 3)
        if p in el:
            e_row = round(med_row(p), 4)
            n_row = sum(1 for r in el[p] if r not in eu_codes)
        else:   # no p_ElasDem anywhere (textile crops: processing use only) -> CAPRI's processing elasticity
            e_row = tobacco_processing_elas(args.elas_proc, args.market_proc, None, p)
            n_row = "processing,"
        print(f"{mc:5s} <- {p}: EU {e_eu:+.3f} (was {ov.get(mc, 'n/a')}); non-EU {e_row:+.4f} over {n_row} CAPRI "
              f"regions (was {arm.at[mc, 'eta'] if mc in arm.index else 'n/a'})")
        ov[mc] = e_eu
        arm.loc[mc, "eta"] = e_row
    ov["_source"] = ("CAPRI calibrated market elasticities elas_2_1717defaulta p_ElasDem, own-price, median over EU "
                     "member states (supplied by the project lead). Applied to the EU row only. Cereals (K24) and "
                     "later market products added by tools/build/build_demand_elas_capri.py.")
    json.dump(ov, open(f, "w"), indent=1)
    arm.to_csv(MKT / "armington_params.csv")
    print(f"wrote {f.relative_to(ROOT)} and armington_params.csv")


if __name__ == "__main__":
    main()
