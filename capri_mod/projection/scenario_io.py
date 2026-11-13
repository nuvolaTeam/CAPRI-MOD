"""A projection trajectory as a scenario folder, capri_data/scenarios/<name>/ (converted from
capri_data/2030/<name>.json on 31 October 2026; the project lead's rule: a scenario's settings and its
reference data in separate files, in a scenario folder).

    settings.toml   name, source, vintage, base_year, target_years, notes (optional) and [provenance] (optional)
    growth.csv      block, item, year, factor          growth[block][item][year], the trajectory's factors
    regional.csv    block, region, item, year, factor  regional[block][region][item][year], the per-region detail
A folder without growth.csv drives nothing (the null trajectory); without regional.csv it has no regional detail.

read() gives the document the JSON file held (the keys of BaselineTrajectory.from_dict, notes as "_note", provenance as
"_provenance"; the years as strings, the factors as floats written with repr); write() writes it.
"""
from __future__ import annotations

import csv
import json
import tomllib
from pathlib import Path

SETTINGS = "settings.toml"
GROWTH = ["block", "item", "year", "factor"]
REGIONAL = ["block", "region", "item", "year", "factor"]
_SCALARS = ("name", "source", "vintage", "base_year", "target_years")


def folder_of(path) -> Path:
    """The scenario folder of a path: the folder itself or its settings.toml."""
    p = Path(path)
    return p.parent if p.name == SETTINGS else p


def read(path) -> dict:
    folder = folder_of(path)
    f = folder / SETTINGS
    if not f.exists():
        raise FileNotFoundError(f"scenario settings {f} are missing")
    with open(f, "rb") as fh:
        s = tomllib.load(fh)
    doc = {k: s[k] for k in _SCALARS if k in s}
    doc["growth"] = {}
    g = folder / "growth.csv"
    if g.exists():
        for block, item, year, factor in _rows(g, GROWTH):
            doc["growth"].setdefault(block, {}).setdefault(item, {})[year] = float(factor)
    r = folder / "regional.csv"
    if r.exists():
        doc["regional"] = {}
        for block, region, item, year, factor in _rows(r, REGIONAL):
            doc["regional"].setdefault(block, {}).setdefault(region, {}).setdefault(item, {})[year] = float(factor)
    if "notes" in s:
        doc["_note"] = s["notes"]
    if "provenance" in s:
        doc["_provenance"] = s["provenance"]
    return doc


def write(folder, doc: dict) -> None:
    """Write a trajectory document (the keys read() gives) to its folder; other keys are refused."""
    folder = Path(folder)
    other = set(doc) - set(_SCALARS) - {"growth", "regional", "_note", "_provenance"}
    if other:
        raise ValueError(f"trajectory keys {sorted(other)} have no place in a scenario folder")
    folder.mkdir(parents=True, exist_ok=True)
    lines = [f"{k} = {_toml(doc[k])}" for k in _SCALARS if k in doc]
    if "_note" in doc:
        lines.append(f"notes = {_toml(doc['_note'])}")
    if "_provenance" in doc:
        lines += ["", "[provenance]"] + [f"{k} = {_toml(v)}" for k, v in doc["_provenance"].items()]
    (folder / SETTINGS).write_text("\n".join(lines) + "\n")
    growth = doc.get("growth") or {}
    _write(folder / "growth.csv", GROWTH,
           ([b, i, str(y), repr(float(f))] for b, items in growth.items() for i, ys in items.items() for y, f in ys.items()),
           keep=bool(growth))
    if "regional" in doc:
        _write(folder / "regional.csv", REGIONAL,
               ([b, r, i, str(y), repr(float(f))] for b, regs in doc["regional"].items() for r, items in regs.items()
                for i, ys in items.items() for y, f in ys.items()), keep=True)
    elif (folder / "regional.csv").exists():
        (folder / "regional.csv").unlink()
    want = dict(doc, growth={b: {i: {str(y): float(f) for y, f in ys.items()} for i, ys in items.items()}
                             for b, items in growth.items()})
    if "regional" in doc:
        want["regional"] = {b: {r: {i: {str(y): float(f) for y, f in ys.items()} for i, ys in items.items()}
                                for r, items in regs.items()} for b, regs in doc["regional"].items()}
    if read(folder) != want:                     # the years as JSON wrote them (strings)
        raise ValueError(f"{folder}: the written scenario does not read back as the trajectory written")


def _toml(v) -> str:
    """A TOML value of the simple kinds a trajectory's settings hold (strings, integers, floats, flat lists)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)              # a JSON string is a TOML basic string
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml(x) for x in v) + "]"
    raise TypeError(f"no TOML form here for {type(v).__name__}")


def _write(path: Path, header, rows, keep: bool) -> None:
    if not keep:
        if path.exists():
            path.unlink()
        return
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def _rows(path: Path, header) -> list:
    with open(path, newline="") as fh:
        r = csv.reader(fh)
        head = next(r, None)
        if head != header:
            raise ValueError(f"{path}: header {head}, expected {header}")
        return list(r)
