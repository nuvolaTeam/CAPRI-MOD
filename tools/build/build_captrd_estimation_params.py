"""The parameters of CAPTRD's estimation equations (captrd/equations.gms, m_trendMS) that are CAPRI data rather than
CAPTRD results, from CAPRI's own instantiation (sim_ini_21730.gdx; the raw dataset nuvolaTeam/capri-mod-raw,
capri/results/simini/sim_ini_21730/, as Parquet):
  p_carcassShare(COLS)   carcass weight over live weight (FinalWgt_, Dailyup_, l. 573-593); CAPRI's constants of
                         feed/feed_decl.gms l. 211-226, which captrd.gms includes (l. 370)
  p_startWgt(COLS)       live weight at the start of fattening, kg (FinalWgt_; feed_decl.gms l. 231-245)
  p_NCNC_CONT(ROWS, NCNC) nutrient content per kg (NUTBAL_, l. 740-746): the USDA contents mapped to CAPRI's codes,
                         computed alike by captrd.gms l. 622-633 and coco2.gms l. 255-262
(LU_'s p_LUUnits is CAPTRD's data file, already in capri_data/pipeline/captrd/dat/p_luunits.csv, build_captrd_dat.py.)
p_globiomTightLink (REQS_, l. 522-540) is empty in sim_ini_21730 (and in CAPTRD's reference run), so REQS_ takes the
0.2% yearly feeding efficiency gain; the builder stops if it is not empty.

The rows are kept in capri_data/sources/raw/capri/results/simini/sim_ini_21730/captrd_estimation_params.parquet, so the
builder rebuilds without the raw files.

    python tools/build/build_captrd_estimation_params.py [--parquet DIR | --download]
        DIR: a copy of the raw dataset's capri/ folder; --download: from the raw dataset (Hugging Face);
        neither: from the kept extract
Output: capri_data/pipeline/captrd/params/{carcass_share,start_wgt,ncnc_cont}.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from _sources_io import read_source, write_source  # noqa: E402  (capri_data/sources: Parquet)

OUT = ROOT / "capri_data" / "pipeline" / "captrd" / "params"
SUB = "capri/results/simini/sim_ini_21730"
KEEP = ROOT / "capri_data" / "sources" / "raw" / SUB / "captrd_estimation_params.parquet"
#: symbol -> (output name, number of index dimensions)
SYMBOLS = {"p_carcassShare": ("carcass_share", 1), "p_startWgt": ("start_wgt", 1),
           "p_NCNC_CONT": ("ncnc_cont", 2)}
EMPTY = ["p_globiomTightLink"]
REPO = "nuvolaTeam/capri-mod-raw"


def _folder(parquet: Path | None, download: bool):
    if parquet is not None:
        return parquet / "results" / "simini" / "sim_ini_21730"
    if not download:
        return None
    from huggingface_hub import snapshot_download
    p = snapshot_download(REPO, repo_type="dataset",
                          allow_patterns=[f"{SUB}/{s}.parquet" for s in list(SYMBOLS) + EMPTY])
    return Path(p) / SUB


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", type=Path, default=None)
    ap.add_argument("--download", action="store_true")
    a = ap.parse_args()
    folder = _folder(a.parquet, a.download)
    if folder is not None:
        for s in EMPTY:
            if len(pd.read_parquet(folder / f"{s}.parquet")):
                raise SystemExit(f"{s} is not empty: REQS_ would take it (equations.gms l. 527-530), not ported")
        rows = []
        for s, (_o, dim) in SYMBOLS.items():
            d = pd.read_parquet(folder / f"{s}.parquet")
            for t in d.itertuples(index=False):
                rows.append([s, t.d1, t.d2 if dim == 2 else "", float(t.value)])
        ex = pd.DataFrame(rows, columns=["symbol", "d0", "d1", "value"])
        KEEP.parent.mkdir(parents=True, exist_ok=True)
        write_source(ex, KEEP, index=False)
        print(f"extracted {len(ex)} rows -> {KEEP.relative_to(ROOT)}")
    src = read_source(KEEP)
    OUT.mkdir(parents=True, exist_ok=True)
    for s, (o, dim) in SYMBOLS.items():
        d = src[src.symbol == s]
        if d.empty:
            raise SystemExit(f"{s}: no records")
        with open(OUT / f"{o}.csv", "w", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow([f"d{k}" for k in range(dim)] + ["value"])
            for t in sorted(d.itertuples(index=False), key=lambda t: (t.d0, t.d1)):
                w.writerow([t.d0] + ([t.d1] if dim == 2 else []) + [repr(float(t.value))])
        print(f"{(OUT / (o + '.csv')).relative_to(ROOT)}: {len(d)} records")


if __name__ == "__main__":
    main()
