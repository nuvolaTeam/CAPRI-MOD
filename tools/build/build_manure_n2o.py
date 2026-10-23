"""CAPRI's manure N2O by source, per model region and animal, and the ammonia technologies' N2O effects.

CAPRI (envind/gases.gms) computes manure N2O per activity from its manure N (MANN) and loss shares by stage:
  N2OMAN  housing and storage   MANN x (loss N2O Hous + loss N2O Stor) x 44/28
  N2OAPP  application           MANN x loss N2O Appl x 44/28
  N2OGRA  grazing               MANN x loss N2O Graz x 44/28
  N2OLEA  leaching              (indirect)
  N2OAMM  volatilisation        (NH3 + NOx)-N x EF4 x 44/28 (indirect)
The loss shares move with the ammonia technologies (v_emiLoss): CAPRI's technology effects on N2O
(ammo_tech.gms; capri_data/2017/abatement/ammonia/ammonia_technology_effects.csv, N2OHOU and N2OAPP; manure
acidification from p_litRevAmmoTechsAdd) - covered storage cuts housing/storage N2O, low-emission
application raises application N2O (slurry injected, less NH3, more N2O).

Written (capri_data/2017/environment/):
  manure_n2o_factors.csv  region, animal, f_man, f_app, f_gra, f_lea: t N2O-N per t of manure N (CAPRI 2017
                          res_17: N2O items over MANN, CAPRI activities aggregated to the model's animals with
                          manure N x level weights; model regions take their CAPRI region, else the national row)
  manure_n2o_tech.csv     region, animal, technology, r_hou, r_app: CAPRI's relative reduction of housing and
                          storage (r_hou, applied to N2OMAN: CAPRI gives it as N2OHOU, used only for the
                          options its housing equation HOUSN_ sums) and application N2O per unit adopting
                          the option, weighted over the animal's sub-activities as in ammonia_tech_model.csv
                          (weight x manure N); combined options take their cover's effect

    python tools/build/build_manure_n2o.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, json, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ITEMS = ("LEVL", "MANN", "N2OMAN", "N2OAPP", "N2OGRA", "N2OLEA")
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Z0-9]+)'\.'(" + "|".join(ITEMS) + r")'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")
N2ON = 28.0 / 44.0
COMBO_BASE = {"AirPurCovHigh": "CovStorHigh", "AirPurCovLow": "CovStorLow"}
#: the options CAPRI's housing equation applies (supply_model.gms HOUSN_): manure-management N2O is
#: computed at housing level (ammo_tech.gms moves the storage options' N2OSTO effects to N2OHOU), but
#: HOUSN_ sums only these options - the plain storage covers (CovStorLow, CovStorHigh) carry an N2OHOU
#: effect in the data that the equation never uses, so in CAPRI a cover does not cut manure N2O
HOUSN_OPTIONS = {"LowEmHous", "AirPur", "AirPurCovLow", "AirPurCovLowC", "AirPurCovHigh", "ManAcid"}


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    a = ap.parse_args()
    c2m = _load(ROOT / "tools" / "build" / "build_livestock_output_coef.py").CAPRI_TO_MODEL
    v = defaultdict(lambda: defaultdict(dict))
    for f in glob.glob(str(a.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = ROW.match(line)
            if m and m.group(2) in c2m:
                v[m.group(1)][m.group(2)][m.group(3)] = float(m.group(4))
    mr = _load(ROOT / "tools" / "lib" / "_model_regions.py")
    corr = json.loads((ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    import importlib.util as _ilu_
    _sp_ = _ilu_.spec_from_file_location("_mr_", ROOT / "tools" / "lib" / "_model_regions.py")
    _mr_ = _ilu_.module_from_spec(_sp_); _sp_.loader.exec_module(_mr_)
    to_c8 = _mr_.region_to_capri()          # correspondence + NUTS splits and merges (tools/lib/_model_regions.py)

    rows = []
    for reg in mr.model_regions():
        c8 = to_c8.get(reg)
        for src in (c8, mr.national_code(reg)):
            if src and src in v:
                break
        else:
            continue
        agg = defaultdict(lambda: defaultdict(float))
        for act, d in v[src].items():
            L, M = d.get("LEVL", 0.0), d.get("MANN", 0.0)
            if L <= 0 or M <= 0:
                continue
            ma = c2m[act]
            agg[ma]["N"] += L * M
            for it in ("N2OMAN", "N2OAPP", "N2OGRA", "N2OLEA"):
                agg[ma][it] += L * d.get(it, 0.0) * N2ON
        for ma, s in agg.items():
            if s["N"] > 0:
                rows.append({"region": reg, "animal": ma, "capri_region": src,
                             "f_man": s["N2OMAN"] / s["N"], "f_app": s["N2OAPP"] / s["N"],
                             "f_gra": s["N2OGRA"] / s["N"], "f_lea": s["N2OLEA"] / s["N"]})
    fac = pd.DataFrame(rows)

    # technology effects on N2O
    amm = ROOT / "capri_data" / "2017" / "abatement" / "ammonia"
    eff = pd.read_csv(amm / "ammonia_technology_effects.csv")
    eff = eff[eff["item"].isin(["N2OHOU", "N2OAPP"])]
    lit = pd.read_csv(amm / "p_litRevAmmoTechsAdd.csv")
    lit = lit[lit["item"].isin(["N2OHOU", "N2OAPP"]) & (lit["technology"] == "ManAcid")]
    lit = lit.groupby(["region", "technology", "activity", "item"], as_index=False)["value"].mean()
    E = {(r.region, r.activity, r.technology, r.item): float(r.reduction) for r in eff.itertuples()}
    for r in lit.itertuples():
        E[(r.region, r.activity, r.technology, r.item)] = float(r.value)
    tm = pd.read_csv(amm / "ammonia_tech_model.csv")
    out = defaultdict(lambda: [0.0, 0.0, 0.0])       # (region, animal, tech) -> [w, w r_hou, w r_app]
    for r in tm.itertuples():
        creg, cact = str(r.sub).split("|")
        w = float(r.weight) * float(r.mann_rel)
        t = COMBO_BASE.get(r.technology, r.technology)
        rh = E.get((creg, cact, t, "N2OHOU"), E.get((creg[:2] + "000000", cact, t, "N2OHOU"), 0.0)) \
            if r.technology in HOUSN_OPTIONS else 0.0
        ra = E.get((creg, cact, t, "N2OAPP"), E.get((creg[:2] + "000000", cact, t, "N2OAPP"), 0.0))
        o = out[(r.region, r.animal, r.technology)]
        o[0] += w; o[1] += w * rh; o[2] += w * ra
    tech = pd.DataFrame([{"region": k[0], "animal": k[1], "technology": k[2], "r_hou": v_[1] / v_[0], "r_app": v_[2] / v_[0]}
                         for k, v_ in out.items() if v_[0] > 0])
    tech = tech[(tech["r_hou"].abs() > 1e-9) | (tech["r_app"].abs() > 1e-9)]
    dest = ROOT / "capri_data" / "2017" / "environment"
    fac.to_csv(dest / "manure_n2o_factors.csv", index=False, float_format="%.6g")
    tech.to_csv(dest / "manure_n2o_tech.csv", index=False, float_format="%.6g")
    tot = fac[["f_man", "f_app", "f_gra", "f_lea"]].sum(axis=1)
    print(f"manure_n2o_factors.csv: {len(fac)} rows, {fac.region.nunique()} regions; direct N2O-N / manure N median "
          f"{tot.median():.4f} (model's flat factor 0.02); manure_n2o_tech.csv: {len(tech)} rows; median effects "
          + ", ".join(f"{t} hou {g.r_hou.median():+.2f} app {g.r_app.median():+.2f}" for t, g in tech.groupby("technology")))


if __name__ == "__main__":
    main()
