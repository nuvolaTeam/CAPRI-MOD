"""The manifest of the published CAPRI source set (docs/design/MODEL_CONTENT_PLAN.md section 12b, step 2): every file
of a version of the gated Hugging Face dataset nuvolaTeam/capri-mod-raw with its SHA-256 and size, kept in git
(tools/pipeline/capri_raw_manifest.json) so that a run or a builder names the exact files it rests on.

The set's layout (the project lead, 11 November 2026, replacing that of 4 November): the folders of CAPRI's
installation, Parquet only (the originals are not published: the Parquet holds every record and names its source)
  capri/dat/<subfolder>/<file>/, capri/results/<module>/<file>/, capri/temp/<file>/
                                         one Parquet file per GAMS symbol and _symbols.csv (tools/build/
                                         convert_capri_gdx.py), checked record by record against the GDX
                                         (tools/check/check_capri_gdx_parquet.py)
The manifest's "sources" give per CAPRI file its name, SHA-256, size, where its folder comes from and whether it is
trusted (tools/build/relayout_raw_dataset.py, tools/build/publish_raw_batch.py).

    python tools/build/make_raw_manifest.py STAGE_DIR --date YYYY-MM-DD [--note TEXT] [--revision COMMIT]
Merges the stage's files into the manifest (a file already listed with another hash is an error: a new version of a
file gets a new path) and records the upload in the manifest's history; --revision, the dataset commit the files are
at once uploaded. The dataset has no tags: each file is pinned by its SHA-256 and the manifest by the commit (the
project lead, 12 November 2026).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools" / "pipeline" / "capri_raw_manifest.json"
REPO = "nuvolaTeam/capri-mod-raw"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", type=Path)
    ap.add_argument("--date", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--revision", default="")
    a = ap.parse_args()
    man = json.loads(OUT.read_text()) if OUT.exists() else {"repo": REPO, "repo_type": "dataset", "history": [],
                                                              "files": {}}
    added = 0
    for p in sorted(x for x in a.stage.rglob("*") if x.is_file()):
        rel = p.relative_to(a.stage).as_posix()
        e = {"sha256": sha256(p), "size": p.stat().st_size}
        old = man["files"].get(rel)
        if old and old["sha256"] != e["sha256"]:
            sys.exit(f"{rel}: listed with another SHA-256 ({old['sha256'][:12]})")
        if not old:
            man["files"][rel] = e
            added += 1
    man.setdefault("history", []).append({"date": a.date, "note": a.note, "files_added": added})
    if a.revision:
        man["revision"] = a.revision
    man["files"] = dict(sorted(man["files"].items()))
    OUT.write_text(json.dumps(man, indent=1) + "\n")
    print(f"{OUT.relative_to(ROOT)}: {added} files added ({a.date}), {len(man['files'])} in all")


if __name__ == "__main__":
    main()
