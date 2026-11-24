"""CAPRI's literal parameters of its requirement and manure output functions (capri_data/2017/feed/
req_or_man_params.csv), the data of capri_mod/feed/equations/req_or_man_fnc.py and req_or_man_fnc_req.py
(feed/req_or_man_fnc.gms called with %1 = man and %1 = req). Until 24 November 2026 (afternoon) the file was
manure_output_params.csv, written by build_manure_output_params.py.

Read from CAPRI star 3.0's feed/feed_decl.gms (capri_sources/gams):
- p_NutContManureKgM3(ANTYP, ROWS): the N, P2O5 and K2O in kg per cubic metre of cattle, swine and poultry manure (the
  TABLE, l. 130-135; the per-kg-and-day contents CAPRI derives from it, l. 146-157, are a function of the module);
- p_addExcrPerkgMilk(ROWS): the extra N, P2O5 and K2O per kg of milk (l. 163-164);
- p_carcassShare(COLS), p_startWgt(COLS): the carcass share of the live weight and the start weight (l. 211-245);
- p_reqfcnlim(COLS, ROWS, up/lo): the limits on days and daily gains of the requirement functions (l. 284-312);
- p_NutContFeedRef(act, A, requirement, feed aggregate, MIN/MEAN/MAX): the typical nutrient densities of the rations
  (the table, l. 80-119);
- p_convFactEnergyUnitsToEnne(REQSE): the energy units over net energy for lactation (l. 207-208);
- p_coeffEnergyForGrowth: IPCC's coefficient of the energy for growth by animal (l. 268-276);
CAPRI's livestock units p_LUUnits (CAPRI's dat/policy/livestock_units.gms, capri_data/sources/raw/capri/dat/
policy/livestock_units_p_LUUnits.parquet; the stocking rate of req_or_man_fnc.gms l. 100-110); and the fattened pigs'
requirements by weight class, p_pigsReqHighWgt(porkFinWgtHi, *) and p_pigsReqLowWgt(porkFinWgtLo, *) (XDUF the days,
XALW the live weight, CRPR the crude protein, ...: CAPRI's dat/feed/porkreq.gms, which feed/feed_decl.gms l. 191
includes; capri_sources/dat/feed/porkreq.gms, the project lead's file of 24 November 2026).

Output, long: symbol, key1, ..., key5, value (keys empty where the symbol has fewer).

    python tools/build/build_req_or_man_params.py [--gams capri_sources/gams] [--dat capri_sources/dat]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from gams_text import read_text, table_records  # noqa: E402  (GAMS's table layout)
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)

OUT = ROOT / "capri_data" / "2017" / "feed" / "req_or_man_params.csv"
LU = ROOT / "capri_data" / "sources" / "raw" / "capri" / "dat" / "policy" / "livestock_units_p_LUUnits.parquet"


def _code(text: str) -> list[str]:
    """The file's lines without GAMS comment lines ('*' in the first column)."""
    return [l for l in text.splitlines() if not l.startswith("*")]


def _block(lines: list[str], head: str) -> list[str]:
    """The lines from the one starting a declaration matching `head` to its closing ';' (or '/;')."""
    for i, l in enumerate(lines):
        if re.match(head, l.strip(), re.I):
            out = []
            for m in lines[i:]:
                out.append(m)
                if m.rstrip().endswith(";"):
                    return out
    raise ValueError(f"feed_decl.gms: no declaration {head!r}")


def _slash_list(block: list[str]) -> list[tuple[str, float]]:
    """The 'NAME value' pairs of a PARAMETER's /.../ list (one or several per line, comma separated)."""
    body = " ".join(block)
    body = body[body.index("/") + 1: body.rindex("/")]
    return [(k, float(v)) for k, v in re.findall(r"([A-Za-z0-9_]+)\s+([-0-9.Ee+]+)", body)]


def p_NutContManureKgM3(lines) -> list[tuple]:
    """TABLE p_NutContManureKgM3(ANTYP, ROWS): the rows CATT, SWINE, POUL under the columns MANN, MANP, MANK."""
    b = _block(lines, r"TABLE\s+p_NutContManureKgM3")
    cols = b[1].split()
    rows = []
    for l in b[2:]:
        t = l.replace(";", "").split()
        if len(t) == len(cols) + 1:
            rows += [("p_NutContManureKgM3", t[0], c, "", "", "", float(v)) for c, v in zip(cols, t[1:])]
    return rows


def p_reqfcnlim(lines) -> list[tuple]:
    """Table p_reqfcnlim(COLS, ROWS, *): the up and lo limits by COL.ROW (a missing entry is CAPRI's 0, not written)."""
    b = _block(lines, r"Table\s+p_reqfcnlim")
    hdr = next(l for l in b[1:] if l.split() == ["up", "lo"])
    labels = [(m.start(), m.group(0)) for m in re.finditer(r"up|lo", hdr)]
    rows = []
    for l in b[b.index(hdr) + 1:]:
        m = re.match(r"^([A-Z0-9]+)\.([A-Z]+)\s", l)
        if not m:
            continue
        for v in re.finditer(r"[-0-9.]+", l[m.end():]):
            # a value belongs to the header's column nearest to it (GAMS's table layout: PIGF.DAYS has its lo only)
            at = m.end() + v.start()
            bound = min(labels, key=lambda x: abs(x[0] - at))[1]
            rows.append(("p_reqfcnlim", m.group(1), m.group(2), bound, "", "", float(v.group(0))))
    return rows


def pig_requirements(dat: Path) -> list[tuple]:
    """TABLE p_pigsReqHighWgt and p_pigsReqLowWgt of CAPRI's dat/feed/porkreq.gms: (weight class, item, value)."""
    # a table's last row ends with its ';' (GAMS): put it on a line of its own for the table reader
    text = re.sub(r";[ \t]*$", "\n;", read_text(dat / "feed" / "porkreq.gms"), flags=re.M)
    rows = []
    for name in ("p_pigsReqHighWgt", "p_pigsReqLowWgt"):
        rows += [(name, c, item, "", "", "", float(v)) for c, item, v in table_records(text, name, 1, "porkreq.gms")]
    return rows


def p_NutContFeedRef(lines) -> list[tuple]:
    """table p_NutContFeedRef: rows act.A.requirement.aggregate under the columns "MIN", MEAN, "MAX" (quoted labels)."""
    b = _block(lines, r"table\s+p_NutContFeedRef")
    cols = [c.strip('"') for c in b[1].split()]
    rows = []
    for l in b[2:]:
        t = l.replace(";", "").split()
        if len(t) == len(cols) + 1 and t[0].count(".") == 3:
            rows += [("p_NutContFeedRef", *t[0].split("."), c, float(v)) for c, v in zip(cols, t[1:])]
    return rows


def _one(k, v, symbol):
    return (symbol, k, "", "", "", "", v)


def build(gams: Path, dat: Path) -> pd.DataFrame:
    lines = _code((gams / "feed" / "feed_decl.gms").read_text(errors="ignore"))
    rows = p_NutContManureKgM3(lines)
    for name in ("p_addExcrPerkgMilk", "p_carcassShare", "p_startWgt", "p_convFactEnergyUnitsToEnne",
                 "p_coeffEnergyForGrowth"):
        rows += [_one(k, v, name) for k, v in _slash_list(_block(lines, rf"PARAMETER\s+{name}"))]
    rows += p_reqfcnlim(lines)
    rows += p_NutContFeedRef(lines)
    lu = pd.read_parquet(LU)
    rows += [_one(a, float(v), "p_LUUnits") for a, v in zip(lu.act, lu.value)]
    rows += pig_requirements(dat)
    return pd.DataFrame(rows, columns=["symbol", "key1", "key2", "key3", "key4", "key5", "value"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gams", default=str(SOURCES / "gams"))
    ap.add_argument("--dat", default=str(SOURCES / "dat"))
    a = ap.parse_args()
    t = build(Path(a.gams), Path(a.dat))
    t.to_csv(OUT, index=False)
    print(f"{OUT.relative_to(ROOT)}: {len(t)} rows; " + ", ".join(f"{s} {n}" for s, n in t.symbol.value_counts().items()))


if __name__ == "__main__":
    main()
