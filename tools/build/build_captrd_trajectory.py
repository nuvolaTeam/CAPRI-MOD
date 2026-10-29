"""CAPRI's trend projection as the model's alternative 2030 trajectory: capri_data/trajectories/captrd_2030.json
(`--trajectory captrd`; the default is CAPRI's 2030 reference, capri_ref_2030.json). The file's one writer, from blank.

Source: CAPTRD's results of the base-2017 run (results_1770.gdx, p_result, datatype "series": the final reconciled trend
in projection years), as converted to capri_reference/captrd_results/1770/series.csv.gz
(tools/build/build_captrd_results_reference.py). The CAPRI-keyed factors are those of
capri_mod/projection/captrd_import.extract_trajectory (per-activity medians of the per-region cumulative ratios 2030 /
2017 of YILD and LEVL, band projection.captrd_factor_bounds, per-region factors where the base value is at least 1);
the model's activity and region keys are added by build_trajectory_model_keys.add_model_keys.

Until 29 October 2026 the file had no builder (extracted once from a series slice not kept; KNOWN_ISSUES K91). Rebuilt
from CAPTRD's results it reproduces the earlier file's growth factors and every entry keyed by the model's regions
exactly (the entries the projection reads); its CAPRI-keyed regional entries differ where the model-keys step of the
NUTS-2016 model (four-character model regions) had overwritten them with the model's aliases.

    python tools/build/build_captrd_trajectory.py [--series capri_reference/captrd_results/1770/series.csv.gz]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build")]
OUT = ROOT / "capri_data" / "trajectories" / "captrd_2030.json"
SERIES = Path("/home/claude/work/capri_reference/captrd_results/1770/series.csv.gz")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", type=Path, default=SERIES)
    a = ap.parse_args()
    from capri_mod.projection.captrd_import import extract_trajectory
    import build_trajectory_model_keys as K
    with tempfile.TemporaryDirectory() as tmp:
        # the extractor reads gdxdump lines of p_result: the 2017 and 2030 series of YILD, LEVL, PRIC
        sl = Path(tmp) / "series_slice.txt"
        n = 0
        with gzip.open(a.series, "rt", newline="") as fh, open(sl, "w") as out:
            r = csv.reader(fh)
            next(r)
            for reg, col, row, t, val, _eps in r:
                if row in ("YILD", "LEVL", "PRIC") and t in ("2017", "2030"):
                    out.write(f"'{reg}'.'{col}'.'{row}'.'{t}'.'series' {val}\n")
                    n += 1
        traj = extract_trajectory(sl, vintage="CAPTRD results_1770 (base 2017), the project lead's CAPRI installation")
    traj["_provenance"]["extracted_from"] = ("capri_reference/captrd_results/1770/series.csv.gz (results_1770.gdx "
                                             "p_result, series; tools/build/build_captrd_trajectory.py)")
    added = K.add_model_keys(traj)
    OUT.write_text(json.dumps(traj, indent=1))
    print(f"{OUT.relative_to(ROOT)}: {n} series records; {added}")


if __name__ == "__main__":
    main()
