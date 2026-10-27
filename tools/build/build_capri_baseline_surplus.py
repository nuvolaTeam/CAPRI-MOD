"""CAPRI's own baseline gross N surplus per ha (2030 reference), per model region: the starting point
of the Farm-to-Fork tiered nitrogen target (JRC121368, CAPRI pol_input/greendeal/surptot.gms).

CAPRI applies the tiered rule per CAPRI region, to its own surplus (dataOut perHa.SURTOT.NITF). The model's
regions are CAPRI's regional units (27 October 2026), so each takes its own CAPRI value; a unit without one takes
its member state's (REGISTERED).

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


def main():
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    g = _read_csv(ROOT / "capri_data" / "2017" / "environment" / "capri_gnb_components_2030.csv")
    sur = g[g["item"] == "SURTOT"].set_index("capri_region")["kg_n_per_ha"].astype(float)
    t = _read_csv(ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_marginal_terms_ini_2030.csv.xz",
                    header=None, names=["region", "act", "item", "value"], dtype=str)
    t = t[(t["act"] == "UAAR") & (t["item"] == "LEVL")]
    uaar = pd.to_numeric(t.set_index("region")["value"], errors="coerce")
    # the model's regions are CAPRI's regional units: each takes its own row (until 27 October 2026 NUTS-2016 regions,
    # through the NUTS correspondence, merges UAAR-weighted and split parts taking their parent's value)
    to_capri = {r: {r} for r in mr.model_regions() if r in sur.index}

    rows = []
    for reg in mr.model_regions():
        src = sorted(to_capri.get(reg, ()))
        if src:
            w = [float(uaar.get(c, 0.0)) if pd.notna(uaar.get(c)) else 0.0 for c in src]
            if sum(w) <= 0:
                w = [1.0] * len(src)
            v = sum(wi * float(sur[c]) for wi, c in zip(w, src)) / sum(w)
            how = ("CAPRI 2030 reference, NUTS-2 " + "+".join(src) + (" UAAR-weighted" if len(src) > 1 else "")
                   )
        else:
            ms = mr.national_code(reg)
            if ms not in sur.index:
                rows.append({"region": reg, "surplus_kg_n_per_ha": float("nan"),
                             "source": "no CAPRI value (model's own balance used)"})
                continue
            v = float(sur[ms])
            multi = any(ms[:2] == c[:2] and mr.regional_row(c) and c != ms for c in sur.index)
            how = (f"CAPRI 2030 reference, national {ms} (region not modelled by CAPRI; REGISTERED)" if multi
                   else f"CAPRI 2030 reference, {ms} (CAPRI holds the country as one region)")
        rows.append({"region": reg, "surplus_kg_n_per_ha": v, "source": how})
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
