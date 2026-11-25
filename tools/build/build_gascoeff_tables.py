"""CAPRI's raw methane coefficients, from CAPRI's code to Parquet sources.

CAPRI's envind/gascoeff.gms loads its raw coefficients from rawdat_gascoeff.gdx and climdat_gascoeff.gdx (l. 520-522),
which envind/create_rawdat_gascoeff_gdx.gms writes from tables in its own text (l. 740-741: "Initialise selected
parameters via 'large' tables"). This builder reads those tables as GAMS reads them and writes them one to one:

  capri_data/sources/intermediate/envind/
    capri_emiscalc0.parquet             region, act, tech, item, value     EMISCALC0(Rall, COLS, A, emisParGdx) l. 44-75:
                                                                           CH4AN, CH4EN, YM, DE, ASH, B0, NRET (IPCC 2006)
    capri_tier1_manure_ef.parquet       region, act, tech, clim, value     p_tier1EmFactManMgt0(emisRegGdx, COLS, A,
                                                                           CLIMALL) l. 77-122, kg CH4 per head and year
    capri_share_clim_zone.parquet       region, clim, value                p_shareClimZone0(Rall, CLIMALL) l. 161-228
                                                                           (cool, temperate, warm per member state) and
                                                                           l. 231-354 (the temperature cells 10-20 per
                                                                           regional unit), percent
    capri_manure_mgt_share.parquet      region, act, tech, par, clim,      p_manureMgtShare0(emisRegGdx, COLS, A, EMISPAR,
                                        mansys, value                      CLIMALL, ManSys) l. 363-509 (MANAG, CH4CONV by
                                                                           climate zone) and l. 512-696 (CH4CONV by the
                                                                           temperature cells)

How GAMS reads a table, as done here: lines from $ontext to $offtext are dropped (a block inside the second management
table, l. 569-631, is dropped so); a line starting with * is a comment; the line after the TABLE statement that has no
row label is the column header, and a line "+" starts a new block whose next line is its header; a value belongs to the
column whose header it overlaps (any value overlapping no header or two stops the builder); a dotted column header
(10.Liquid) gives two index positions; a row label without values has no records. Both TABLE statements of
p_shareClimZone0 and of p_manureMgtShare0 are kept (their keys do not overlap; the builder checks). Not converted:
GHGEFS0 and ipcc11_2, which the methane does not use.

    python tools/build/build_gascoeff_tables.py [CAPRI gams folder, default capri_sources/gams]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import write_source  # noqa: E402  (capri_data/sources: Parquet)

import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "sources" / "intermediate" / "envind"
FILE = Path("envind") / "create_rawdat_gascoeff_gdx.gms"

#: symbol -> (output file, the row label's index names, the column header's index names)
TABLES = {
    "EMISCALC0": ("capri_emiscalc0.parquet", ("region", "act", "tech"), ("item",)),
    "p_tier1EmFactManMgt0": ("capri_tier1_manure_ef.parquet", ("region", "act", "tech"), ("clim",)),
    "p_shareClimZone0": ("capri_share_clim_zone.parquet", ("region",), ("clim",)),
}
MGT = ("capri_manure_mgt_share.parquet", ("region", "act", "tech", "par", "clim", "mansys"))


def gams_lines(text: str) -> list:
    """The file's lines without the $ontext ... $offtext blocks, numbered as in the file: [(line number, line)]."""
    out, skip = [], False
    for n, ln in enumerate(text.replace("\r", "").split("\n"), 1):
        low = ln.strip().lower()
        if low.startswith("$ontext"):
            skip = True
            continue
        if low.startswith("$offtext"):
            skip = False
            continue
        if not skip:
            out.append((n, ln))
    return out


def tables_of(lines: list, name: str) -> list:
    """Every TABLE statement of the symbol: [(first line number, [(line number, line), ...] up to the ";")]."""
    out = []
    pat = re.compile(rf"^\s*TABLE\s+{re.escape(name)}\s*\(", re.I)
    for i, (n, ln) in enumerate(lines):
        if pat.match(ln):
            body = []
            for m, l2 in lines[i + 1:]:
                if l2.strip() == ";":
                    break
                body.append((m, l2))
            else:
                raise SystemExit(f"{name} at l. {n}: no closing ';'")
            out.append((n, body))
    return out


def _label(tok: str) -> tuple:
    return tuple(p.strip('"').strip("'") for p in tok.split("."))


def parse_table(body: list, name: str) -> list:
    """A table's records [(row label parts, column label parts, value, line number)] read as GAMS reads them."""
    recs, cols, want_head = [], None, True
    for n, ln in body:
        if not ln.strip() or ln.startswith("*"):
            continue
        if ln.strip() == "+":
            want_head = True
            continue
        if want_head:
            if not ln[0].isspace():
                raise SystemExit(f"{name} l. {n}: a header was expected, found {ln.strip()[:40]!r}")
            cols = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\S+", ln)]
            want_head = False
            continue
        toks = list(re.finditer(r"\S+", ln))
        lab, k = toks[0].group(0), 1
        while lab.endswith(".") and k < len(toks):        # a label continued after its dot ("EU000000".   DCOW.T)
            lab, k = lab + toks[k].group(0), k + 1
        row = _label(lab)
        for t in toks[k:]:
            s, e = t.start(), t.end()
            hit = [c for c in cols if s < c[2] and e > c[1]]
            if len(hit) != 1:
                raise SystemExit(f"{name} l. {n}: value {t.group(0)!r} at {s}-{e} overlaps {len(hit)} headers")
            recs.append((row, _label(hit[0][0]), float(t.group(0)), n))
    return recs


def frame(recs: list, row_names: tuple, col_names: tuple, name: str) -> pd.DataFrame:
    rows = []
    for row, col, v, n in recs:
        if len(row) != len(row_names) or len(col) != len(col_names):
            raise SystemExit(f"{name} l. {n}: {row}.{col} does not have the indices {row_names + col_names}")
        rows.append(dict(zip(row_names + col_names, row + col), value=v))
    t = pd.DataFrame(rows, columns=list(row_names + col_names) + ["value"])
    keys = list(row_names + col_names)
    if t.duplicated(keys).any():
        raise SystemExit(f"{name}: keys given twice: {t[t.duplicated(keys, keep=False)].head().to_dict('records')}")
    return t


def main(gams: Path) -> None:
    path = gams / FILE
    lines = gams_lines(path.read_text(errors="ignore"))
    OUT.mkdir(parents=True, exist_ok=True)
    for sym, (fname, rn, cn) in TABLES.items():
        recs = [r for _, body in tables_of(lines, sym) for r in parse_table(body, sym)]
        t = frame(recs, rn, cn, sym)
        write_source(t, OUT / fname, index=False)
        print(f"{fname}: {len(t)} values ({sym}, {len(tables_of(lines, sym))} table(s))")
    tabs = tables_of(lines, "p_manureMgtShare0")
    recs = []
    for k, (_, body) in enumerate(tabs):
        for row, col, v, n in parse_table(body, "p_manureMgtShare0"):
            # the first table: rows region.act.tech.par.clim, columns the systems; the second: rows
            # region.act.tech.par, columns clim.system
            recs.append((row, col, v, n) if len(row) == 5 else ((row + col[:1]), col[1:], v, n))
    t = frame(recs, MGT[1][:5], MGT[1][5:], "p_manureMgtShare0")
    write_source(t, OUT / MGT[0], index=False)
    print(f"{MGT[0]}: {len(t)} values (p_manureMgtShare0, {len(tabs)} tables)")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCES / "gams")
