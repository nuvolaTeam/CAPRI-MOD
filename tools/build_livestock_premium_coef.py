"""CAPRI's livestock premiums per MODEL head (per region and model animal).

CAPRI's PRME (DATA2, EUR per activity unit; capreg_cap_premium.csv) is attached to its
own activities (SCOW, BULF, HEIF/HEIR, CAMF/CAFF/CAMR/CAFR, SOWS/PIGF, HENS, POUF,
SHGM/SHGF). The model looked premiums up by its own names (BCOW, HFRS, CALV, ...), so
every animal but dairy cows and bulls had NO premium - suckler cows lost EUR 117-121 per
head in France - and the per-unit values were on CAPRI's activity basis, not the model's
census heads. As for revenue and costs (build_livestock_output_coef.py), the coefficient
is CAPRI's regional total (LEVL x PRME, capreg_activity_levels.csv) / the model's heads.

Output: capri_data/2017/supply/livestock_premium_coef.csv (EUR per model head)
Usage:  python tools/build_livestock_premium_coef.py [<dir with res_17<CC>.txt dumps>]
"""
import importlib.util
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_sp = importlib.util.spec_from_file_location("_loc", ROOT / "tools" / "build_livestock_output_coef.py")
_loc = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_loc)
CAPRI_TO_MODEL = _loc.CAPRI_TO_MODEL


def main():
    import sys
    sys.path.insert(0, str(ROOT))
    from capri_mod.data.loaders import load_all_data
    herds = load_all_data(str(ROOT / "capri_data"))["animal_numbers"]
    src = ROOT / "capri_data" / "sources" / "capreg"
    lev = pd.read_csv(src / "capreg_activity_levels.csv", index_col=0)
    prm = pd.read_csv(src / "capreg_cap_premium.csv", index_col=0)
    tot = defaultdict(float)
    for reg in prm.index.intersection(lev.index):
        for ca, ma in CAPRI_TO_MODEL.items():
            if ca in prm.columns and ca in lev.columns:
                p_, l_ = prm.at[reg, ca], lev.at[reg, ca]
                if pd.notna(p_) and pd.notna(l_):
                    tot[(reg, ma)] += float(p_) * float(l_)
    acts = sorted(set(CAPRI_TO_MODEL.values()))
    out = pd.DataFrame(index=sorted(herds.index), columns=acts, dtype=float)
    for (reg, ma), t in tot.items():
        if reg in herds.index and ma in herds.columns and float(herds.at[reg, ma]) > 0:
            out.at[reg, ma] = t / float(herds.at[reg, ma])
    # first choice: the res_17 dumps through the output-coefficient builder (national rows and
    # residual allocation for regions without a regional CAPRI entry); this table fills the rest
    dump_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if dump_dir is not None and dump_dir.exists():
        dm = _loc.build(dump_dir, "PRME").reindex(index=out.index, columns=out.columns)
        out = dm.combine_first(out)
    dest = ROOT / "capri_data" / "2017" / "supply" / "livestock_premium_coef.csv"
    out.to_csv(dest)
    print(f"wrote {dest.name}: {out.notna().sum().to_dict()}")
    print(out.median().round(1).to_dict())


if __name__ == "__main__":
    main()
