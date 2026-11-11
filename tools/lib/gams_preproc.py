"""A small GAMS compile-time preprocessor, to read the branch of a GAMS file that a given set of control variables
selects (for porting files such as global/convert_globiom.gms, whose $if branches cover many input files).

It evaluates, in order: $ontext/$offtext; $set, $setlocal, $setglobal, $drop...; $if/$ifi/$ifE (one line, the rest of
the line being a statement or another dollar command); $ifthen/$iftheni[.tag] ... $elseif/$elseifi ... $else ...
$endif[.tag]; %name% substitution. Conditions: "a" == "b" (case-insensitive with the i forms), "set name",
"setglobal name", "setlocal name", "not" before any of them. Conditions it cannot decide ("exist", "declared",
$ifE expressions other than a numeric comparison) are reported and taken as false, so a caller sees which ones it assumed.

Comment lines (* in column 1) and $include lines are kept, so line numbers stay those of the source.

Usage: python tools/lib/gams_preproc.py FILE [name=value ...]   prints the active lines with their line numbers.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Result:
    lines: List[Tuple[int, str]] = field(default_factory=list)       # (line number, text after %name% substitution)
    undecided: List[Tuple[int, str]] = field(default_factory=list)   # conditions taken as false
    variables: Dict[str, str] = field(default_factory=dict)


_VAR = re.compile(r"%([A-Za-z_][A-Za-z0-9_.]*)%")


def _subst(s: str, v: Dict[str, str]) -> str:
    return _VAR.sub(lambda m: v.get(m.group(1).lower(), m.group(0)), s)


def _token(s: str) -> Tuple[str, str]:
    """The first token of s (a quoted string or a word up to blank or ==) and the rest."""
    s = s.lstrip()
    if s[:1] in "\"'":
        q = s[0]
        j = s.index(q, 1)
        return s[1:j], s[j + 1:]
    m = re.match(r"([^\s=]+)(.*)", s, re.S)
    return (m.group(1), m.group(2)) if m else ("", "")


def _cond(s: str, v: Dict[str, str], ci: bool) -> Tuple[Optional[bool], str]:
    """(value of the condition at the start of s or None if undecidable, the rest of s)."""
    s = s.lstrip()
    neg = False
    while re.match(r"not\s", s, re.I):
        neg = not neg
        s = s[3:].lstrip()
    m = re.match(r"(setglobal|setlocal|set|setenv)\s+(\S+)(.*)", s, re.I | re.S)
    if m:
        r = m.group(2).lower() in v
        return (r != neg), m.group(3)
    m = re.match(r"(exist|declared|defined|errorfree|dimension|warnings|errorlevel|readable|solver|putopen|"
                 r"decla_ok)\s+(\S+)(.*)", s, re.I | re.S)
    if m:
        return None, m.group(3)
    a, rest = _token(s)
    rest = rest.lstrip()
    if not rest.startswith("=="):
        return None, rest
    b, rest = _token(rest[2:])
    r = (a.lower() == b.lower()) if ci else (a == b)
    return (r != neg), rest


def _cond_e(s: str) -> Optional[bool]:
    """$ifE / $ifThenE: a numeric comparison such as "58>52" (after %name% substitution), else None."""
    e = s.strip()
    if e[:1] in "\"'":
        e = e[1:e.index(e[0], 1)]
    m = re.fullmatch(r"\s*(-?[0-9.]+)\s*(>=|<=|<>|==|=|>|<)\s*(-?[0-9.]+)\s*", e)
    if not m:
        return None
    a, op, b = float(m.group(1)), m.group(2), float(m.group(3))
    return {">": a > b, "<": a < b, ">=": a >= b, "<=": a <= b, "==": a == b, "=": a == b, "<>": a != b}[op]


def preprocess(text: str, variables: Optional[Dict[str, str]] = None) -> Result:
    v = {k.lower(): str(x) for k, x in (variables or {}).items()}
    out = Result()
    stack: List[List] = []           # [active, branch taken, tag]
    comment = False

    def active() -> bool:
        return all(f[0] for f in stack)

    def directive(n: int, s: str) -> Optional[str]:
        """Execute one dollar command (s starts with $); returns a statement to emit, if any."""
        nonlocal comment
        m = re.match(r"\$(\w+)(?:\.(\w+))?\s*(.*)", s, re.S)
        if not m:
            return None
        cmd, tag, rest = m.group(1).lower(), (m.group(2) or "").lower(), m.group(3)
        if cmd in ("ifthen", "iftheni", "ifthene"):
            if not active():
                stack.append([False, True, tag])
                return None
            if cmd == "ifthene":
                c = _cond_e(_subst(rest, v))
                if c is None:
                    out.undecided.append((n, s.strip()))
            else:
                c, _ = _cond(_subst(rest, v), v, cmd == "iftheni")
                if c is None:
                    out.undecided.append((n, s.strip()))
            stack.append([bool(c), bool(c), tag])
            return None
        if cmd in ("elseif", "elseifi", "elseife"):
            f = stack[-1]
            outer = all(g[0] for g in stack[:-1])
            if f[1] or not outer:
                f[0] = False
                return None
            c, _ = _cond(_subst(rest, v), v, cmd == "elseifi") if cmd != "elseife" else (None, "")
            if c is None:
                out.undecided.append((n, s.strip()))
            f[0] = bool(c)
            f[1] = bool(c)
            return None
        if cmd == "else":
            f = stack[-1]
            outer = all(g[0] for g in stack[:-1])
            f[0] = outer and not f[1]
            f[1] = True
            return None
        if cmd == "endif":
            stack.pop()
            return None
        if not active():
            return None
        if cmd in ("ontext",):
            comment = True
            return None
        if cmd in ("set", "setlocal", "setglobal", "eval", "evallocal", "evalglobal"):
            rest = _subst(rest, v).strip()
            name, val = (rest.split(None, 1) + [""])[:2]
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            v[name.lower()] = val
            return None
        if cmd in ("drop", "droplocal", "dropglobal"):
            v.pop(rest.strip().lower(), None)
            return None
        if cmd in ("if", "ifi", "ife"):
            if cmd == "ife":
                out.undecided.append((n, s.strip()))
                return None
            c, stmt = _cond(_subst(rest, v), v, cmd == "ifi")
            if c is None:
                out.undecided.append((n, s.strip()))
                return None
            if not c:
                return None
            stmt = stmt.strip()
            if stmt.startswith("$"):
                return directive(n, stmt)
            return stmt
        return s                     # other dollar commands ($include, $gdxin, $load, ...) are kept as they are

    for n, line in enumerate(text.splitlines(), 1):
        s = line.rstrip("\n")
        if comment:
            if re.match(r"\$offtext", s, re.I):
                comment = False
            continue
        if s.startswith("$"):                    # a compile-time command starts in column 1; an indented $ is a condition
            r = directive(n, s)
            if r is not None and active():
                out.lines.append((n, _subst(r, v)))
            continue
        if active():
            out.lines.append((n, _subst(s, v)))
    out.variables = v
    return out


if __name__ == "__main__":
    path, *kv = sys.argv[1:]
    r = preprocess(open(path, encoding="latin-1").read(), dict(a.split("=", 1) for a in kv))
    for n, s in r.lines:
        print(f"{n:5d}  {s}")
    if r.undecided:
        print("\n# conditions taken as false:", file=sys.stderr)
        for n, s in r.undecided:
            print(f"#  l. {n}: {s}", file=sys.stderr)
