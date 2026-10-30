"""Readers of GAMS text: data statements of CAPRI's .gms files and gdxdump output.

parameter_list and table read the data statements of CAPRI's include files as tools/build/build_captrd_dat.py read
them before the sources were converted to CSV (30 October 2026): GAMS labels upper-cased (GAMS is case-insensitive),
values as floats. parameter_records and table_records are the same readers returning the labels and the numbers as
the file writes them (tools/build/convert_sources_to_csv.py writes those). gdxdump_symbols reads the text gdxdump
writes (`Parameter p(*,*) text / 'a'.'b' value, ... /;` and sets).
"""
from __future__ import annotations

import io
import re
from pathlib import Path


def read_text(src, encoding: str = "latin-1") -> str:
    """The text of a file (a path) or of its bytes, with universal newlines as Path.read_text gives it."""
    if isinstance(src, (bytes, bytearray)):
        return io.TextIOWrapper(io.BytesIO(src), encoding=encoding, newline=None).read()
    return Path(src).read_text(encoding=encoding)


def parameter_records(text: str, name: str, dim: int, where: str = ""):
    """The records of `parameter name(...) "text" / k1.k2 value ... /;` (comment lines starting with * skipped), as
    written: (key 1, ..., key dim, value text); "BioD .RAPO" is read as BioD.RAPO. As build_captrd_dat.py read them
    before 30 October 2026, but for a quoted text holding a slash (p_secgConv "... (t/t)", which it did not read)."""
    # the explanatory text may hold a slash when quoted ("... (t/t)")
    m = re.search(rf"parameter\s+{name}\s*(?:\([^)]*\))?\s*(?:\"[^\"]*\"|'[^']*'|[^/\"']*)\s*/(.*?)/\s*;", text,
                  flags=re.I | re.S)
    if not m:
        raise KeyError(f"{name} not in {where}")
    out = []
    for ln in m.group(1).splitlines():
        if not ln.strip() or ln.lstrip().startswith("*"):
            continue
        s = re.sub(r"\s*\.\s*", ".", ln.strip())           # "BioD .RAPO" -> "BioD.RAPO"
        parts = s.split()
        if len(parts) != 2:
            raise ValueError(f"{where}: {name}: unreadable line {ln!r}")
        keys = parts[0].split(".")
        if len(keys) != dim:
            raise ValueError(f"{where}: {name}: {dim} keys expected in {ln!r}")
        out.append((*keys, parts[1]))
    if len({tuple(k.upper() for k in r[:-1]) for r in out}) != len(out):
        raise ValueError(f"{where}: {name}: duplicate keys")
    return out


def parameter_list(path: Path, name: str, dim: int):
    """The records of `parameter name(...) "text" / k1.k2 value ... /;`: (KEY 1, ..., KEY dim, float value)."""
    return [(*(k.upper() for k in r[:-1]), float(r[-1]))
            for r in parameter_records(read_text(path), name, dim, str(path))]


def table_records(text: str, name: str, row_dims: int, where: str = ""):
    """The records of `Table name(...) "text"` (GAMS table: a header line of column labels, then rows of a label of
    row_dims parts joined by dots and numbers in the columns they overlap), as written: (row keys..., column, value
    text)."""
    lines = text.splitlines()
    k = next(i for i, ln in enumerate(lines) if re.match(rf"\s*table\s+{name}\s*\(", ln, flags=re.I))
    i = k + 1
    while not lines[i].strip() or lines[i].lstrip().startswith("*"):
        i += 1
    head = lines[i]
    cols = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", head)]
    out = []
    for ln in lines[i + 1:]:
        s = ln.rstrip()
        if s.strip() == ";" or s.strip().endswith(";") and not re.search(r"\d", s):
            break
        if not s.strip() or s.lstrip().startswith("*"):
            continue
        toks = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", s)]
        label, j = "", 0
        while j < len(toks):
            label += toks[j][2]
            j += 1
            if label.count(".") >= row_dims - 1 and not label.endswith(".") and not (
                    j < len(toks) and toks[j][2].startswith(".")):
                break
        keys = [x.strip() for x in label.split(".")]
        if len(keys) != row_dims:
            raise ValueError(f"{where}: {name}: unreadable row label in {ln!r}")
        for a, b, v in toks[j:]:
            ov = [(min(b, ce) - max(a, cs), cn) for cs, ce, cn in cols]
            best = max(ov)
            if best[0] <= 0:
                raise ValueError(f"{where}: {name}: value {v!r} under no column in {ln!r}")
            float(v)                                         # a number, as table() requires
            out.append((*keys, best[1], v))
    return out


def table(path: Path, name: str, row_dims: int):
    """The records of `Table name(...) "text"`: (ROW KEYS..., COLUMN, float value)."""
    return [(*(k.upper() for k in r[:-2]), r[-2].upper(), float(r[-1]))
            for r in table_records(read_text(path), name, row_dims, str(path))]


_LABEL = r"(?:'[^']*'|\"[^\"]*\")"
_HEAD = re.compile(r"^(Parameter|Set|Scalar)\s+(\w+)(?:\(([^)]*)\))?\s*(.*?)\s*/\s*$", re.I)
_REC = re.compile(rf"^({_LABEL}(?:\.{_LABEL})*)\s*(.*)$")


def gdxdump_symbols(text: str, where: str = ""):
    """The symbols of a gdxdump text: [(kind, name, dims, description, records)], a record being (key 1, ..., key n,
    value text) for a parameter and (key 1, ..., key n, element text or "") for a set; labels without their quotes."""
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        m = _HEAD.match(lines[i].strip())
        if not m:
            if lines[i].strip() and not lines[i].strip().startswith("$"):
                raise ValueError(f"{where}: line {i + 1} not understood: {lines[i]!r}")
            i += 1
            continue
        kind, name, dom, desc = m.group(1), m.group(2), m.group(3), m.group(4)
        dims = len(dom.split(",")) if dom else 0
        recs = []
        while True:
            i += 1
            s = lines[i].strip()
            end = s.endswith("/;")
            body = s[:-2].strip() if end else s
            if body:
                r = _REC.match(body)
                if not r:
                    raise ValueError(f"{where}: {name}: line {i + 1} not understood: {lines[i]!r}")
                keys = [k[1:-1] for k in re.findall(_LABEL, r.group(1))]
                if len(keys) != dims:
                    raise ValueError(f"{where}: {name}: {dims} keys expected on line {i + 1}")
                rest = r.group(2).strip()
                rest = rest[:-1].strip() if rest.endswith(",") else rest
                if kind.lower() == "set":
                    rest = rest[1:-1] if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in "'\"" else rest
                elif not rest:
                    raise ValueError(f"{where}: {name}: no value on line {i + 1}")
                recs.append((*keys, rest))
            if end:
                break
        out.append((kind, name, dims, desc, recs))
        i += 1
    return out
