"""Publish the TABLE symbols of one of CAPRI's GAMS data include files (dat/<subfolder>/<file>.gms) to the raw set
nuvolaTeam/capri-mod-raw, as tools/build/publish_raw_batch.py publishes CAPRI's GDX files: one Parquet file per symbol
in the GDX converter's layout (tools/build/convert_capri_gdx.py: the index positions as text columns d1..dN, value,
special; the symbol's type, dimension, domains, record count and the source file's name and SHA-256 in the Parquet
metadata, key "capri_gms"), and _symbols.csv; each record checked against a second reading of the file (whitespace
columns of the table's header, every cell present); uploaded under capri/<folder>/<file name without extension>/ and
entered in the manifest (tools/pipeline/capri_raw_manifest.json: the files, the source's name, SHA-256 and size, its
location in CAPRI's installation, trusted).

    python tools/build/publish_capri_gms_tables.py FILE.gms --folder dat/feed --tables NAME:DOMAIN[,NAME:DOMAIN]
        --location "code: ..." --date YYYY-MM-DD [--note TEXT] [--stage DIR] [--upload]
Without --upload the Parquet is written to the stage and checked only. The Hugging Face token is the one huggingface_hub
finds (its token file); it is never printed.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "build")]
from gams_text import read_text, table_records  # noqa: E402
from make_raw_manifest import OUT, REPO, sha256  # noqa: E402


def _second_reading(text: str, name: str) -> dict:
    """{(row, column): value} of TABLE name read by whitespace: the header's labels, then rows of a label and one
    number per label (the check of the converter's records; a table with empty cells is not read here)."""
    lines = text.splitlines()
    k = next(i for i, ln in enumerate(lines) if re.match(rf"\s*table\s+{name}(\s|\(|$)", ln, flags=re.I))
    head = lines[k + 1].split()
    out = {}
    for ln in lines[k + 2:]:
        t = ln.replace(";", " ").split()
        if not t or ln.startswith("*"):
            continue
        if len(t) != len(head) + 1:
            raise ValueError(f"{name}: row {ln!r} does not have one value per column")
        out.update({(t[0], c): float(v) for c, v in zip(head, t[1:])})
        if ln.rstrip().endswith(";"):
            break
    return out


def convert(src: Path, out: Path, tables: list[tuple[str, str]]) -> list:
    import pyarrow as pa
    import pyarrow.parquet as pq
    text = read_text(src)
    # a table's last row ends with its ';' (GAMS): on a line of its own for the table reader
    reader = re.sub(r";[ \t]*$", "\n;", text, flags=re.M)
    info = {"file": src.name, "sha256": sha256(src)}
    out.mkdir(parents=True, exist_ok=True)
    listing = []
    for name, dom in tables:
        recs = table_records(reader, name, 1, src.name)
        check = _second_reading(text, name)
        got = {(r, c): float(v) for r, c, v in recs}
        if got != check or len(recs) != len(check):
            raise SystemExit(f"{src.name} {name}: the two readings differ")
        meta = {"symbol": name, "type": "parameter", "dim": 2, "domains": [dom, "*"], "text": "",
                "records": len(recs), "source": info}
        schema = pa.schema([("d1", pa.string()), ("d2", pa.string()), ("value", pa.float64()),
                            ("special", pa.string())]).with_metadata({"capri_gms": json.dumps(meta)})
        tab = pa.table({"d1": [r for r, _, _ in recs], "d2": [c for _, c, _ in recs],
                        "value": [float(v) for _, _, v in recs], "special": [""] * len(recs)}, schema=schema)
        pq.write_table(tab, str(out / f"{name}.parquet"), compression="zstd")
        back = pq.read_table(str(out / f"{name}.parquet")).to_pydict()
        if {(a, b): v for a, b, v in zip(back["d1"], back["d2"], back["value"])} != check:
            raise SystemExit(f"{name}: the Parquet read back differs from the file")
        listing.append((name, "parameter", 2, len(recs), "", 0))
    with open(out / "_symbols.csv", "w", newline="") as fh:
        wr = csv.writer(fh, lineterminator="\n")
        wr.writerow(["symbol", "type", "dim", "records", "text", "latin1_strings"])
        wr.writerows(listing)
    return listing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("--folder", required=True)
    ap.add_argument("--tables", required=True)
    ap.add_argument("--location", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--stage", type=Path, default=ROOT / ".cache" / "raw_stage")
    ap.add_argument("--upload", action="store_true")
    a = ap.parse_args()
    tables = [tuple(x.split(":")) for x in a.tables.split(",")]
    dest = f"capri/{a.folder}/{a.src.stem}"
    if a.stage.exists():
        shutil.rmtree(a.stage)
    up = a.stage / "upload"
    listing = convert(a.src, up / dest, tables)
    files = sorted(x for x in up.rglob("*") if x.is_file())
    entries = {x.relative_to(up).as_posix(): {"sha256": sha256(x), "size": x.stat().st_size} for x in files}
    print(f"{dest}: " + ", ".join(f"{n} {r} records" for n, _, _, r, _, _ in listing) + " (checked)")
    if not a.upload:
        return
    man = json.loads(OUT.read_text())
    h = sha256(a.src)
    if h in {e["sha256"] for e in man["sources"].values()}:
        sys.exit(f"{a.src.name}: already published (same SHA-256)")
    if dest in man["sources"]:
        sys.exit(f"{dest}: listed with another source")
    from huggingface_hub import HfApi
    ci = HfApi().upload_folder(repo_id=REPO, repo_type="dataset", folder_path=str(up),
                               commit_message=f"{a.date}: {dest}")
    man["revision"] = ci.oid
    new = [k for k in entries if k not in man["files"]]
    man["files"].update(entries)
    man["sources"][dest] = {"file": a.src.name, "sha256": h, "size": a.src.stat().st_size, "location": a.location,
                            "trusted": True}
    man.setdefault("history", []).append({"date": a.date, "note": a.note, "files_added": len(new)})
    man["files"] = dict(sorted(man["files"].items()))
    man["sources"] = dict(sorted(man["sources"].items()))
    OUT.write_text(json.dumps(man, indent=1) + "\n")
    shutil.rmtree(a.stage)
    print(f"{OUT.relative_to(ROOT)}: {len(new)} files added ({a.date}), {len(man['files'])} in all")


if __name__ == "__main__":
    main()
