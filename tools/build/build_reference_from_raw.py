"""capri_sources/reference from the published raw set's Parquet tables (Hugging Face nuvolaTeam/capri-mod-raw, gated,
at the revision of tools/pipeline/capri_raw_manifest.json; the layout capri/<folder>/<file>/<symbol>.parquet with the
columns d1..dn, value, special) instead of CAPRI's GDX files, for a container without GAMS or the CAPRI results.
The outputs are in the formats of tools/build/build_captrd_results_reference.py, build_capreg_tseries_reference.py
and build_capri_sets_reference.py (their writers copied: the value's repr, eps 1 for a record stored as Eps, the
records in the file's order):
- captrd_results/1770: one file per result position of CAPTRD's reference run (p_result of results_1770),
  respos_counts.csv, settings.csv;
- capreg_tseries/17: CAPREG's time series, one file per country;
- sets/simini_21730: CAPRI's sets of sim_ini_21730, one file per set, _index.csv.
Not in the published set: capreg_base (CAPREG's base year for the EU's countries), so the pipeline tests that read
it (CAPTRD's bounds, NLP and NUTS 2 solves at given countries) cannot run on a reference built this way.

The download, in two passes (the sets' list is in sim_ini_21730's _symbols.csv), into RAW_DIR at the same paths:
    python tools/build/build_reference_from_raw.py --list RAW_DIR      # the files still missing, one path a line
    curl -sfL --create-dirs -o RAW_DIR/PATH \
         https://huggingface.co/datasets/nuvolaTeam/capri-mod-raw/resolve/REVISION/PATH      # each PATH
(with the token in an Authorization: Bearer header, or a proxy that adds it; never in the repository). Then:
    python tools/build/build_reference_from_raw.py RAW_DIR [REFERENCE_DIR]   # default capri_sources/reference
p_result's 33 million records are streamed in batches (about 1 GB of memory, 10 minutes).
"""
import argparse
import csv
import gzip
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tools" / "pipeline" / "capri_raw_manifest.json"
CAPTRD = "capri/results/baseline/results_1770"
TSERIES = "capri/results/capreg/Capreg_tseries"
SIMINI = "capri/results/simini/sim_ini_21730"


def needed(raw: Path):
    """The raw files the reference needs, in the manifest; the sets once sim_ini_21730's _symbols.csv is there."""
    files = json.loads(MANIFEST.read_text())["files"]
    want = [f"{CAPTRD}/p_result.parquet", f"{CAPTRD}/SETTINGS.parquet", f"{SIMINI}/_symbols.csv"]
    want += sorted(p for p in files if p.startswith(TSERIES + "/") and p.endswith("_17/DATA.parquet"))
    sy = raw / SIMINI / "_symbols.csv"
    if sy.exists():
        want += [f"{SIMINI}/{r['symbol']}.parquet" for r in csv.DictReader(open(sy)) if r["type"] == "set"]
    missing = [p for p in want if p not in files]
    assert not missing, f"not in the manifest: {missing[:5]}"
    return want


def rows(t, nd):
    keys = [t[f"d{i}"].astype(str).tolist() for i in range(1, nd + 1)]
    vals = t["value"].tolist()
    eps = (t["special"].fillna("") == "value:EPS").tolist()
    for i in range(len(t)):
        e = int(eps[i])
        yield [k[i] for k in keys], repr(0.0 if e else float(vals[i])), e


def captrd_results(raw: Path, ref: Path):
    import pandas as pd
    import pyarrow.parquet as pq
    src, out = raw / CAPTRD, ref / "captrd_results" / "1770"
    out.mkdir(parents=True, exist_ok=True)
    writers, files, counts = {}, [], Counter()
    for batch in pq.ParquetFile(src / "p_result.parquet").iter_batches(batch_size=500_000):
        c = batch.to_pydict()
        for d1, d2, d3, d4, rp, val, sp in zip(c["d1"], c["d2"], c["d3"], c["d4"], c["d5"], c["value"], c["special"]):
            e = int(sp == "value:EPS")
            counts[rp] += 1
            if rp not in writers:
                fh = gzip.open(out / f"{rp}.csv.gz", "wt", newline="", compresslevel=6)
                files.append(fh)
                writers[rp] = csv.writer(fh, lineterminator="\n")
                writers[rp].writerow(["region", "col", "row", "t", "value", "eps"])
            writers[rp].writerow((d1, d2, d3, d4, repr(0.0 if e else float(val)), e))
        del c, batch
    for fh in files:
        fh.close()
    with open(out / "respos_counts.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["respos", "records", "written"])
        for rp, n in sorted(counts.items()):
            w.writerow([rp, n, 1])
    s = pd.read_parquet(src / "SETTINGS.parquet")
    with open(out / "settings.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["d0", "d1", "d2", "text"])
        for r in s.itertuples(index=False):
            w.writerow([r.d1, r.d2, r.d3, r.text if isinstance(r.text, str) else ""])
    print(f"captrd_results/1770: {sum(counts.values())} records, {len(counts)} positions")


def capreg_tseries(raw: Path, ref: Path):
    import pandas as pd
    out = ref / "capreg_tseries" / "17"
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for d in sorted((raw / TSERIES).glob("*_17")):
        t = pd.read_parquet(d / "DATA.parquet")
        with gzip.open(out / f"{d.name[:-3]}.csv.gz", "wt", newline="", compresslevel=6) as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["region", "col", "row", "t", "value", "eps"])
            for k, v, e in rows(t, 4):
                w.writerow((k[0], k[1], k[2], k[3], v, e))
        n += 1
    print(f"capreg_tseries/17: {n} countries")


def sets(raw: Path, ref: Path):
    import pandas as pd
    src, out = raw / SIMINI, ref / "sets" / "simini_21730"
    out.mkdir(parents=True, exist_ok=True)
    sy = [r for r in csv.DictReader(open(src / "_symbols.csv")) if r["type"] == "set"]
    index, seen = [], set()
    for i, r in enumerate(sy, 1):
        name, dim = r["symbol"], int(r["dim"])
        fname = re.sub(r"[^A-Za-z0-9_]", "_", name)
        if fname.lower() in seen:
            fname = f"{fname}__{i}"
        seen.add(fname.lower())
        t = pd.read_parquet(src / f"{name}.parquet")
        with open(out / f"{fname}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow([f"d{k}" for k in range(dim)] + ["text"])
            txt = t["text"].fillna("").astype(str).tolist() if "text" in t else [""] * len(t)
            cols = [t[f"d{k}"].astype(str).tolist() for k in range(1, dim + 1)]
            for j in range(len(t)):
                w.writerow([c[j] for c in cols] + [txt[j]])
        index.append((name, fname, dim, len(t), r.get("text", "")))
    with open(out / "_index.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["set", "file", "dim", "records", "description"])
        w.writerows(index)
    print(f"sets/simini_21730: {len(index)} sets")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw", type=Path)
    ap.add_argument("reference", type=Path, nargs="?", default=ROOT / "capri_sources" / "reference")
    ap.add_argument("--list", action="store_true", help="print the raw files still missing under RAW and stop")
    a = ap.parse_args()
    if a.list:
        print(f"# revision {json.loads(MANIFEST.read_text())['revision']}")
        for p in needed(a.raw):
            if not (a.raw / p).exists():
                print(p)
    else:
        captrd_results(a.raw, a.reference)
        capreg_tseries(a.raw, a.reference)
        sets(a.raw, a.reference)
