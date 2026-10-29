"""The run manifest (capri_mod/run_manifest.py): the inputs a run reads, with their SHA-256, and the code's state."""
import hashlib
import json

import pandas as pd

from capri_mod import run_manifest
from capri_mod.csvio import read_csv


def test_the_manifest_records_the_inputs_read_with_their_hash(tmp_path):
    root = run_manifest.ROOT
    f = root / "capri_data" / "shared" / "rms_to_rm.csv"
    run_manifest.start()
    read_csv(f)
    json.loads((root / "capri_data" / "MANIFEST.json").read_text())       # Path.read_text: Python's open too
    out = tmp_path / "x.csv"
    pd.DataFrame({"a": [1]}).to_csv(out)                                   # a write is not an input
    m = run_manifest.finish()
    rel = "capri_data/shared/rms_to_rm.csv"
    assert rel in m["inputs"]
    assert m["inputs"][rel]["sha256"] == hashlib.sha256(f.read_bytes()).hexdigest()
    assert "capri_data/MANIFEST.json" in m["inputs"]
    assert str(out) not in m["external_inputs"]
    assert len(m["git"]["commit"]) == 40 and m["software"]["pandas"] == pd.__version__
    # recording stops at finish
    run_manifest.start(); m2 = run_manifest.finish()
    read_csv(f)
    assert rel not in m2["inputs"]
    d = run_manifest.compare(m, m2)
    assert rel in d["inputs_only_first"] and not d["inputs_differ"]
