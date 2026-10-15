"""CAPRI's emission side effects of nitrification inhibitors on mineral fertiliser, per model region.

CAPRI's literature review (dat/scen/ghgtech/LitRevFertTech.gdx, p_litRevFertTechs, from
prep_data_LitRev.gms) gives, per region, the relative change in emissions of a hectare fertilised
with the option against one without it: nitrification inhibitors on mineral N cut N2O by about 19%
and NOx by 19%, and raise NH3 by about 12% (negative value = increase). envind/ghgMiti.gms
(l. 552-555) turns this into the option's change of the emission factor per kg of N, since the
option's N saving (othImpact NMIN) is counted apart:

    EF(option) / EF(NOC) = (1 - lit) x (1 + NMIN)

NOx (NOXSYN) is not carried: the model keeps no NOx account. Nitrate leaching and runoff effects (NO3SLEA, NO3SRUN) are zeroed in CAPRI unless leaching is
endogenous (%endoLeach%, off in the Green Deal runs) and are not carried. 
Inhibitors on applied manure (technology NITR_INH_MAN here): CAPRI's entries per animal and
manure system (N2OAPP, NH3APP) enter ghgMiti.gms l. 557-563 weighted by the animals' manure N and
their liquid/solid shares. NH3APP is the same for every animal and system (-0.2505: +25% NH3 from
treated manure at application), so the weighting does not matter there; N2OAPP differs a little
by system and is written as the plain mean (the model keeps no manure-application N2O account, so
it is recorded, not used - REGISTERED). Fertiliser timing on manure (FERTTIME) is not carried: the
model has no such option.

Source: capri_data/sources/ghgtech/LitRevFertTech_p_litRevFertTechs.csv (the records used, from the
gdxdump of the installation's LitRevFertTech.gdx; the full dump is the .txt beside it). Model regions take their CAPRI region, else the national entry,
else (multi-region countries whose model region has no CAPRI counterpart: city states, recent NUTS
splits, Norway) the median over the country's CAPRI regions (REGISTERED; the values vary little
within a country).
Output: capri_data/2017/abatement/fert_side_effects.csv (region, technology, item, value)

    python tools/build_fert_side_effects.py
"""
from __future__ import annotations
import importlib.util, json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ("N2OSYN", "NH3SYN")
MAN_ITEMS = ("NH3APP", "N2OAPP")


def main():
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    raw = pd.read_csv(ROOT / "capri_data" / "sources" / "ghgtech" / "LitRevFertTech_p_litRevFertTechs.csv")
    m = raw[(raw["system"] == "Mineral") & raw["item"].isin(ITEMS)][["region", "technology", "item", "value"]]
    mm = raw[(raw["technology"] == "NITR_INH") & raw["system"].isin(["LIQUID", "SOLID"]) & raw["item"].isin(MAN_ITEMS)]
    mm = mm.groupby(["region", "item"], as_index=False)["value"].mean().assign(technology="NITR_INH_MAN")
    d = pd.concat([m, mm[["region", "technology", "item", "value"]]], ignore_index=True)
    KEYS = [(t, i) for t in sorted(set(m["technology"])) for i in ITEMS] + [("NITR_INH_MAN", i) for i in MAN_ITEMS]
    val = {(r.region, r.technology, r.item): float(r.value) for r in d.itertuples()}
    corr = json.loads((ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    import importlib.util as _ilu_
    _sp_ = _ilu_.spec_from_file_location("_mr_", ROOT / "tools" / "_model_regions.py")
    _mr_ = _ilu_.module_from_spec(_sp_); _sp_.loader.exec_module(_mr_)
    to_c8 = _mr_.region_to_capri()          # correspondence + NUTS splits and merges (tools/_model_regions.py)
    med = d.assign(ms=d["region"].str[:2]).groupby(["ms", "technology", "item"])["value"].median().to_dict()
    rows, n_reg, n_nat, n_med = [], 0, 0, 0
    for reg in mr.model_regions():
        for src, kind in ((to_c8.get(reg), "regional"), (mr.national_code(reg), "national")):
            if src and all((src, t, i) in val for t, i in KEYS):
                for t, i in KEYS:
                    rows.append((reg, t, i, val[(src, t, i)], src))
                n_reg += kind == "regional"; n_nat += kind == "national"
                break
        else:
            ms = mr.national_code(reg)[:2]
            if all((ms, t, i) in med for t, i in KEYS):
                for t, i in KEYS:
                    rows.append((reg, t, i, med[(ms, t, i)], ms + " median"))
                n_med += 1
    out = pd.DataFrame(rows, columns=["region", "technology", "item", "value", "capri_region"])
    dest = ROOT / "capri_data" / "2017" / "abatement" / "fert_side_effects.csv"
    out.to_csv(dest, index=False, float_format="%.6g")
    print(f"wrote {dest.name}: {out.region.nunique()} regions ({n_reg} regional, {n_nat} national entries, {n_med} country medians); "
          + ", ".join(f"{i} median {out[out.item == i].value.median():+.3f}" for i in ITEMS + MAN_ITEMS))


if __name__ == "__main__":
    main()
