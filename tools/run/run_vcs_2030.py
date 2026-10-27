"""Supply-response test: CAPRI's 2030 run without voluntary coupled support (VCS).

CAPRI's pair (tools/build/extract_capri_vcs_pair.py -> capri_data/validation/coupled_support_2030/
capri_vcs_effect.csv): cap_after_2014 reference and the same run with voluntaryCoupledSupportFile =
void.gms. Removing VCS cuts the premium on suckler cows by 82%, on bulls by 59%, on dairy cows by
44%, on pulses by 20% and on sugar beet by 19%, while the envelope moves into the decoupled
payment (cereal premiums per ha +9 to +11%).

The test applies CAPRI's relative change of the premium per unit (PRME without VCS / PRME in the
reference), per CAPRI region and activity, to the model's 2030 baseline premiums, and compares the
EU response with CAPRI's. Model activities aggregate CAPRI's with their reference levels:
factor = sum L PRME_novcs / sum L PRME_ref. Model regions take their CAPRI region, else the
national row (as in the other builders).

    python tools/run/run_vcs_2030.py OUT.pkl [--verbose]
"""
from __future__ import annotations
import os as _os
import sys as _sys
# reproducible runs: the model iterates sets of names in a few places, and Python randomises string hashing per
# process, which changed results by up to ~0.2% between two runs of the same scenario (degenerate regions more).
# A fixed hash seed makes a run repeat exactly (Sprint 9n).
if _os.environ.get("PYTHONHASHSEED") != "0":
    _os.environ["PYTHONHASHSEED"] = "0"
    _os.execv(_sys.executable, [_sys.executable] + _sys.argv)
import argparse, importlib.util, json, pickle, sys, time, warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]

#: indicators compared: model key -> CAPRI (region EU27yr19) activity or product
HERDS = {"DCOW": "DCOW", "BCOW": "SCOW", "BULL": "BULF", "HFRS": "HEIF", "SHGM": "SHGM", "SHGF": "SHGF",
         "PIGF": "PIGF", "LAYS": "HENS", "BROI": "POUF"}
CROPS_ = {"PULS": "PULS", "SOYA": "SOYA", "SUGB": "SUGB", "DWHE": "DWHE", "SWHE": "SWHE", "CORN": "MAIZ",
          "BARL": "BARL", "RAPE": "RAPE", "SUNF": "SUNF", "TOMA": "TOMA", "GRAS": "GRAS", "MAIF": "MAIF"}
#: the model's young-animal goods (tools/build/build_young_animals.py) -> CAPRI's products
YANI = {"calves": ("YCAM", "YCAF"), "young": ("YBUL", "YHEI"), "cows": "YCOW", "piglets": "YPIG", "lambs": "YLAM"}
PRICES = {"BEEF": "BEEF", "MILK": "COMI", "SGMT": "SGMT", "PORK": "PORK", "PULS": "PULS", "SOYA": "SOYA",
          "SUGB": "SUGB", "DWHE": "DWHE", "SWHE": "SWHE"}


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def premium_factors(regions):
    eff = _read_csv(ROOT / "capri_data" / "validation" / "coupled_support_2030" / "capri_vcs_effect.csv.xz")
    prme = eff[eff["item"] == "PRME"].set_index(["region", "activity"])[["ref", "novcs"]]
    levl = eff[eff["item"] == "LEVL"].set_index(["region", "activity"])["ref"]
    mr = _load(ROOT / "tools" / "lib" / "_model_regions.py")
    base = _load(ROOT / "tools" / "build" / "build_capri_base.py")
    lsk = _load(ROOT / "tools" / "build" / "build_livestock_output_coef.py").CAPRI_TO_MODEL
    model_of = defaultdict(list)
    for col, acts in base.CROP_MAP.items():
        for a in acts:
            model_of[col].append(a)
    for ca, ma in lsk.items():
        model_of[ma].append(ca)
    corr = json.loads((ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    to_c8 = {}
    for c8, lst in corr.items():
        if not c8.endswith("000000"):
            for r in lst:
                to_c8.setdefault(r, c8)
    have = set(prme.index.get_level_values(0))
    out = {}
    for reg in regions:
        src = to_c8.get(reg) if to_c8.get(reg) in have else mr.national_code(reg)
        if src not in have:
            continue
        f = {}
        for ma, cas in model_of.items():
            num = den = 0.0
            for ca in cas:
                if (src, ca) not in prme.index:
                    continue
                L = float(levl.get((src, ca), 0.0) or 0.0)
                p0, p1 = prme.loc[(src, ca)]
                if L > 0 and pd.notna(p0) and pd.notna(p1) and p0 > 0:
                    num += L * float(p1); den += L * float(p0)
            if den > 0:
                f[ma] = num / den
        if f:
            out[reg] = f
    return out


def capri_eu(eff, item, acts):
    e = eff[(eff["region"] == "EU27yr19") & (eff["item"] == item)].set_index("activity")
    out = {}
    for k, a in acts.items():
        a = a if isinstance(a, tuple) else (a,)
        r0 = sum(float(e.at[x, "ref"]) for x in a if x in e.index and pd.notna(e.at[x, "ref"]))
        r1 = sum(float(e.at[x, "novcs"]) for x in a if x in e.index and pd.notna(e.at[x, "novcs"]))
        out[k] = 100 * (r1 / r0 - 1) if r0 > 0 else float("nan")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(ROOT))
    from capri_mod.model import CAPRIModel
    from capri_mod.projection import ProjectionModule, BaselineTrajectory
    from capri_mod.policy.policy_module import PolicyScenario
    from capri_mod import settings as _S
    if a.verbose:
        _S.activate(_S.current().replace({"diagnostics.trace_outer": True}))
    m = CAPRIModel(data_dir=str(ROOT / "capri_data"), verbose=False)
    t0 = time.time()
    fac = premium_factors(list(m.data["areas"].index))
    scen = PolicyScenario(name="WITHOUT_VCS", description="CAPRI cap_after_2014 without voluntary coupled support",
                          premium_factor_regional=fac)
    traj = BaselineTrajectory.from_file(str(ROOT / "capri_data" / "trajectories" / "captrd_2030.json"))
    pmod = ProjectionModule(m, traj, capri_prices_dir=str(ROOT / "capri_data" / "trajectories"))
    res = pmod.run(policy_scenario=scen, years=[2030])
    b, s = res.baseline[2030], res.scenario[2030]

    def agg(r):
        o = {}
        for v in r["supply"].values():
            for k, x in v.activities.items():
                if np.isfinite(x):
                    o[k] = o.get(k, 0.0) + float(x)
        return o
    ab, as_ = agg(b), agg(s)
    db, ds = b["market"].domestic_prices.loc["EU27"], s["market"].domestic_prices.loc["EU27"]
    eff = _read_csv(ROOT / "capri_data" / "validation" / "coupled_support_2030" / "capri_vcs_effect.csv.xz")
    rows = []
    for k, ref in capri_eu(eff, "LEVL", HERDS).items():
        rows.append(("herd", k, 100 * (as_.get(k, 0) / ab[k] - 1) if ab.get(k) else np.nan, ref))
    for k, ref in capri_eu(eff, "LEVL", CROPS_).items():
        rows.append(("area", k, 100 * (as_.get(k, 0) / ab[k] - 1) if ab.get(k) else np.nan, ref))
    pe = eff[(eff["region"] == "EU27yr19") & (eff["item"] == "UVAP")].set_index("activity")
    for k, c in PRICES.items():
        ref = 100 * (float(pe.at[c, "novcs"]) / float(pe.at[c, "ref"]) - 1) if c in pe.index else np.nan
        mod = 100 * (float(ds[k]) / float(db[k]) - 1) if k in db.index and db[k] > 0 else np.nan
        rows.append(("price", k, mod, ref))
    # YOUNG-ANIMAL PRICES (CAPRI clears them in its market, yaniMarket_; here per market region): the model's price
    # ratio in the scenario over the baseline's, against CAPRI's UVAG change (a good of two CAPRI products: the
    # change of the sum of their unit values)
    yb = (b.get("metadata", {}) or {}).get("young_animal_markets") or {}
    ys = (s.get("metadata", {}) or {}).get("young_animal_markets") or {}
    for k, c in YANI.items():
        ref = capri_eu(eff, "UVAG", {k: c})[k]
        kk = f"EU27|{k}"
        # the ratio is to the baseline's price (1 where the baseline records no clearing of its own)
        r0 = float(yb[kk][0]) if kk in yb else 1.0
        mod = 100 * (float(ys[kk][0]) / r0 - 1) if kk in ys and r0 != 0 else np.nan
        rows.append(("young animal price", k, mod, ref))
    tab = pd.DataFrame(rows, columns=["kind", "indicator", "model", "capri"])
    tab["diff"] = tab["model"] - tab["capri"]
    md = s.get("metadata", {}) or {}
    pd.set_option("display.width", 200)
    print(tab.round(2).to_string(index=False))
    ok = tab[tab["kind"] != "young animal price"].dropna()
    print(f"mean absolute deviation from CAPRI ({len(ok)} indicators, young-animal prices aside): {ok['diff'].abs().mean():.2f} points; "
          f"correlation {np.corrcoef(ok['model'], ok['capri'])[0, 1]:+.2f}")
    pickle.dump({"table": tab, "act": (ab, as_), "factors": fac, "young_animal_markets": (yb, ys),
                 "meta": {"conv": md.get("outer_converged"), "it": md.get("n_outer_iterations"),
                          "seconds": round(time.time() - t0)}}, open(a.out, "wb"))
    print(f"saved {a.out} | converged {md.get('outer_converged')} in {md.get('n_outer_iterations')} iterations, "
          f"{round(time.time() - t0)} s")


if __name__ == "__main__":
    main()
