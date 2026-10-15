"""CAPRI-mod's 2030 baseline against the EU agricultural outlook 2020-2030 and CAPRI star 3.0's 2030 reference.

python tools/compare_outlook_2030.py RUN.pkl [OUT.csv]

RUN.pkl: a run saved by tools/run_f2f_2030.py (its baseline is the 2030 baseline). Three columns per item: the
outlook's 2030 (capri_data/validation/eu_outlook_2020_2030.csv, tools/build_eu_outlook_2030.py), CAPRI's 2030
reference (capri_data/validation/capri_eu27_market_balance_2030_ref.json, levels from capri_eu27_levels_2030_ref.csv)
and CAPRI-mod's baseline. Trade is compared as net exports only: CAPRI's IMPT / EXPT are sums over member states and
include intra-EU trade; the outlook's are extra-EU.

Item definitions follow the outlook's tables; where CAPRI's product differs it is said in the 'note' column.
"""
import csv
import json
import pickle
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "capri_data" / "validation"

# (label, unit, outlook (table, item, factor), CAPRI (product, field) or level (act), CAPRI-mod source, note)
#   CAPRI-mod source: ("act", code) 1000 ha / 1000 heads; ("out", code) regional supply 1000 t; ("prod", code) market
#   production 1000 t; ("net", code) market net exports 1000 t
ITEMS = [
    ("common wheat area", "1000 ha", ("8.8", "Common wheat", 1000), ("lvl", "SWHE"), ("act", "SWHE"), ""),
    ("durum wheat area", "1000 ha", ("8.8", "Durum wheat", 1000), ("lvl", "DWHE"), ("act", "DWHE"), ""),
    ("barley area", "1000 ha", ("8.8", "Barley", 1000), ("lvl", "BARL"), ("act", "BARL"), ""),
    ("maize area", "1000 ha", ("8.8", "Maize", 1000), ("lvl", "MAIZ"), ("act", "CORN"), ""),
    ("rye area", "1000 ha", ("8.8", "Rye", 1000), ("lvl", "RYEM"), ("act", "RYEM"), "CAPRI RYEM = rye and meslin"),
    ("rapeseed area", "1000 ha", ("8.8", "Rapeseed", 1000), ("lvl", "RAPE"), ("act", "RAPE"), ""),
    ("sunflower area", "1000 ha", ("8.8", "Sunseed", 1000), ("lvl", "SUNF"), ("act", "SUNF"), ""),
    ("soya area", "1000 ha", ("8.8", "Soyabeans", 1000), ("lvl", "SOYA"), ("act", "SOYA"), ""),
    ("sugar beet area", "1000 ha", ("8.8", "Sugar beet", 1000), ("lvl", "SUGB"), ("act", "SUGB"), ""),
    ("pulses area", "1000 ha", ("8.8", "Pulses", 1000), ("lvl", "PULS"), ("act", "PULS"), ""),
    ("rice area", "1000 ha", ("8.8", "Rice", 1000), ("lvl", "PARI"), ("act", "PARI"), ""),
    ("common wheat production", "1000 t", ("8.12", "Production", 1000), ("SWHE", "GROF"), ("out", "SWHE"), ""),
    ("durum wheat production", "1000 t", ("8.13", "Production", 1000), ("DWHE", "GROF"), ("out", "DWHE"), ""),
    ("barley production", "1000 t", ("8.14", "Production", 1000), ("BARL", "GROF"), ("out", "BARL"), ""),
    ("maize production", "1000 t", ("8.15", "Production", 1000), ("MAIZ", "GROF"), ("out", "CORN"), ""),
    ("cereals production", "1000 t", ("8.9", "Production", 1000), ("CERE", "GROF"), ("sum_out", "SWHE DWHE RYEM BARL OATS CORN OCER"), "outlook: excl. rice"),
    ("cereals net exports", "1000 t", ("8.9", "Exports-Imports", 1000), ("CERE", "NET"), ("sum_net", "SWHE BARL CORN OCER"), "CAPRI-mod: wheat incl. durum, rye/oats in OCER"),
    ("rapeseed production", "1000 t", ("8.18", "Rapeseed", 1000), ("RAPE", "GROF"), ("out", "RAPE"), ""),
    ("sunflower seed production", "1000 t", ("8.18", "Sunflower seed", 1000), ("SUNF", "GROF"), ("out", "SUNF"), ""),
    ("soya bean production", "1000 t", ("8.18", "Soya beans", 1000), ("SOYA", "GROF"), ("out", "SOYA"), ""),
    ("oilseed meal production", "1000 t", ("8.19", "Production", 1000), ("CAKS", "GROF"), ("sum_prod", "RAPC SUNC SOYC"), ""),
    ("oilseed oil production", "1000 t", ("8.20", "Production", 1000), ("OILP", "GROF"), ("sum_prod", "RAPO SUNO SOYO"), ""),
    ("sugar beet production", "1000 t", ("8.22", "Sugar beet production (million tonnes)", 1000), ("SUGB", "GROF"), ("out", "SUGB"), ""),
    ("sugar production", "1000 t", ("8.22", "Sugar production*", 1000), ("SUGA", "GROF"), ("prod", "SUGR"), ""),
    ("dairy cows", "1000 heads", ("8.25", "Dairy cows (million heads)", 1000), ("lvl", "DCOW"), ("act", "DCOW"), ""),
    ("suckler cows", "1000 heads", ("8.32", "of which sukler cows", 1000), ("lvl", "SCOW"), ("act", "BCOW"), ""),
    ("cow milk production", "1000 t", ("8.25", "Dairy cow milk production (million t)", 1000), ("COMI", "GROF"), ("out", "DCOW"), "milk of dairy cows"),
    ("cheese production", "1000 t", ("8.27", "Production", 1), ("CHES", "GROF"), ("prod", "CHES"), ""),
    ("butter production", "1000 t", ("8.28", "Production", 1), ("BUTT", "GROF"), ("prod", "BUTR"), ""),
    ("SMP production", "1000 t", ("8.29", "Production", 1), ("SMIP", "GROF"), ("prod", "SKIM"), ""),
    ("WMP production", "1000 t", ("8.30", "Production", 1), ("WMIO", "GROF"), ("prod", "WMIO"), "CAPRI WMIO includes other milk powders"),
    ("beef production", "1000 t cwe", ("8.32", "Gross Indigenous Production", 1), ("BEEF", "GROF"), ("prod", "BEEF"), ""),
    ("pigmeat production", "1000 t cwe", ("8.34", "Gross Indigenous Production", 1), ("PORK", "GROF"), ("prod", "PORK"), ""),
    ("poultry meat production", "1000 t cwe", ("8.35", "Gross Indigenous Production", 1), ("POUM", "GROF"), ("prod", "POUL"), ""),
    ("sheep and goat meat production", "1000 t cwe", ("8.33", "Gross Indigenous Production", 1), ("SGMT", "GROF"), ("prod", "SHGM"), ""),
    ("egg production", "1000 t", ("8.37", "Production", 1), ("EGGS", "GROF"), ("prod", "EGGS"), ""),
    ("pigmeat net exports", "1000 t cwe", ("8.34", "Exports-Imports", 1), ("PORK", "NET"), ("net", "PORK"), ""),
    ("poultry net exports", "1000 t cwe", ("8.35", "Exports-Imports", 1), ("POUM", "NET"), ("net", "POUL"), ""),
    ("beef net exports", "1000 t cwe", ("8.32", "Exports-Imports", 1), ("BEEF", "NET"), ("net", "BEEF"), ""),
    ("olive oil production", "1000 t", ("8.38", "Production", 1), ("OLIO", "GROF"), ("prod", "OLIV"), ""),
    ("wine production", "1000 t (= 10 hl)", ("8.39", "Vinified production", 100), ("TWIN", "GROF"), ("out", "WINE"), "outlook in million hl"),
    ("apple production", "1000 t", ("8.40", "Gross production", 1), ("APPL", "GROF"), ("out", "APPL"), ""),
    ("tomato production", "1000 t", ("8.41", "Production (total)", 1), ("TOMA", "GROF"), ("out", "TOMA"), ""),
]

TRADE = {"Exports-Imports": ("Exports", "Imports")}
TRADE_MEAT = {"Exports-Imports": ("Exports (meat)", "Imports (meat)")}


def outlook_value(ol, table, item, factor, year="2030"):
    g = ol[ol.table == table]
    if item == "Exports-Imports":
        ex, im = TRADE_MEAT[item] if table in ("8.32", "8.33", "8.34", "8.35") else TRADE[item]
        e = g[g.item == ex][year]; i_ = g[g.item == im][year]
        if e.empty or i_.empty:
            return None
        return (float(e.iloc[0]) - float(i_.iloc[0])) * factor
    r = g[g.item == item][year]
    return float(r.iloc[0]) * factor if not r.empty else None


def main(run, out_csv=None):
    ol = pd.read_csv(VAL / "eu_outlook_2020_2030.csv", dtype=str)
    capri = json.load(open(VAL / "capri_eu27_market_balance_2030_ref.json"))["products"]
    lvl = pd.read_csv(VAL / "capri_eu27_levels_2030_ref.csv", index_col=0)["val"].to_dict()
    d = pickle.load(open(run, "rb"))
    act, outq = d["act"][0], d["out"][0]
    bm = d["base_market"]
    rows = []
    for lab, unit, (tab, item, fac), (cp, cf), (src, code), note in ITEMS:
        o = outlook_value(ol, tab, item, fac)
        if cp == "lvl":
            c = lvl.get(cf)
            c = float(c) if c is not None else None
        elif cf == "NET":
            v = capri.get(cp) or {}
            c = (float(v.get("EXPT", 0.0)) - float(v.get("IMPT", 0.0))) if v else None
        else:
            c = float((capri.get(cp) or {}).get(cf)) if (capri.get(cp) or {}).get(cf) is not None else None
        codes = code.split()
        if src == "act":
            m = float(act.get(code, float("nan")))
        elif src == "out":
            m = float(outq.get(code, float("nan")))
        elif src == "sum_out":
            m = sum(float(outq.get(k, 0.0)) for k in codes)
        elif src == "prod":
            m = float(bm["prod"].get(code, float("nan")))
        elif src == "sum_prod":
            m = sum(float(bm["prod"].get(k, 0.0)) for k in codes)
        elif src == "net":
            m = float(bm["net_exports"].get(code, float("nan")))
        elif src == "sum_net":
            m = sum(float(bm["net_exports"].get(k, 0.0)) for k in codes)
        else:
            m = None
        rows.append((lab, unit, o, c, m, note))
    w = max(len(r[0]) for r in rows)
    print(f"{'item':{w}s} {'unit':>16s} {'outlook':>10s} {'CAPRI ref':>10s} {'CAPRI-mod':>10s} {'mod/outl':>9s} {'CAPRI/outl':>10s}")
    for lab, unit, o, c, m, note in rows:
        def f(x):
            return f"{x:10.0f}" if x is not None and x == x else f"{'-':>10s}"

        def r(a, b):
            return f"{100 * (a / b - 1):+8.1f}%" if (a is not None and b and a == a and "net" not in lab) else f"{'':>9s}"
        print(f"{lab:{w}s} {unit:>16s} {f(o)} {f(c)} {f(m)} {r(m, o)} {r(c, o):>10s}  {note}")
    if out_csv:
        with open(out_csv, "w", newline="") as fh:
            cw = csv.writer(fh)
            cw.writerow(["item", "unit", "outlook_2030", "capri_ref_2030", "capri_mod_2030", "note"])
            cw.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
