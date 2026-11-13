"""The lines of a text file, or of every file in a zip archive, that match a pattern: `grep -E` in Python.

The builders read CAPRI's large GAMS text listings (dataOut and the market exports, up to 388 MB) for a few items. Until
31 October 2026 they ran `grep -E` (and `unzip -p | grep -E` for a zip) as a subprocess, which needs those Unix tools;
this function returns the same text on any system, with Python's standard library only (re, zipfile):

    from _grep import grep
    txt = grep(r"^'[A-Z0-9]{8}'\\.''\\.'(MTRADE|EXCRET)'\\.'NITF'\\.'2030'", ref)     # as grep -E PATTERN FILE
    txt = grep(pattern, "res_2_1730greendeal_refdefaulta.zip")                     # as unzip -p ZIP | grep -E

The text is grep's as the builders read it (subprocess with text=True): the matching lines in file order, each ended
by a newline (a Windows line end read as one, universal newlines); "" when none matches. Several files (a list) are
read in order, as `grep -h PATTERN FILE...`. The patterns the builders use are extended regular expressions that
Python's re reads alike (anchors, classes, counts, alternation).
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path


def _lines(fh):
    for raw in fh:
        yield raw[:-1] if raw.endswith(b"\n") else raw


def _members(path: Path):
    """The file's lines, or every member's of a zip archive in the archive's order (unzip -p)."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                with z.open(info) as fh:
                    yield from _lines(fh)
    else:
        with open(path, "rb") as fh:
            yield from _lines(fh)


def lines(path):
    """Every line of the file, or of every member of a zip archive (as `unzip -p`), as text without its line end, one at
    a time (for the builders that read a whole listing; open(path, errors="ignore") on a plain file until 9 November
    2026, when the 2030 baseline's listing became the zip res_2_1730greendeal_refdefaulta.zip)."""
    for raw in _members(Path(path)):
        yield raw.decode("utf-8", errors="ignore").rstrip("\r")


def grep(pattern: str, paths) -> str:
    """The lines of the file(s) that match the extended regular expression, as grep -E (-h) prints them."""
    rx = re.compile(pattern.encode("latin-1"))
    out = []
    for p in ([paths] if isinstance(paths, (str, Path)) else list(paths)):
        out.extend(line for line in _members(Path(p)) if rx.search(line))
    # as the builders read grep's output (subprocess, text=True): line ends in universal-newline form
    return b"".join(line + b"\n" for line in out).decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
