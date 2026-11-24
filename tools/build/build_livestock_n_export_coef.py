"""CAPRI's nitrogen exported in animal products per model head (capri_data/2017/environment/livestock_n_export_coef.csv).

CAPRI's item CRPR_EXPT (kg N per unit of activity: fert/calc_nexport.gms - N in meat by liveweight and carcass ratio,
in milk at 0.0054 kg N per kg, in young animals sold less bought, in eggs, ...), 2017 results (res_17* dumps),
summed as CRPR_EXPT x LEVL over the CAPRI activities of each model animal and divided by the model's herd, per group
of CAPRI and model regions covering the same territory - the construction of livestock_manure_n_coef.csv (MANN) by
tools/build/build_livestock_output_coef.build. Used for the report item n_animal_products (until 23 October 2026: 25% of
excreted N; PROXY_AUDIT S199). The 2030 market year takes CAPRI's 2030 values (tools/build/build_livestock_n_export_2030.py).

The bulls and heifers take CAPRI's elementary activities (BULL, BULH; HEIL, HEIH, HEIR), not the aggregates BULF and
HEIF of build_livestock_output_coef.CAPRI_TO_MODEL (KNOWN_ISSUES K202): in res_17 the aggregates' CRPR_EXPT is the
LEVL-weighted mean of their members' per unit, while their LEVL is not the members' sum, so LEVL x CRPR_EXPT of BULF is
0.606 of the members' sum and of HEIF 0.617 at the median (their BEEF, MANN, MANP, ENNE, feed, TOIN, TOOU and PRME add
up). Until 24 November 2026 the bulls' and the fattening heifers' N in products was taken from the aggregates.

    python tools/build/build_livestock_n_export_coef.py [--dump-dir capri_sources/capreg]
"""
import argparse
import glob
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)

ROOT = Path(__file__).resolve().parents[2]
#: the bulls' and heifers' CAPRI activities of the N in products: the elementary ones (the module docstring)
ELEMENTARY = {"BULL": ("BULL", "BULH"), "HFRS": ("HEIL", "HEIH", "HEIR")}


def capri_activities(c2m: dict) -> dict:
    """CAPRI activity -> model animal: build_livestock_output_coef.CAPRI_TO_MODEL with the bulls' and heifers'
    elementary activities (ELEMENTARY) in place of theirs."""
    out = {ca: ma for ca, ma in c2m.items() if ma not in ELEMENTARY}
    for ma, acts in ELEMENTARY.items():
        out.update({ca: ma for ca in acts})
    return out


def totals_2017(B, dump_dir: Path, acts: dict) -> dict:
    """{(8-character region, model animal): sum of LEVL x CRPR_EXPT over the animal's CAPRI activities, t N} of res_17."""
    tot = defaultdict(float)
    for path in sorted(glob.glob(str(dump_dir / "res_17*.txt"))):
        lv, ce = {}, {}
        for line in open(path, errors="ignore"):
            m = B._ROW.match(line)
            if not m or m.group(2) not in acts:
                continue
            if m.group(3) == "LEVL":
                lv[(m.group(1), m.group(2))] = B._num(m.group(4))
            elif m.group(3) == "CRPR_EXPT":
                ce[(m.group(1), m.group(2))] = B._num(m.group(4))
        for (r, a), x in lv.items():
            if (r, a) in ce:
                tot[(r, acts[a])] += x * ce[(r, a)]
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", default=str(SOURCES / "capreg"))
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT)); sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    import build_livestock_output_coef as B
    from capri_mod.data.loaders import load_regional_animal_numbers
    herds = load_regional_animal_numbers(str(ROOT / "capri_data"))
    t = B.per_head(totals_2017(B, Path(a.dump_dir), capri_activities(B.CAPRI_TO_MODEL)), herds)
    dest = ROOT / "capri_data" / "2017" / "environment" / "livestock_n_export_coef.csv"
    t.to_csv(dest)
    print(f"{dest.name}: {t.shape[0]} regions x {t.shape[1]} animals; EU median kg N per head "
          f"{t.median().round(2).to_dict()}")


if __name__ == "__main__":
    main()
