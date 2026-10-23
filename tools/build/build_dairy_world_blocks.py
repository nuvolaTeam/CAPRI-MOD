"""CAPRI's dairy block for the non-EU market regions (dairy Stage 4).

CAPRI solves DairyNQ_, ProcMargM_ and FatsProtBal_ for every market region with dairy data, not only the
member states, and outside the EU raw milk comes from the market model's own supply function (the
normalised quadratic p_hessNQSupp, MILK row). So a non-EU region's butter, skimmed milk powder, cheese and
whey respond to dairy prices through its raw milk supply (CAPRI p_elasSupp MILK: NZL 0.72, USA 0.92) and its
dairies' choice of products (p_ElasDair: own-price elasticities around 1.5). The market used a flat 0.2-0.3
supply elasticity for each dairy product in every non-EU region (armington_params eps), so an EU supply cut
moved world dairy prices several times more than in CAPRI.

This builder takes, for every CAPRI market region outside the EU block (the EU member states of
dairy_processing.csv) that has a dairy Hessian - Norway included (trade region NOR, KNOWN_ISSUES K56: CAPRI's
market region NO000000 with supply models; the market delivers its raw milk from its supply models instead of
the raw milk supply function, as CAPRI's RMSSUP) - from CAPRI's 2030 Green Deal reference market results and elasticities:
  quantities (PROD, PROC), fat and protein contents, producer prices, INPE, fat and protein prices,
  food use HCON, feed use FEED, extra-region trade (Imports_noIntra, Exports_noIntra) of the products,
  p_hessNQDairy (symmetric, MILK row reversed as in arm/market1.gms), p_hessNQSupp(MILK, MILK) (raw milk
  supply), p_ElasDem among the nine products,
and maps each region to the model's trade region (tools/build/recalibrate_trade_2017.py REGION_MAP; others ROW).

Outputs (capri_data/2017/market/):
  dairy_world_processing.csv   trade_region, rms, item, q_kt, proc_kt, fats_pct, prot_pct, price, hcon_kt,
                               feed_kt, net_imports_kt   (items: the nine products and MILK; rows INPE, FATS,
                               PROT carry the prices; row MILKSUP carries the raw milk supply slope h_milk)
  dairy_world_hessian.csv      rms, row, col, h
  dairy_world_demand_elas.csv  rms, row, col, elas

    python tools/build/build_dairy_world_blocks.py
"""
from __future__ import annotations
import re, sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC_M = ROOT / "capri_data" / "sources" / "market" / "dairy_world_dataout_2030.csv"
SRC_E = ROOT / "capri_data" / "sources" / "market" / "dairy_world_elasticities_2030.csv"
PRODUCTS = ("BUTT", "SMIP", "CHES", "FRMI", "CREM", "COCM", "WMIO", "CASE", "WHEP")
MLK = PRODUCTS + ("MILK",)
ITEMS = ("PROD", "PROC", "FATS", "PROT", "PPRI", "HCON", "FEED", "Imports_noIntra", "Exports_noIntra")


def extract(dump: Path, elas: Path):
    pat = re.compile(r"^'([A-Z_0-9]+)'\.''\.'(" + "|".join(ITEMS) + r")'\.'([A-Z]+)'\.'2030'\s+([-\d.Ee+]+)")
    keep = set(MLK) | {"INPE", "FATS", "PROT"}
    rows = []
    for line in open(dump, errors="ignore"):
        if line.startswith("'"):
            m = pat.match(line)
            if m and m.group(3) in keep:
                rows.append(m.groups())
    pd.DataFrame(rows, columns=["region", "item", "product", "value"]).to_csv(SRC_M, index=False)
    want = {"p_hessNQDairy", "p_ElasDem", "p_hessNQSupp"}
    cur, out = None, []
    pe = re.compile(r"^'([A-Z_0-9]+)'\.'([A-Z]+)'\.'([A-Z]+)'\.'CAL'\s+([-\d.Ee+]+)")
    for line in open(elas, errors="ignore"):
        if line.startswith("Parameter"):
            cur = line.split()[1].split("(")[0]
            continue
        if cur in want:
            m = pe.match(line)
            if m and m.group(2) in MLK and m.group(3) in MLK and (cur != "p_hessNQSupp" or m.group(2) == m.group(3) == "MILK"):
                out.append((cur,) + m.groups())
    pd.DataFrame(out, columns=["param", "rms", "row", "col", "value"]).to_csv(SRC_E, index=False)
    print(f"extracted {len(rows)} market rows, {len(out)} elasticity rows")


def main():
    dump = Path("/mnt/user-data/uploads/markmarket_greendeal_1730et_base_1717.txt")
    elas = Path("/mnt/user-data/uploads/elas_2_1730defaulta.csv")
    if dump.exists() and elas.exists():
        extract(dump, elas)
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]
    from recalibrate_trade_2017 import REGION_MAP
    eu_block = set(pd.read_csv(ROOT / "capri_data" / "2017" / "market" / "dairy_processing.csv")["ms"])
    src = pd.read_csv(SRC_M)
    v = {(r.region, r.item, r.product): float(r.value) for r in src.itertuples()}
    el = pd.read_csv(SRC_E)
    hrms = set(el.loc[el.param == "p_hessNQDairy", "rms"])
    rms_all = sorted(r for r in hrms if r not in eu_block and v.get((r, "PROD", "MILK"), 0) > 0
                     and v.get((r, "PPRI", "INPE")))
    rows, hrows, erows = [], [], []
    for r in rms_all:
        tr = REGION_MAP.get(r, "ROW")
        inpe = v[(r, "PPRI", "INPE")]
        rows += [{"trade_region": tr, "rms": r, "item": x, "price": v.get((r, "PPRI", x), 0.0)} for x in ("INPE", "FATS", "PROT")]
        hs = el[(el.param == "p_hessNQSupp") & (el.rms == r)]
        rows.append({"trade_region": tr, "rms": r, "item": "MILKSUP", "price": float(hs["value"].iloc[0]) if len(hs) else 0.0})
        for k in MLK:
            q = v.get((r, "PROD", k), 0.0)
            if not q > 0:
                continue
            rows.append({"trade_region": tr, "rms": r, "item": k, "q_kt": q,
                         "proc_kt": v.get((r, "PROC", k), 0.0) if k != "MILK" else 0.0,
                         "fats_pct": v.get((r, "FATS", k), 0.0), "prot_pct": v.get((r, "PROT", k), 0.0),
                         "price": v.get((r, "PPRI", k), 0.0), "hcon_kt": v.get((r, "HCON", k), 0.0),
                         "feed_kt": v.get((r, "FEED", k), 0.0),
                         "net_imports_kt": v.get((r, "Imports_noIntra", k), 0.0) - v.get((r, "Exports_noIntra", k), 0.0)})
        H = defaultdict(float)
        for e in el[(el.param == "p_hessNQDairy") & (el.rms == r)].itertuples():
            H[(e.row, e.col)] = e.value
        for (i, j), x in list(H.items()):
            if (j, i) not in H:
                H[(j, i)] = x
        for (i, j), x in H.items():
            if x != 0 and v.get((r, "PROD", i), 0) > 0 and v.get((r, "PROD", j), 0) > 0:
                hrows.append({"rms": r, "row": i, "col": j, "h": -x if i == "MILK" else x})
        for e in el[(el.param == "p_ElasDem") & (el.rms == r)].itertuples():
            if e.row in PRODUCTS and e.col in PRODUCTS:
                erows.append({"rms": r, "row": e.row, "col": e.col, "elas": e.value})
    out = pd.DataFrame(rows)
    dest = ROOT / "capri_data" / "2017" / "market"
    out.to_csv(dest / "dairy_world_processing.csv", index=False, float_format="%.10g")
    pd.DataFrame(hrows).to_csv(dest / "dairy_world_hessian.csv", index=False, float_format="%.10g")
    pd.DataFrame(erows).to_csv(dest / "dairy_world_demand_elas.csv", index=False, float_format="%.6g")

    # checks: fat and protein balance per region; raw milk supply elasticity
    print(f"{len(rms_all)} CAPRI regions -> trade regions {sorted(out.trade_region.unique())}")
    worst = 0.0
    for r in rms_all:
        s = out[(out.rms == r) & out["item"].isin(MLK)]
        if "MILK" not in set(s["item"]):
            continue
        m = s[s["item"] == "MILK"].iloc[0]; p = s[s["item"] != "MILK"]
        for col in ("fats_pct", "prot_pct"):
            lhs, rhs = m.q_kt * m[col], float(((p.q_kt - p.proc_kt) * p[col]).sum())
            if lhs > 0:
                worst = max(worst, abs(rhs / lhs - 1))
    print(f"fat/protein balance: worst relative closure {worst:.2e}")
    ms = out[out["item"] == "MILKSUP"].set_index("rms")["price"]
    for r in ("USA", "NZL", "IND", "AUS", "BRA", "CHN"):
        if r in ms.index:
            q = float(out[(out.rms == r) & (out["item"] == "MILK")]["q_kt"].iloc[0])
            p = v[(r, "PPRI", "MILK")]; inpe = v[(r, "PPRI", "INPE")]
            print(f"  {r}: raw milk {q:9.0f} kt, supply elasticity {ms[r] * p / inpe / q:.2f}")


if __name__ == "__main__":
    main()
