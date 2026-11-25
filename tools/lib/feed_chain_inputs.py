"""The readers of CAPRI's inputs of the feed chain (capri_mod/feed/chain.py, ChainInputs) for one member state:

- CAPREG's results of the base year: capri_sources/reference/capreg_base/17/<CC>.csv.gz (CAPREG's DATA2 at "Y", the
  source the CAPTRD port reads; docs/EXTERNAL_SOURCES.md);
- CAPREG's p_technFact and p_rcEmissions: capri_sources/dat_parquet/capreg_tseries/<CC>_17/<symbol>.parquet;
- CAPREG's requirement corrections: results/capreg/reqrel_17<CC>/p_animReqCorrFac1 of the raw dataset
  nuvolaTeam/capri-mod-raw (a local copy of its capri/ folder, else downloaded);
- CAPRI's trends: capri_sources/exports/trends_1730.csv (CAPTRD's DATA2 at "Y" as CAPRI's baseline loads it).

    from feed_chain_inputs import chain_inputs
    ci = chain_inputs("DK")
"""
from __future__ import annotations

import csv
import gzip
import re
from pathlib import Path

import pandas as pd

from capri_mod.feed.chain import ChainInputs, regions_of
from capri_mod.projection.equations import load_base_data_and_trends as ly
from paths import SOURCES

CAPREG_BASE = SOURCES / "reference" / "capreg_base" / "17"
CAPREG_RES = SOURCES / "dat_parquet" / "capreg_tseries"
TRENDS = SOURCES / "exports" / "trends_1730.csv"
RAW_REPO = "nuvolaTeam/capri-mod-raw"
REQREL = "results/capreg/reqrel_17*/p_animReqCorrFac1.parquet"
_REC = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'([^']*)'\s+(\S+?),?\s*$")


def _num(s: str) -> float:
    s = s.strip().rstrip(",")
    return 0.0 if s.upper() == "EPS" else float(s)


def read_capreg(cc: str, regions: set) -> ly.Data:
    """CAPREG's results of the member state cc (DATA2 at "Y") for the regions."""
    D = ly.Data()
    with gzip.open(CAPREG_BASE / f"{cc}.csv.gz", "rt", newline="") as f:
        rd = csv.reader(f)
        next(rd)
        for r, c, w, t, v, *_ in rd:
            if r in regions and t == "Y":
                D.set(r, c, w, "Y", float(v))
    return D


def read_trends(regions: set, path: Path = TRENDS) -> ly.Data:
    """CAPRI's trends (DATA2 at "Y") of the regions."""
    D = ly.Data()
    with open(path) as f:
        for line in f:
            m = _REC.match(line)
            if m and m.group(1) in regions and m.group(4) == "Y":
                D.set(m.group(1), m.group(2), m.group(3), "Y", _num(m.group(5)))
    return D


def capreg_folder(cc: str) -> Path:
    """The folder of CAPREG's 2017 results of the country cc (its base-year file's code): <CC>_17, or the folder of
    its region code where that differs (Turkey: base year TU, results TUR_17)."""
    p = CAPREG_RES / f"{cc}_17"
    if p.exists():
        return p
    alt = sorted(CAPREG_RES.glob(f"{cc}?_17"))
    if len(alt) != 1:
        raise FileNotFoundError(f"CAPREG's 2017 results of {cc}: none of {p.name} or {cc}?_17 in {CAPREG_RES}")
    return alt[0]


def capreg_results(cc: str, name: str, regions: set) -> dict:
    """A symbol of CAPREG's 2017 results for the member state's regions, {(d1, ..., dn): value}."""
    t = pd.read_parquet(capreg_folder(cc) / f"{name}.parquet")
    t = t[t.d1.isin(regions)]
    keys = [c for c in t.columns if c.startswith("d")]
    return {tuple(row[:-1]): float(row[-1]) for row in t[keys + ["value"]].itertuples(index=False, name=None)}


def raw_folder(raw: Path | None = None) -> Path:
    """The raw dataset's capri/ folder: the local copy, else a download of the corrections' files."""
    if raw is not None:
        return raw
    from huggingface_hub import snapshot_download
    return Path(snapshot_download(RAW_REPO, repo_type="dataset", allow_patterns=[f"capri/{REQREL}"])) / "capri"


def capreg_corrections(raw: Path, regions: set) -> dict:
    """CAPREG's p_animReqCorrFac1 {(region, animal, A, item): value} of the regions, from every reqrel_17<CC> file."""
    out = {}
    for f in sorted(raw.glob(REQREL)):
        t = pd.read_parquet(f)
        for r, a, tt, i, v in zip(t.d1, t.d2, t.d3, t.d4, t.value):
            if r in regions:
                out[(r, a, tt, i)] = float(v)
    return out


def chain_inputs(cc: str, raw: Path | None = None, others_bas: ly.Data | None = None) -> ChainInputs:
    """ChainInputs of the member state cc (DK, DE, ...) from CAPRI's files (module docstring)."""
    S = ly.YearSets.from_codes()
    _, mine = regions_of(cc, S)
    return ChainInputs(MS=cc, capreg=read_capreg(cc, mine), trends=read_trends(mine | set(S.MSALL)),
                       p_technFact=capreg_results(cc, "p_technFact", mine),
                       p_rcEmissions=capreg_results(cc, "p_rcEmissions", mine),
                       p_animReqCorrFac=capreg_corrections(raw_folder(raw), mine),
                       others_bas=others_bas if others_bas is not None else ly.Data())
