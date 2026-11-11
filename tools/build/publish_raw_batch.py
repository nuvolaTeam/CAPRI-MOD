"""Publish a batch of CAPRI's GDX files to the gated Hugging Face dataset nuvolaTeam/capri-mod-raw, one file at a time
(the stage holds one file, so the batch needs no more disk than its largest file): its symbols as Parquet
(tools/build/convert_capri_gdx.py), checked record by record against the GDX (tools/check/
check_capri_gdx_parquet.py), uploaded, entered in the manifest (tools/pipeline/capri_raw_manifest.json: the files and
the source's name, SHA-256 and size), and the stage emptied. Only the Parquet is published (the project lead,
11 November 2026); the GDX stays outside the uploaded folder.

The batch is a CSV with the columns src (the file to publish), folder (its folder in CAPRI's installation:
dat/<subfolder>, results/<module>, temp), location (where that folder comes from: "code: <statement>" or
"inferred: <reason>") and trusted (yes/no); the Parquet goes to capri/<folder>/<file name without extension>/. A file
whose SHA-256 the manifest's sources already list is skipped; a folder listed with another source is an error.

    python tools/build/publish_raw_batch.py BATCH.csv STAGE_DIR --version TAG [--note TEXT] [--lib-dir DIR]
The Hugging Face token is the one huggingface_hub finds (its token file); it is never printed.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "build"))
from make_raw_manifest import OUT, REPO, sha256  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", type=Path)
    ap.add_argument("stage", type=Path)
    ap.add_argument("--version", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--lib-dir", default="")
    a = ap.parse_args()
    from huggingface_hub import HfApi
    api = HfApi()
    man = json.loads(OUT.read_text())
    man.setdefault("sources", {})
    known = {e["sha256"] for e in man["sources"].values()}
    ver = next((v for v in man["versions"] if v["tag"] == a.version), None)
    if ver is None:
        ver = {"tag": a.version, "note": a.note, "files_added": 0}
        man["versions"].append(ver)
    lib = ["--lib-dir", a.lib_dir] if a.lib_dir else []
    with open(a.batch, newline="") as fh:
        rows = list(csv.DictReader(fh))
    for i, r in enumerate(rows, 1):
        src = Path(r["src"])
        dest = f"capri/{r['folder']}/{src.stem}"
        h = sha256(src)
        if h in known:
            print(f"[{i}/{len(rows)}] {dest}: already published (same SHA-256), skipped", flush=True)
            continue
        if dest in man["sources"]:
            sys.exit(f"{dest}: listed with another source")
        if a.stage.exists():
            shutil.rmtree(a.stage)
        up = a.stage / "upload"
        pq = up / dest
        pq.parent.mkdir(parents=True)
        for cmd in (["tools/build/convert_capri_gdx.py", str(src), str(pq)],
                    ["tools/check/check_capri_gdx_parquet.py", str(src), str(pq)]):
            p = subprocess.run([sys.executable, *cmd, *lib], cwd=ROOT, capture_output=True, text=True)
            if p.returncode:
                sys.exit(f"{dest}: {cmd[0]} failed:\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
        files = sorted(x for x in up.rglob("*") if x.is_file())
        entries = {x.relative_to(up).as_posix(): {"sha256": sha256(x), "size": x.stat().st_size,
                                                   "version": a.version} for x in files}
        for k, e in entries.items():
            if k in man["files"] and man["files"][k]["sha256"] != e["sha256"]:
                sys.exit(f"{k}: listed with another SHA-256")
        api.upload_folder(repo_id=REPO, repo_type="dataset", folder_path=str(up),
                          commit_message=f"{a.version}: {dest}")
        new = [k for k in entries if k not in man["files"]]
        man["files"].update(entries)
        man["sources"][dest] = {"file": src.name, "sha256": h, "size": src.stat().st_size, "location": r["location"],
                                "trusted": r["trusted"].strip().lower() in ("yes", "true", "1"), "version": a.version}
        ver["files_added"] += len(new)
        known.add(h)
        man["files"] = dict(sorted(man["files"].items()))
        man["sources"] = dict(sorted(man["sources"].items()))
        OUT.write_text(json.dumps(man, indent=1) + "\n")
        size = sum(e["size"] for e in entries.values())
        print(f"[{i}/{len(rows)}] {dest}: {len(entries)} files, {size / 1e6:.1f} MB uploaded", flush=True)
        shutil.rmtree(a.stage)
    print(f"{OUT.relative_to(ROOT)}: {ver['files_added']} files in {a.version}, {len(man['files'])} in all")


if __name__ == "__main__":
    main()
