"""A reader of GAMS set definitions: the data statements of CAPRI's set files, for the builders that transcribe them.

What it reads, as GAMS does (GAMS user's guide, "Sets" and "Data entry"):
  - set (sets, alias) declarations with data (a set declared again adds its data to the members, as with CAPRI's
    $onMulti):  set NAME(domain) 'text' / element list / ;  several in one statement
    (set a /.../, b /.../;); declarations without data (set NAME(domain) 'text';) define an empty set
  - element lists: one element per line or several separated by commas; an element is a label, a quoted label or a
    tuple of them joined by '.', where any part can be a parenthesised list (a.(b,c) is a.b and a.c) or a range
    (1970*2040, a1*a9); 'set.NAME' or 'NAME' preceded by 'set.' inserts the members of a set read before; the rest of
    the line after an element is its explanatory text and is dropped
  - alias(a, b, ...)
  - $ontext / $offtext, comment lines (* in column 1), $include of another file (relative to a root folder), $setglobal
    and %name% substitution, $ifi / $if with a comparison of %names% (==), $exit
Everything else (assignments, loops, displays, aborts, parameters) is returned unparsed, with its file and line, for the
builder to transcribe by hand (GAMS's set assignments are few in these files).

Labels are kept as written; GAMS compares them case-insensitively, so lookups use upper case (key()).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def key(label: str) -> str:
    return label.upper()


@dataclass
class GamsSets:
    sets: Dict[str, List[Tuple[str, ...]]] = field(default_factory=dict)     # key(name) -> members, in order
    names: Dict[str, str] = field(default_factory=dict)                      # key(name) -> name as declared
    aliases: Dict[str, str] = field(default_factory=dict)                    # key(alias) -> key(set)
    unparsed: List[Tuple[str, int, str]] = field(default_factory=list)       # (file, line, statement)
    globals: Dict[str, str] = field(default_factory=dict)

    def get(self, name: str) -> List[Tuple[str, ...]]:
        k = key(name)
        k = self.aliases.get(k, k)
        return self.sets[k]

    def has(self, name: str) -> bool:
        k = key(name)
        return self.aliases.get(k, k) in self.sets

    def put(self, name: str, members: List[Tuple[str, ...]]) -> None:
        seen, out = set(), []
        for m in members:
            km = tuple(key(x) for x in m)
            if km not in seen:
                seen.add(km)
                out.append(m)
        self.sets[key(name)] = out
        self.names.setdefault(key(name), name)


_LABEL = r"(?:'[^']*'|\"[^\"]*\"|[A-Za-z0-9_+\-#@&%$!?|\[\]{}<>~^`:]+(?:\.\.[A-Za-z0-9_+\-#@&%$!?]+)*)"


class _Text:
    """The statements of a file with $-control lines applied, each with its first line number."""

    def __init__(self, root: Path, globals_: Dict[str, str]):
        self.root, self.g = root, globals_

    def lines(self, path: Path):
        skip, out = False, []
        for no, raw in enumerate(path.read_text(encoding="latin-1").splitlines(), 1):
            s = raw.rstrip("\n")
            low = s.strip().lower()
            if low.startswith("$ontext"):
                skip = True
                continue
            if low.startswith("$offtext"):
                skip = False
                continue
            if skip or s.startswith("*"):
                continue
            s = re.sub(r"%(\w+(?:\.\w+)?)%", lambda m: self.g.get(m.group(1).lower(), m.group(0)), s)
            st = s.strip()
            if s.startswith("$"):                 # compile-time commands start in column 1; an indented $ is a condition
                yield from self._control(path, no, st)
                continue
            out.append((path, no, s))
            yield (path, no, s)

    def _control(self, path, no, st):
        m = re.match(r"\$\$?(\w+)\s*(.*)", st)
        if not m:
            return
        cmd, rest = m.group(1).lower(), m.group(2).strip()
        if cmd in ("setglobal", "setlocal", "set"):
            parts = rest.split(None, 1)
            if parts:
                self.g[parts[0].lower()] = parts[1].strip() if len(parts) > 1 else ""
        elif cmd in ("include", "batinclude"):
            f = rest.split()[0].strip("'\"")
            p = (self.root / f) if not Path(f).is_absolute() else Path(f)
            if p.exists():
                yield from self.lines(p)
            else:
                yield (path, no, f"$include {f}  (not found)")
        elif cmd in ("if", "ifi", "ifthen", "ifthenI"):
            cm = re.match(r"(not\s+)?(\S+?)\s*==\s*(\S+)\s+(.*)", rest, flags=re.I)
            if cm:
                a, b = cm.group(2).strip("'\""), cm.group(3).strip("'\"")
                eq = (a.lower() == b.lower()) if cmd == "ifi" else (a == b)
                if bool(cm.group(1)) != eq:
                    tail = cm.group(4).strip()
                    if tail.startswith("$"):
                        yield from self._control(path, no, tail)
                    else:
                        yield (path, no, tail)
            else:
                yield (path, no, st)
        elif cmd == "exit":
            raise StopIteration
        elif cmd in ("onundf", "offundf", "onmulti", "offmulti", "oneolcom", "offeolcom", "onempty", "offempty",
                     "onlisting", "offlisting", "title", "stitle", "ondotl", "offdotl", "onglobal", "offglobal"):
            return
        else:
            yield (path, no, st)


def _statements(text: _Text, path: Path):
    """Statements ended by ';' outside quotes and outside / data / lists, with their first line."""
    buf, first, in_data = [], None, False
    q = None
    try:
        for p, no, s in text.lines(path):
            if first is None and s.strip():
                first = (p, no)
            buf.append(s)
            i = 0
            while i < len(s):
                c = s[i]
                if q:
                    if c == q:
                        q = None
                elif c in "'\"":
                    q = c
                elif c == "/":
                    in_data = not in_data
                elif c == ";" and not in_data:
                    stmt = "\n".join(buf)
                    cut = len(stmt) - (len(s) - i)
                    yield first, stmt[:cut]
                    rest = s[i + 1:]
                    buf, first = ([rest] if rest.strip() else []), ((p, no) if rest.strip() else None)
                    s, i = rest, -1
                i += 1
            q = None                       # a quote does not run past its line
    except RuntimeError:                   # StopIteration inside a generator ($exit)
        pass
    if buf and "".join(buf).strip():
        yield first, "\n".join(buf)


def _split_top(s: str, sep: str) -> List[str]:
    out, depth, q, cur = [], 0, None, []
    for c in s:
        if q:
            cur.append(c)
            if c == q:
                q = None
            continue
        if c in "'\"":
            q = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        if c == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    out.append("".join(cur))
    return out


def _unq(x: str) -> str:
    x = x.strip()
    return x[1:-1] if len(x) >= 2 and x[0] == x[-1] and x[0] in "'\"" else x


def _range(a: str, b: str) -> List[str]:
    ma, mb = re.match(r"(.*?)(\d+)$", a), re.match(r"(.*?)(\d+)$", b)
    if not (ma and mb and ma.group(1) == mb.group(1)):
        raise ValueError(f"range {a}*{b}")
    w = len(ma.group(2)) if ma.group(2).startswith("0") else 0
    return [f"{ma.group(1)}{str(i).zfill(w)}" for i in range(int(ma.group(2)), int(mb.group(2)) + 1)]


def _part(tok: str, gs: Optional["GamsSets"] = None) -> List[str]:
    tok = tok.strip()
    if gs is not None and re.fullmatch(r"set\.\w+", tok, flags=re.I):
        return [m[0] for m in gs.get(tok.split(".", 1)[1])]
    if tok.startswith("("):
        out = []
        for x in _split_top(tok[1:-1], ","):
            out += _part(x, gs)
        return out
    if "*" in tok and not tok.startswith(("'", '"')):
        a, b = tok.split("*", 1)
        return _range(a.strip(), b.strip())
    return [_unq(tok)]


_ELEM = re.compile(r"\s*((?:\([^)]*\)|" + _LABEL + r"(?:\s*\*\s*" + _LABEL + r")?)"
                   r"(?:\s*\.\s*(?:\([^)]*\)|" + _LABEL + r"(?:\s*\*\s*" + _LABEL + r")?))*)")


def _elements(data: str, gs: GamsSets) -> List[Tuple[str, ...]]:
    out: List[Tuple[str, ...]] = []
    for line in data.splitlines():
        for piece in _split_top(line, ","):
            piece = piece.strip()
            if not piece:
                continue
            if re.fullmatch(r"set\.\w+(\s+.*)?", piece, flags=re.I | re.S) and not re.match(
                    r"set\.\w+\s*\.", piece, flags=re.I):
                out += gs.get(piece.split(".", 1)[1].split()[0])
                continue
            m = _ELEM.match(piece)
            if not m or not m.group(1).strip():
                raise ValueError(f"element {piece!r}")
            spec = m.group(1)
            # tuple parts joined by '.' (not the '..' inside Aglink's labels such as QP..ET)
            parts = [p for p in re.split(r"(?<!\.)\s*\.\s*(?![.])", spec)]
            parts = _merge_dots(spec)
            combos: List[Tuple[str, ...]] = [()]
            for p in parts:
                combos = [c + (x,) for c in combos for x in _part(p, gs)]
            out += combos
    return out


def _merge_dots(spec: str) -> List[str]:
    """spec split at the tuple dots: a '.' outside quotes and parentheses that is not part of '..'."""
    parts, cur, q, depth, i = [], [], None, 0, 0
    while i < len(spec):
        c = spec[i]
        if q:
            cur.append(c)
            if c == q:
                q = None
        elif c in "'\"":
            q = c
            cur.append(c)
        elif c == "(":
            depth += 1
            cur.append(c)
        elif c == ")":
            depth -= 1
            cur.append(c)
        elif c == "." and depth == 0:
            if "".join(cur).strip().lower() == "set":       # set.NAME: a set's members as one part
                cur.append(c)
            elif spec[i:i + 2] == ".." or (i > 0 and spec[i - 1] == "."):
                cur.append(c)
            else:
                parts.append("".join(cur).strip())
                cur = []
        else:
            cur.append(c)
        i += 1
    parts.append("".join(cur).strip())
    return parts


def _close(s: str, i: int) -> int:
    """The position of the '/' that closes a data list opened before i: the first one outside quotes (an element's
    text can hold a '/', e.g. 'national currency/t')."""
    q = None
    for j in range(i, len(s)):
        c = s[j]
        if q:
            if c == q or c == "\n":
                q = None
        elif c in "'\"":
            q = c
        elif c == "/":
            return j
    raise ValueError("data list not closed")


_DECL = re.compile(r"^\s*(sets?|singleton\s+sets?)\b(.*)$", re.I | re.S)


def _declarations(body: str, gs: GamsSets) -> None:
    """set a(dom) 'text' / data /, b 'text' / data / ..."""
    i, n = 0, len(body)
    while i < n:
        m = re.match(r"[\s,]*(\w+)\s*(\([^)]*\))?\s*(" + r"'[^']*'|\"[^\"]*\"|[^/,]*?" + r")\s*(/)?", body[i:], re.S)
        if not m or not m.group(1):
            break
        name = m.group(1)
        i += m.end()
        members: List[Tuple[str, ...]] = []
        if m.group(4):
            j = _close(body, i)
            members = _elements(body[i:j], gs)
            i = j + 1
        if gs.has(name):
            # a set declared again: CAPRI compiles with $onMulti, so the new data are added to the set's members
            if members:
                gs.put(gs.names.get(gs.aliases.get(key(name), key(name)), name), list(gs.get(name)) + members)
            continue
        gs.put(name, members)


def read(path: Path, root: Path, globals_: Optional[Dict[str, str]] = None,
         base: Optional[GamsSets] = None) -> GamsSets:
    """The sets of a GAMS file (and the files it includes, relative to root), on top of base's."""
    gs = base or GamsSets()
    gs.globals.update({k.lower(): v for k, v in (globals_ or {}).items()})
    text = _Text(root, gs.globals)
    for (p, no), stmt in _statements(text, path):
        s = stmt.strip()
        if not s:
            continue
        m = _DECL.match(s)
        if m:
            try:
                _declarations(m.group(2), gs)
            except (ValueError, KeyError) as e:
                gs.unparsed.append((str(p), no, f"{s[:200]}  [{e}]"))
            continue
        am = re.match(r"^\s*alias\s*\((.*)\)\s*$", s, re.I | re.S)
        if am:
            names = [x.strip() for x in am.group(1).split(",")]
            target = next((x for x in names if gs.has(x)), names[0])
            tk = gs.aliases.get(key(target), key(target))
            for x in names:
                if key(x) != tk:
                    gs.aliases[key(x)] = tk
            continue
        gs.unparsed.append((str(p), no, s[:300]))
    return gs
