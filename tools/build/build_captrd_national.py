"""The inputs of CAPTRD's national expert supports (captrd/national_supports.gms, included by captrd/expert_support.gms
l. 779), as CSV.

Sources (the project lead's CAPRI installation, docs/EXTERNAL_SOURCES.md):
  gams/captrd/national_supports.gms  its sets xpCOLS, xpDisAgg, xpROWS, Expert_to_cols, Expert_to_rows (l. 52-137) and
                                     absDairyRunr (l. 1516-1535), read by tools/lib/gams_sets.py from those lines (the
                                     file's $iftheni blocks are not for that reader); labels as written ('Castrated
                                     horses ' keeps its blank)
  dat/baseline/necp_expert.gms       the table p_fromNECP(rAll, xpCols, simyy) (the member states' NECP herds and
                                     fertiliser, 2005-2050; read by national_supports.gms l. 149), its nonzero records
                                     (GAMS stores no zeros)
Output: capri_data/pipeline/captrd/sets/national/<set>.csv (d0, d1), capri_data/pipeline/captrd/dat/national_p_fromnecp.csv.

    python tools/build/build_captrd_national.py
"""
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import gams_sets as G                                      # noqa: E402
import gams_text as GT                                     # noqa: E402
from paths import SOURCES                                  # noqa: E402

GAMS = SOURCES / "course_capri_git" / "gams"
NECP = SOURCES / "dat_local" / "baseline" / "necp_expert.gms"
OUT_SETS = ROOT / "capri_data" / "pipeline" / "captrd" / "sets" / "national"
OUT_DAT = ROOT / "capri_data" / "pipeline" / "captrd" / "dat"
#: the lines of national_supports.gms holding the sets (1-based, inclusive)
SET_LINES = [(48, 143), (1516, 1535)]
SETS = ["xpCOLS", "xpDisAgg", "xpROWS", "Expert_to_cols", "Expert_to_rows", "absDairyRunr"]


def _write(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"{path.relative_to(ROOT)}: {len(rows)} records")


def main() -> None:
    lines = (GAMS / "captrd" / "national_supports.gms").read_text(errors="replace").splitlines()
    text = "\n".join("\n".join(lines[a - 1:b]) for a, b in SET_LINES)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "national_sets.gms"
        p.write_text(text + "\n")
        gs = G.read(p, GAMS, {})
    for n in SETS:
        m = gs.get(n)
        _write(OUT_SETS / f"{n.lower()}.csv", [f"d{i}" for i in range(len(m[0]))], m)
    recs = GT.table_records(GT.read_text(NECP), "p_fromNECP", 2, "necp_expert.gms", unquote=True)
    _write(OUT_DAT / "national_p_fromnecp.csv", ["region", "xpcol", "year", "value"],
           [(r.upper(), c, int(y), repr(float(v))) for r, c, y, v in recs if float(v)])


if __name__ == "__main__":
    main()
