"""CAPRI's dairy processing, per member state: fat and protein balance and the dairies' normalised
quadratic (NQ) production function (arm/market_model.gms DairyNQ_, ProcMargM_, FatsProtBal_).

CAPRI's dairy block, per member state s, products k in BUTT SMIP CHES FRMI CREM COCM WMIO CASE WHEP and raw
milk MILK (= cow milk COMI + sheep and goat milk SGMI delivered to dairies, sets.gms PRCD MILK.(COMI,SGMI)):

  ProcMargM_   m_k = p_k - FATS_k x p_fat - PROT_k x p_prot        (m_MILK also nets CSEI)
  DairyNQ_     Q_k = c_k + sum_j H_kj m_j / p_INPE                  (MILK row sign-reversed: milk is the input)
  FatsProtBal_ Q_MILK x FATS_MILK = sum_k (Q_k - PROC_k) x FATS_k   (and the same for protein)

H = p_hessNQDairy (CAL, arm/trim_elas.gms), made symmetric and with the MILK row reversed as in
arm/market1.gms; in simulation CUR = CAL. FATS/PROT are contents in % (p_fat, p_prot per %-point and t).

Sources (CAPRI 2030 Green Deal reference): market results markmarket_greendeal_1730et_base_1717 (dataOut,
member states and EU): PROD, PROC, PRCM, GROF, HCOM, FEDM, INDM, LOSM, PPRI, FATS, PROT, CSEI, INPE,
Imports_noIntra / Exports_noIntra; elasticities elas_2_1730defaulta (p_hessNQDairy, p_ElasDair, p_ElasDem).
The rows used are kept under capri_data/sources/market/ so the build reruns without the dumps.

Outputs (capri_data/2017/market/):
  dairy_processing.csv   ms, item, q_kt, proc_kt, fats_pct, prot_pct, price, csei   (item: products, MILK,
                         COMI, SGMI; ms rows also carry inpe, p_fat, p_prot as items INPE / FATS / PROT)
  dairy_hessian.csv      ms, row, col, h        (symmetric, MILK row reversed; CAL)
  dairy_eu_balance.csv   product, prod_kt, hcom_kt, fedm_kt, indm_kt, losm_kt, proc_kt, net_imports_kt,
                         capri_extra_eu_net_imports_kt, eta_hcom   (sums of the EU27 member states;
                         net imports close their balance; eta = HCOM-weighted member-state own-price p_ElasDem)
  dairy_eu_demand_elas.csv   row, col, elas: EU food demand elasticities among the nine products (CAPRI
                         p_ElasDem own and cross, HCOM-weighted)

    python tools/build_dairy_processing.py [--dump ...markmarket_greendeal_1730et_base_1717.txt]
                                           [--elas ...elas_2_1730defaulta.csv]
"""
from __future__ import annotations
import argparse, importlib.util, re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC_M = ROOT / "capri_data" / "sources" / "market" / "dairy_dataout_2030.csv"
SRC_E = ROOT / "capri_data" / "sources" / "market" / "dairy_elasticities_2030.csv"
PRODUCTS = ("BUTT", "SMIP", "CHES", "FRMI", "CREM", "COCM", "WMIO", "CASE", "WHEP")
MLK = PRODUCTS + ("MILK",)
ITEMS = ("PROD", "PROC", "PRCM", "GROF", "HCOM", "FEDM", "INDM", "LOSM", "PPRI", "FATS", "PROT", "CSEI",
         "Imports_noIntra", "Exports_noIntra")
PRODS = set(MLK) | {"COMI", "SGMI", "INPE", "FATS", "PROT"}


def extract(dump: Path, elas: Path):
    pat = re.compile(r"^'([A-Z]{2}000000|EU)'\.''\.'(" + "|".join(ITEMS) + r")'\.'([A-Z]+)'\.'2030'\s+([-\d.Ee+]+)")
    rows = []
    for line in open(dump, errors="ignore"):
        if line.startswith("'"):
            m = pat.match(line)
            if m and m.group(3) in PRODS:
                rows.append((m.group(1), m.group(2), m.group(3), float(m.group(4))))
    pd.DataFrame(rows, columns=["region", "item", "product", "value"]).to_csv(SRC_M, index=False, float_format="%.10g")
    # elasticity file: three parameters, CAL rows of dairy items
    want = {"p_hessNQDairy", "p_ElasDair", "p_ElasDem"}
    cur, out = None, []
    pe = re.compile(r"^'([A-Z]{2}000000)'\.'([A-Z]+)'\.'([A-Z]+)'\.'CAL'\s+([-\d.Ee+]+)")
    for line in open(elas, errors="ignore"):
        if line.startswith("Parameter"):
            cur = line.split()[1].split("(")[0]
            continue
        if cur in want:
            m = pe.match(line)
            if m and m.group(2) in MLK and m.group(3) in MLK:
                out.append((cur, m.group(1), m.group(2), m.group(3), float(m.group(4))))
    pd.DataFrame(out, columns=["param", "ms", "row", "col", "value"]).to_csv(SRC_E, index=False, float_format="%.10g")
    print(f"extracted {len(rows)} market rows, {len(out)} elasticity rows")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, default=Path("/mnt/user-data/uploads/markmarket_greendeal_1730et_base_1717.txt"))
    ap.add_argument("--elas", type=Path, default=Path("/mnt/user-data/uploads/elas_2_1730defaulta.csv"))
    a = ap.parse_args()
    if a.dump.exists() and a.elas.exists():
        SRC_M.parent.mkdir(parents=True, exist_ok=True)
        extract(a.dump, a.elas)
    src = pd.read_csv(SRC_M)
    v = {(r.region, r.item, r.product): r.value for r in src.itertuples()}
    el = pd.read_csv(SRC_E)

    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    eu_ms = sorted({mr.national_code(r) for r in mr.model_regions()})

    rows, hrows, checks = [], [], []
    for ms in eu_ms:
        if not v.get((ms, "PROD", "MILK"), 0) > 0:
            continue
        inpe, pf, pp = (v.get((ms, "PPRI", x)) for x in ("INPE", "FATS", "PROT"))
        rows += [{"ms": ms, "item": "INPE", "price": inpe}, {"ms": ms, "item": "FATS", "price": pf},
                 {"ms": ms, "item": "PROT", "price": pp}]
        for k in MLK:
            q = v.get((ms, "PROD", k), 0.0)
            if not q > 0:
                continue
            rows.append({"ms": ms, "item": k, "q_kt": q, "proc_kt": v.get((ms, "PROC", k), 0.0) if k != "MILK" else 0.0,
                         "fats_pct": v.get((ms, "FATS", k), 0.0), "prot_pct": v.get((ms, "PROT", k), 0.0),
                         "price": v.get((ms, "PPRI", k), 0.0), "csei": v.get((ms, "CSEI", k), 0.0) if k == "MILK" else 0.0})
        for k in ("COMI", "SGMI"):
            rows.append({"ms": ms, "item": k, "q_kt": v.get((ms, "GROF", k), 0.0), "proc_kt": v.get((ms, "HCOM", k), 0.0),
                         "fats_pct": v.get((ms, "FATS", k), 0.0), "prot_pct": v.get((ms, "PROT", k), 0.0),
                         "price": v.get((ms, "PPRI", k), 0.0)})
        # Hessian: symmetric (market1.gms), MILK row reversed
        h = el[(el.param == "p_hessNQDairy") & (el.ms == ms)]
        H = defaultdict(float)
        for r in h.itertuples():
            H[(r.row, r.col)] = r.value
        for (i, j), x in list(H.items()):
            if (j, i) not in H:
                H[(j, i)] = x
        for (i, j), x in H.items():
            if x != 0 and v.get((ms, "PROD", i), 0) > 0 and v.get((ms, "PROD", j), 0) > 0:
                hrows.append({"ms": ms, "row": i, "col": j, "h": -x if i == "MILK" else x})
        # check: implied own-price elasticity vs CAPRI p_ElasDair
        e = el[(el.param == "p_ElasDair") & (el.ms == ms)].set_index(["row", "col"])["value"]
        for k in ("CHES", "BUTT", "MILK"):
            q, p = v.get((ms, "PROD", k), 0.0), v.get((ms, "PPRI", k), 0.0)
            if q > 0 and (k, k) in H and (k, k) in e.index:
                imp = (-1 if k == "MILK" else 1) * H[(k, k)] * p / inpe / q
                checks.append((ms, k, imp, float(e[(k, k)])))
    out = pd.DataFrame(rows)
    dest = ROOT / "capri_data" / "2017" / "market"
    out.to_csv(dest / "dairy_processing.csv", index=False, float_format="%.10g")
    pd.DataFrame(hrows).to_csv(dest / "dairy_hessian.csv", index=False, float_format="%.10g")

    # EU balance of the products (CAPRI's EU = the member states; trade without intra-EU flows)
    dem = el[el.param == "p_ElasDem"]
    bal = []
    S = lambda it, k: sum(v.get((ms, it, k), 0.0) for ms in eu_ms)
    for k in PRODUCTS:
        hc = {ms: v.get((ms, "HCOM", k), 0.0) for ms in eu_ms}
        own = {r.ms: r.value for r in dem[(dem.row == k) & (dem.col == k)].itertuples()}
        w = sum(hc[m] for m in own if hc.get(m, 0) > 0)
        eta = sum(own[m] * hc[m] for m in own if hc.get(m, 0) > 0) / w if w > 0 else float("nan")
        rec = {"product": k, "prod_kt": S("PROD", k), "hcom_kt": S("HCOM", k), "fedm_kt": S("FEDM", k),
               "indm_kt": S("INDM", k), "losm_kt": S("LOSM", k), "proc_kt": S("PROC", k)}
        # extra-EU net imports close the member states' balance (intra-EU trade cancels); CAPRI's own
        # extra-EU trade (EU Imports_noIntra - Exports_noIntra) is kept for comparison
        rec["net_imports_kt"] = (rec["hcom_kt"] + rec["fedm_kt"] + rec["indm_kt"] + rec["losm_kt"]
                                 + rec["proc_kt"] - rec["prod_kt"])
        rec["capri_extra_eu_net_imports_kt"] = (v.get(("EU", "Imports_noIntra", k), 0.0)
                                                - v.get(("EU", "Exports_noIntra", k), 0.0))
        rec["eta_hcom"] = eta
        bal.append(rec)
    bal = pd.DataFrame(bal)
    bal.to_csv(dest / "dairy_eu_balance.csv", index=False, float_format="%.8g")
    # EU food demand elasticities among the nine products (CAPRI p_ElasDem, own and cross), each row
    # weighted by the member states' food use (HCOM) of the row product
    em = []
    for k in PRODUCTS:
        hc = {ms: v.get((ms, "HCOM", k), 0.0) for ms in eu_ms}
        sub = dem[dem.row == k]
        for j in PRODUCTS:
            vals = {r.ms: r.value for r in sub[sub.col == j].itertuples()}
            w = sum(hc[m] for m in vals if hc.get(m, 0) > 0)
            if w > 0:
                em.append({"row": k, "col": j, "elas": sum(vals[m] * hc[m] for m in vals if hc.get(m, 0) > 0) / w})
    pd.DataFrame(em).to_csv(dest / "dairy_eu_demand_elas.csv", index=False, float_format="%.6g")

    print(f"dairy_processing.csv: {out.ms.nunique()} member states; dairy_hessian.csv: {len(hrows)} entries")
    print(bal.round(2).to_string(index=False))
    c = pd.DataFrame(checks, columns=["ms", "item", "implied", "capri"])
    print(f"own-price elasticity implied by H vs CAPRI p_ElasDair: max |diff| {float((c.implied - c.capri).abs().max()):.2e} "
          f"over {len(c)} checks")
    # fat and protein balance at the reference: milk solids in = solids in products
    for ms in eu_ms[:4] + ["DE000000", "FR000000"]:
        s = out[(out.ms == ms) & out["item"].isin(MLK)]
        if s.empty:
            continue
        m = s[s["item"] == "MILK"].iloc[0]
        p = s[s["item"] != "MILK"]
        for col in ("fats_pct", "prot_pct"):
            lhs, rhs = m.q_kt * m[col], float(((p.q_kt - p.proc_kt) * p[col]).sum())
            print(f"  {ms} {col[:4]}: milk {lhs:9.0f}  products {rhs:9.0f}  ({rhs / lhs - 1:+.2%})")


if __name__ == "__main__":
    main()
