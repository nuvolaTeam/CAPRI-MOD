"""Recompute every run id of a capri-mod results store from the tables alone (no capri-mod code): the recipe
'capri-mod run id 1' as documented in capri_mod/io_results.py (rows_digest, run_id_of). Published beside the store
(Hugging Face dataset nuvolaTeam/capri-mod-results). Each run's rows are read alone (a filter on run_id) and in
batches, and their lines sorted on disk by sort(1) in byte order (LC_ALL=C: for UTF-8 text the code-point order of
Python's sorted), so a run of millions of rows is checked in bounded memory. Needs the deltalake and pyarrow packages
and the sort command.

    python verify_ids.py STORE_DIR        (the folder holding runs/ and long/)
Exit status 1 if an id does not recompute.
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile

import pyarrow.dataset as ds
from deltalake import DeltaTable

TEXT = ["block", "region", "dim5", "cols", "rows", "capri_region", "capri_dim5", "capri_cols", "capri_rows", "unit"]


def t(v):
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)


def n_(v):
    return "nan" if v is None or math.isnan(float(v)) else float(v).hex()


def digest(scanner):
    """The SHA-256 of a run's rows as JSON lines, sorted and joined by newlines (no newline at the end)."""
    with tempfile.TemporaryDirectory() as td:
        src, dst = os.path.join(td, "lines"), os.path.join(td, "sorted")
        n = 0
        with open(src, "w", encoding="utf-8", newline="\n") as fh:
            for b in scanner.to_batches():
                cols = {c: b.column(c).to_pylist() for c in TEXT + ["year", "value"]}
                for i in range(b.num_rows):
                    fh.write(json.dumps([t(cols[c][i]) for c in TEXT] + [int(cols["year"][i]), n_(cols["value"][i])],
                                        ensure_ascii=False, separators=(",", ":")) + "\n")
                n += b.num_rows
        subprocess.run(["sort", "-S", "256M", "-T", td, "-o", dst, src], check=True, env={**os.environ, "LC_ALL": "C"})
        h = hashlib.sha256()
        with open(dst, "rb") as fh:
            data = fh.read(1 << 20)
            while data:
                nxt = fh.read(1 << 20)
                h.update(data if nxt else data[:-1] if data.endswith(b"\n") else data)
                data = nxt
        return h.hexdigest(), n


def main(root):
    runs = DeltaTable(f"{root}/runs").to_pyarrow_table().to_pylist()
    dset = DeltaTable(f"{root}/long").to_pyarrow_dataset()
    ok = 0
    for rec in sorted(runs, key=lambda r: r["seq"]):
        sc = dset.scanner(columns=TEXT + ["year", "value"], filter=ds.field("run_id") == rec["run_id"],
                          batch_size=200_000, batch_readahead=1, fragment_readahead=1)
        dig, nrows = digest(sc)
        rid = hashlib.sha256("\n".join(["capri-mod run id 1", rec["kind"], rec["scenario"],
                                         rec["reference_run_id"] or "", rec["fingerprint"], dig]).encode()).hexdigest()
        good = rid == rec["run_id"]
        print(rec["kind"], rec["scenario"][:24], rec["run_id"][:12], "OK" if good else "MISMATCH", nrows, flush=True)
        ok += good
    print(f"{ok}/{len(runs)} ids recomputed")
    return 0 if ok == len(runs) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
