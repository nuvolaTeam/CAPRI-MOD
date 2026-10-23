"""CAPRI's nitrogen exported in animal products per model head (capri_data/2017/environment/livestock_n_export_coef.csv).

CAPRI's item CRPR_EXPT (kg N per unit of activity: fert/calc_nexport.gms - N in meat by liveweight and carcass ratio,
in milk at 0.0054 kg N per kg, in young animals sold less bought, in eggs, ...), 2017 results (res_17* dumps),
summed as CRPR_EXPT x LEVL over the CAPRI activities of each model animal and divided by the model's herd, per group
of CAPRI and model regions covering the same territory - the construction of livestock_manure_n_coef.csv (MANN) by
tools/build/build_livestock_output_coef.build. Used for the report item n_animal_products (until 23 October 2026: 25% of
excreted N; PROXY_AUDIT S199). Simulated years: the per-head value scales with the animal's output per head.

    python tools/build/build_livestock_n_export_coef.py [--dump-dir /home/claude/work/capreg]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", default="/home/claude/work/capreg")
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT)); sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]
    import build_livestock_output_coef as B
    t = B.build(Path(a.dump_dir), "CRPR_EXPT")
    dest = ROOT / "capri_data" / "2017" / "environment" / "livestock_n_export_coef.csv"
    t.to_csv(dest)
    print(f"{dest.name}: {t.shape[0]} regions x {t.shape[1]} animals; EU median kg N per head "
          f"{t.median().round(2).to_dict()}")


if __name__ == "__main__":
    main()
