"""CAPRI's fertiliser coefficients per model region and crop: NITF, PHOF, POTF of CAPRI's 2017 results on the model's
activities (KNOWN_ISSUES K100).

The supply models' nutrient coefficients (RegionData.nutrient_coefs: the nutrient balance of the supply result, the
organic and fertiliser-technology instruments' scaling of the N column) were a national table without builder
(nutrient_coefs.csv, one value per crop for every region) overridden by CAPRI's regional extract
(sources/capreg/capreg_nutrient_coefs.csv, tools/build/extract_all_from_data2.py) where the extract has the model's code.
The extract is keyed by CAPRI's activities, so the model's OFOD (CAPRI's OFAR + ROOF), SETA (SETA + FALL) and WINE (TWIN)
never matched and kept the national values in every region. This builder writes the coefficients on the model's
activities, as tools/build/build_crop_economics_2017.py does for yields and costs (build_capri_base.CROP_MAP):

    coefficient(region, crop, item) = sum_a LEVL_a x item_a / sum_a LEVL_a     (kg per ha; a the crop's CAPRI activities)

over the region's CAPRI activities with a level; a crop the region does not grow takes its member state's CAPRI values
(the national row of the same dumps), as the yields and costs; a crop CAPRI has nowhere in the member state gets no
row. CAPRI's items: NITF (N), PHOF (P2O5), POTF (K2O), CAPRI's fertiliser need per ha (DATA2 of res_17<MS>; CAPRI's
NITF equals NRET, the N requirement, not the mineral N applied, NMIN: nutrients_regional.csv).

Output: capri_data/2017/supply/nutrient_coefs_regional.csv (region, activity, N, P2O5, K2O), the one writer.

    python tools/build/build_nutrient_coefs_regional.py [dump dir, default /home/claude/work/capreg]
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
import build_capri_base as B  # noqa: E402
from _model_regions import CTRY as MS_CODE  # noqa: E402  CAPRI member-state codes (capri_member_state_codes.csv)

OUT = ROOT / "capri_data" / "2017" / "supply" / "nutrient_coefs_regional.csv"
#: CAPRI's DATA2 fertiliser items and the model's nutrient names (extract_all_from_data2.NUTRIENT_ITEMS)
ITEMS = {"NITF": "N", "PHOF": "P2O5", "POTF": "K2O"}


def read(dump_dir: Path) -> dict:
    """{CAPRI region: {item: {activity: value}}} of LEVL and the fertiliser items of every dump ('Y' column)."""
    out: dict = defaultdict(lambda: defaultdict(dict))
    keep = {"LEVL", *ITEMS}
    for path in sorted(dump_dir.glob("res_17*.txt")):
        for line in open(path, errors="ignore"):
            m = B._ROW.match(line)
            if m and m.group(3) in keep:
                out[m.group(1)][m.group(3)][m.group(2)] = B._num(m.group(4))
    return out


def national(reg: str) -> str:
    return MS_CODE.get(reg[:2], reg[:2]) + "000000"


def coefficients(capri: dict, code: str, acts) -> dict | None:
    """{nutrient: kg/ha} of the level-weighted CAPRI activities acts in CAPRI region code, None without a level."""
    it = capri.get(code, {})
    lv = {a: it.get("LEVL", {}).get(a, 0.0) for a in acts}
    den = sum(v for v in lv.values() if v > 0)
    if den <= 0:
        return None
    return {n: sum(l * it.get(item, {}).get(a, 0.0) for a, l in lv.items() if l > 0) / den for item, n in ITEMS.items()}


def main(dump_dir: Path) -> None:
    capri = read(dump_dir)
    regs = B.units()
    missing = [r for r in regs if r not in capri]
    assert not missing, f"no CAPRI rows for {missing}"
    rows, n_reg, n_nat = [], 0, 0
    for reg in regs:
        for col, acts in B.CROP_MAP.items():
            v = coefficients(capri, reg, acts)
            if v is None:
                v = coefficients(capri, national(reg), acts)
                n_nat += v is not None
            else:
                n_reg += 1
            if v is None:
                continue
            rows.append({"region": reg, "activity": col, **v})
    df = pd.DataFrame(rows, columns=["region", "activity", *ITEMS.values()])
    df.to_csv(OUT, index=False)
    print(f"{OUT.name}: {len(df)} rows, {df.region.nunique()} regions, {df.activity.nunique()} crops "
          f"({n_reg} from the region's CAPRI activities, {n_nat} from the member state's)")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/claude/work/capreg"))
