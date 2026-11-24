"""The inventory of CAPRI statements the CAPTRD pipeline (capri_mod/pipeline/captrd) ports or cites: one row per
citation of a CAPRI GAMS file's lines, with the module and function that holds it, what the cited first line is in
CAPRI star 3.0 (an assignment, an equation, a declaration, a control statement, a comment) and a status:
  in style     the citation is in capri_mod/pipeline/captrd/equations (a named function quoting its statement);
  moved        a citation outside equations/ of lines an equations/ function quotes (the caller's comment);
  to move      an assignment or a bound outside equations/: a statement block for the refactor's C5 blocks;
  context      a declaration, a control statement, a comment, or a file cited without lines;
  check        the cited lines are not in the file (beyond its end) or the file is not in the copy.
A bare "l. a-b" is attributed to the last .gms file named before it on the same line, else in the same docstring or
comment block, else earlier in the same function, else to the module's files from the most cited: the first of these
the range fits in (the attribution column says which; the later ones are a guess).
    python tools/check/captrd_inventory.py GAMS_DIR [--out docs/dev/captrd_inventory.csv]"""
from __future__ import annotations

import argparse
import ast
import csv
import io
import re
import sys
import tokenize
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "capri_mod" / "pipeline" / "captrd"
FILE_RE = re.compile(r"([A-Za-z0-9_./\\]+\.gms)", re.I)
CIT_RE = re.compile(r"(?:([A-Za-z0-9_./\\]+\.gms)(?:,|:)?\s+)?\bl\.\s*(\d{1,5})(?:\s*-\s*(\d{1,5}))?", re.I)


def texts(path: Path):
    """(line number, text, block id) of the module's docstrings and comments: a docstring is one block, consecutive
    comment lines another."""
    src = path.read_text(encoding="utf-8")
    out = []
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            b = node.body[0]
            if isinstance(b, ast.Expr) and isinstance(getattr(b, "value", None), ast.Constant) and \
                    isinstance(b.value.value, str):
                for i, line in enumerate(b.value.value.split("\n")):
                    out.append((b.lineno + i, line, ("doc", b.lineno)))
    last, blk = None, None
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            ln = tok.start[0]
            if last is None or ln != last + 1:
                blk = ("com", ln)
            out.append((ln, tok.string, blk))
            last = ln
    return sorted(out)


def enclosing(tree):
    """line -> the innermost function (Class.method) holding it."""
    spans = []

    def walk(node, prefix=""):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + ch.name
                spans.append((ch.lineno, ch.end_lineno, name))
                walk(ch, name + ".")
            else:
                walk(ch, prefix)
    walk(tree)

    def at(line):
        best = None
        for a, b, name in spans:
            if a <= line <= b and (best is None or a >= best[0]):
                best = (a, name)
        return best[1] if best else "(module)"
    return at


class Copy:
    def __init__(self, root: Path):
        self.root, self.cache = root, {}

    def resolve(self, name: str):
        name = name.replace("\\", "/").strip("./")
        if name.lower().startswith("gams/"):
            name = name[5:]
        for cand in (self.root / name, self.root / "captrd" / name):
            if cand.exists():
                return cand.relative_to(self.root).as_posix()
        hits = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*.gms")
                      if p.name.lower() == Path(name).name.lower())
        return hits[0] if len(hits) == 1 else (next((h for h in hits if h.startswith("captrd/")), None))

    def lines(self, rel):
        if rel not in self.cache:
            self.cache[rel] = (self.root / rel).read_text(encoding="latin-1").split("\n")
        return self.cache[rel]


def kind(line: str) -> str:
    s = line.strip()
    low = s.lower()
    if not s:
        return "blank"
    if line.startswith("*") or low.startswith("$ontext") or low.startswith("$offtext"):
        return "comment"
    if low.startswith("$"):
        return "control ($)"
    if re.match(r"^(set|sets|parameter|parameters|scalar|scalars|table|alias|variable|variables|positive|equation|"
                r"equations|model)\b", low):
        return "declaration"
    if re.match(r"^(loop|if|else|elseif|while|for|option|solve|display|execute|put|abort)\b", low):
        return "control"
    if ".." in s and not re.search(r"(?<![<>=])=(?!=)", s.split("..")[0]):
        return "equation"
    if re.search(r"\.(lo|up|fx|l|m)\s*\(", low) and "=" in s:
        return "bound"
    if "=" in s or low.endswith(")") or low.endswith("$"):
        return "assignment"
    return "other"


def scan(gams_dir: Path):
    cp = Copy(gams_dir)
    rows = []
    for path in sorted(PKG.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        src = path.read_text(encoding="utf-8")
        at = enclosing(ast.parse(src))
        tx = texts(path)
        # the module's most cited file
        files = Counter(FILE_RE.findall(src))
        block_file, func_file = {}, {}
        for ln, line, blk in tx:
            fn = at(ln)
            last_on_line = None
            for m in re.finditer(r"([A-Za-z0-9_./\\]+\.gms)(?:(?:,|:)?\s+l\.\s*(\d{1,5})(?:\s*-\s*(\d{1,5}))?)?|"
                                 r"\bl\.\s*(\d{1,5})(?:\s*-\s*(\d{1,5}))?", line, re.I):
                if m.group(1):
                    last_on_line = m.group(1)
                    block_file[blk] = m.group(1)
                    func_file[fn] = m.group(1)
                    if m.group(2) is None:
                        rows.append(dict(module=rel, line=ln, function=fn, gms=m.group(1), a=None, b=None,
                                         attribution="named"))
                        continue
                    a, b, how = int(m.group(2)), int(m.group(3) or m.group(2)), "named"
                    f = m.group(1)
                else:
                    a, b = int(m.group(4)), int(m.group(5) or m.group(4))
                    cands = []
                    if last_on_line:
                        cands.append((last_on_line, "same line"))
                    if blk in block_file:
                        cands.append((block_file[blk], "same block"))
                    if fn in func_file:
                        cands.append((func_file[fn], "same function"))
                    cands += [(g, "module's file") for g, _n in files.most_common()]
                    rows.append(dict(module=rel, line=ln, function=fn, gms=None, a=a, b=b, attribution="",
                                     cands=cands))
                    continue
                rows.append(dict(module=rel, line=ln, function=fn, gms=f, a=a, b=b, attribution=how))
    out = []
    for r in rows:
        if "cands" in r:                       # a bare citation: the first candidate file the range fits in
            fit = None
            for g, how in r.pop("cands"):
                rg = cp.resolve(g)
                if rg and r["b"] <= len(cp.lines(rg)):
                    fit = (g, how)
                    break
            r["gms"], r["attribution"] = fit if fit else (None, "none fits")
        res = cp.resolve(r["gms"]) if r["gms"] else None
        if res is None:
            r.update(capri_file=r["gms"] or "", first_line="", kind="", status="check",
                     note="file not in the copy" if r["gms"] else "no cited file holds these lines")
        elif r["a"] is None:
            r.update(capri_file=res, first_line="", kind="file", status="context", note="")
        else:
            L = cp.lines(res)
            if r["a"] > len(L):
                r.update(capri_file=res, first_line="", kind="", status="check", note=f"beyond the file's {len(L)} lines")
            else:
                first = L[r["a"] - 1]
                k = kind(first)
                if k in ("comment", "blank"):          # a range starting on a comment: the first code line in it
                    for j in range(r["a"], min(r["b"], len(L))):
                        if kind(L[j]) not in ("comment", "blank"):
                            first, k = L[j], kind(L[j])
                            break
                if "/captrd/equations/" in r["module"]:
                    st = "in style"
                elif k in ("assignment", "bound", "equation"):
                    st = "to move"
                else:
                    st = "context"
                r.update(capri_file=res, first_line=" ".join(first.split())[:140], kind=k, status=st, note="")
        out.append(r)
    # a citation of lines an equations/ function quotes: the statement has moved (the caller's comment points at it)
    quoted = {}
    for r in out:
        if r["status"] == "in style" and r["a"] is not None:
            quoted.setdefault(r["capri_file"], []).append((r["a"], r["b"]))
    for r in out:
        if r["status"] == "to move" and any(a <= r["b"] and r["a"] <= b for a, b in quoted.get(r["capri_file"], ())):
            r["status"] = "moved"
            r["note"] = "the statement is in capri_mod/pipeline/captrd/equations; this cites it"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("gams_dir", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    rows = scan(a.gams_dir)
    cols = ["capri_file", "lines", "kind", "status", "module", "function", "line", "attribution", "first_line", "note"]
    rows.sort(key=lambda r: (r["capri_file"], r["a"] or 0, r["b"] or 0, r["module"], r["line"]))
    fh = open(a.out, "w", newline="") if a.out else sys.stdout
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(cols)
    for r in rows:
        lines = "" if r["a"] is None else (f"{r['a']}-{r['b']}" if r["b"] != r["a"] else str(r["a"]))
        w.writerow([r["capri_file"], lines, r["kind"], r["status"], r["module"], r["function"], r["line"],
                    r["attribution"], r["first_line"], r["note"]])
    st = Counter(r["status"] for r in rows)
    print(f"{len(rows)} citations: {dict(st)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
