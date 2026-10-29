"""Base-year gross nitrogen balance by member state against Eurostat's (aei_pr_gnb, 2017).

An external check of the model's balance components: mineral fertiliser, manure (total and pigs),
biological fixation, deposition and the surplus per ha. Eurostat's balance differs from CAPRI's by
definition (crop residues left on the field are neither input nor output in Eurostat; CAPRI counts them
on both sides; manure coefficients are national), so components are compared, not only the surplus.

Data: capri_data/sources/eurostat/aei_pr_gnb_nitrogen.csv (Eurostat AEI_PR_GNB, N, tonnes and kg/ha;
supplied by the project lead). Usage: python tools/check/validate_gnb_eurostat.py [year]
"""
import sys
import warnings
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")


def main(year=2017):
    from capri_mod.data.loaders import load_all_data
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    from capri_mod.data.definitions import ANIMALS
    d = load_all_data(str(ROOT / "capri_data"))
    e = EnvironmentalModule(d)
    es = _read_csv(ROOT / "capri_data" / "sources" / "eurostat" / "aei_pr_gnb_nitrogen.csv")
    es = es[es.year == year].pivot_table(index="geo", columns="indic_ag", values="value")
    H = d["animal_numbers"]
    rows = {}
    for r in d["areas"].index:
        if r not in d["yields"].index:
            continue
        acts = {**d["areas"].loc[r].to_dict(), **(H.loc[r].to_dict() if r in H.index else {})}
        nb = e.compute_nitrogen_balance(acts, d["yields"].loc[r], r)
        a = sum(float(d["areas"].loc[r].get(c, 0) or 0) for c in d["areas"].columns)
        cc = {"GR": "EL"}.get(r[:2], r[:2])
        man = {x: float(H.loc[r].get(x, 0)) * e._n_excretion(r, x) for x in ANIMALS} if r in H.index else {}
        v = rows.setdefault(cc, dict(uaa=0.0, mineral=0.0, manure=0.0, pigs=0.0, fixation=0.0, deposition=0.0, surplus=0.0))
        v["uaa"] += a
        v["mineral"] += nb["n_mineral_input"]
        v["manure"] += sum(man.values())
        v["pigs"] += man.get("PIGS", 0.0) + man.get("PIGF", 0.0)
        v["fixation"] += nb["n_fixation"]
        v["deposition"] += nb["n_deposition"]
        v["surplus"] += nb["n_surplus"]
    m = pd.DataFrame(rows).T
    kt = lambda s: s / 1000.0                     # tonnes -> kt (model areas in 1000 ha x kg/ha = t)
    out = pd.DataFrame({
        "mineral_model": kt(m["mineral"]), "mineral_eurostat": kt(es.get("I_FRT_MIN")),
        "manure_model": kt(m["manure"]), "manure_eurostat": kt(es.get("I_MNR_PRD")),
        "pig_manure_model": kt(m["pigs"]), "pig_manure_eurostat": kt(es.get("I_MNR_PPG")),
        "fixation_model": kt(m["fixation"]), "fixation_eurostat": kt(es.get("I_OTH_BIO")),
        "deposition_model": kt(m["deposition"]), "deposition_eurostat": kt(es.get("I_OTH_DEP")),
        "surplus_ha_model": m["surplus"] / m["uaa"], "surplus_ha_eurostat": es.get("BAL_UAA"),
    }).dropna(subset=["mineral_eurostat", "mineral_model"])
    pd.set_option("display.width", 200)
    print(out.round(1).to_string())
    t = out.sum(numeric_only=True)
    for k in ("mineral", "manure", "pig_manure", "fixation", "deposition"):
        sub = out[[f"{k}_model", f"{k}_eurostat"]].dropna()
        print(f"{k:12s} model {sub.iloc[:, 0].sum():8.0f} kt  Eurostat {sub.iloc[:, 1].sum():8.0f} kt"
              f"  ratio {sub.iloc[:, 0].sum() / sub.iloc[:, 1].sum():.2f}  ({len(sub)} countries)")
    print("surplus per ha, correlation across countries: %.2f"
          % out[["surplus_ha_model", "surplus_ha_eurostat"]].corr().iloc[0, 1])
    return out


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2017)
