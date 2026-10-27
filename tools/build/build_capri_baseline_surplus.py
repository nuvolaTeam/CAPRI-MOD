"""CAPRI's own baseline gross N surplus per ha (2030 reference), per model region: the starting point
of the Farm-to-Fork tiered nitrogen target (JRC121368, CAPRI pol_input/greendeal/surptot.gms).

CAPRI applies the tiered rule per CAPRI region, to its own surplus (dataOut perHa.SURTOT.NITF). This
builder takes that value for every model region from CAPRI's regional results:

  1. the CAPRI region(s) whose NUTS codes (shared/nuts_version_correspondence.json, old and new
     NUTS versions) include the model region: their SURTOT, weighted by CAPRI's UAAR where several
     CAPRI regions make up one model region (FI1D = FI13 + FI1A in NUTS 2013);
  2. otherwise the member state's CAPRI value - where CAPRI itself holds the country as one region
     (Denmark, Lithuania, Slovenia, Croatia), that IS the region CAPRI applies the target to;
  3. otherwise (city regions CAPRI does not model: Berlin, Bremen, Hamburg, Vienna, Brussels, Ceuta,
     Melilla) the member state's value as well, REGISTERED.

The earlier file (capri_baseline_surplus_2030.csv, 2026-10) matched only new-NUTS CAPRI codes and gave
82 regions their own surplus pattern scaled to the national value - a proxy that badly misplaced the
cut where CAPRI uses old codes (Italy, Belgium-Luxembourg, Sweden, Finland): Valle d'Aosta took 250
kg N/ha (CAPRI 48.5) and a 70% cut instead of 26%, Luxembourg 235 (CAPRI 157), Swedish regions ~100
(CAPRI 70-79), and the nine capped regions were chosen from the proxied ranking.

Sources: capri_data/2017/environment/capri_gnb_components_2030.csv (SURTOT, from CAPRI's
res_2_1730greendeal_refdefaulta), capri_data/validation/greendeal_2030/capri_marginal_terms_ini_2030.csv.xz
(UAAR LEVL, weights).
Output: capri_data/2017/policy/capri_baseline_surplus_2030.csv (region, surplus_kg_n_per_ha, source)

    python tools/build/build_capri_baseline_surplus.py
"""
from __future__ import annotations
import importlib.util, json
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
#: NUTS splits and merges, shared with the other builders: tools/lib/_model_regions.py SPLITS_MERGES


def main():
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    g = _read_csv(ROOT / "capri_data" / "2017" / "environment" / "capri_gnb_components_2030.csv")
    sur = g[g["item"] == "SURTOT"].set_index("capri_region")["kg_n_per_ha"].astype(float)
    t = _read_csv(ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_marginal_terms_ini_2030.csv.xz",
                    header=None, names=["region", "act", "item", "value"], dtype=str)
    t = t[(t["act"] == "UAAR") & (t["item"] == "LEVL")]
    uaar = pd.to_numeric(t.set_index("region")["value"], errors="coerce")
    corr = json.loads((ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    corr = {**corr, **mr.CORR_FIXES}
    SPLITS_MERGES = mr.SPLITS_MERGES
    to_capri = defaultdict(set)
    for c8, lst in corr.items():
        if c8.endswith("000000") or c8 not in sur.index:
            continue
        for r in lst or []:
            to_capri[r].add(c8)
    # NUTS changes the correspondence leaves out (it keeps one CAPRI code -> one model region only
    # where the areas match): merges take CAPRI's regions UAAR-weighted, splits take the parent
    # CAPRI region's surplus per ha - the region CAPRI sets the target on, so its percentage cut
    for reg, parents in SPLITS_MERGES.items():
        if all(p in sur.index for p in parents) and not to_capri.get(reg):
            to_capri[reg] = set(parents)

    rows = []
    for reg in mr.model_regions():
        src = sorted(to_capri.get(reg, ()))
        if src:
            w = [float(uaar.get(c, 0.0)) if pd.notna(uaar.get(c)) else 0.0 for c in src]
            if sum(w) <= 0:
                w = [1.0] * len(src)
            v = sum(wi * float(sur[c]) for wi, c in zip(w, src)) / sum(w)
            how = ("CAPRI 2030 reference, NUTS-2 " + "+".join(src) + (" UAAR-weighted" if len(src) > 1 else "")
                   + (" (NUTS split/merge)" if reg in SPLITS_MERGES else ""))
        else:
            ms = mr.national_code(reg)
            if ms not in sur.index:
                rows.append({"region": reg, "surplus_kg_n_per_ha": float("nan"),
                             "source": "no CAPRI value (model's own balance used)"})
                continue
            v = float(sur[ms])
            multi = any(ms[:2] == c[:2] and not c.endswith("000000") for c in sur.index)
            how = (f"CAPRI 2030 reference, national {ms} (region not modelled by CAPRI; REGISTERED)" if multi
                   else f"CAPRI 2030 reference, {ms} (CAPRI holds the country as one region)")
        rows.append({"region": reg, "surplus_kg_n_per_ha": round(v, 2), "source": how})
    out = pd.DataFrame(rows)
    dest = ROOT / "capri_data" / "2017" / "policy" / "capri_baseline_surplus_2030.csv"
    old = _read_csv(dest).set_index("region")["surplus_kg_n_per_ha"] if dest.exists() else None
    out.to_csv(dest, index=False)
    kinds = out["source"].str.extract(r"^(CAPRI 2030 reference, NUTS-2|CAPRI 2030 reference, national|"
                                      r"CAPRI 2030 reference, [A-Z]{2}000000|no CAPRI)")[0].value_counts()
    print(f"wrote {dest.name}: {len(out)} regions\n{kinds.to_string()}")
    if old is not None:
        o = out.set_index("region")["surplus_kg_n_per_ha"]
        d = (o - old.reindex(o.index)).abs().sort_values(ascending=False)
        print("largest changes:", ", ".join(f"{r} {old.get(r):.0f}->{o[r]:.0f}" for r in d.index[:12] if d[r] == d[r]))
    print("nine highest:", ", ".join(f"{r} {v:.0f}" for r, v in
                                     out.set_index("region")["surplus_kg_n_per_ha"].dropna().sort_values(ascending=False).head(10).items()))


if __name__ == "__main__":
    main()
