"""Where capri_mod's code iterates in a set's order (the code quality plan, step 1's scan). A set of str iterates in
the hash order, which PYTHONHASHSEED changes. Reported: a loop, comprehension or a call that consumes an iterable in
its order (list, tuple, dict, np.array, sum, enumerate, zip, map, join, min/max ties aside) over
- a set expression: set(...), frozenset(...), a set literal or comprehension, a | b, a - b, a & b, a ^ b of sets,
  .union/.difference/.intersection/.symmetric_difference, dict.keys() | ...;
- a name assigned a set expression in the same function (or module), not reassigned otherwise.
Not reported: sorted(...) of it, membership tests, len, set-to-set operations, any()/all().
    python tools/check/scan_set_order.py capri_mod [--out CSV]   # module paths from ROOT's parent"""
import ast
import csv
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
OUT = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
SET_METHODS = {"union", "difference", "intersection", "symmetric_difference"}
CONSUMERS = {"list", "tuple", "dict", "enumerate", "zip", "map", "filter", "sum", "array", "asarray", "fromiter",
             "join", "Series", "DataFrame", "Index", "extend", "update", "concat", "vstack", "hstack", "stack",
             "fsum", "prod", "reduce", "next", "iter"}


def is_set_expr(n, setnames):
    if isinstance(n, (ast.Set, ast.SetComp)):
        return True
    if isinstance(n, ast.Call):
        f = n.func
        if isinstance(f, ast.Name) and f.id in ("set", "frozenset"):
            return True
        if isinstance(f, ast.Attribute) and f.attr in SET_METHODS and is_set_expr(f.value, setnames):
            return True
        if isinstance(f, ast.Attribute) and f.attr in SET_METHODS and isinstance(f.value, ast.Name) \
                and f.value.id in setnames:
            return True
    if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.BitOr, ast.Sub, ast.BitAnd, ast.BitXor)):
        return is_set_expr(n.left, setnames) or is_set_expr(n.right, setnames)
    if isinstance(n, ast.Name) and n.id in setnames:
        return True
    return False


def scan(path):
    src = path.read_text()
    tree = ast.parse(src)
    hits = []
    lines = src.splitlines()

    def scope_setnames(body_nodes):
        """Names assigned a set expression in a scope, and never assigned anything else there."""
        sets, other = set(), set()
        for n in body_nodes:
            for m in ast.walk(n):
                if isinstance(m, ast.Assign):
                    for t in m.targets:
                        if isinstance(t, ast.Name):
                            (sets if is_set_expr(m.value, set()) else other).add(t.id)
                elif isinstance(m, ast.AnnAssign) and isinstance(m.target, ast.Name) and m.value is not None:
                    (sets if is_set_expr(m.value, set()) else other).add(m.target.id)
                elif isinstance(m, ast.AugAssign) and isinstance(m.target, ast.Name) and \
                        isinstance(m.op, (ast.BitOr, ast.Sub, ast.BitAnd)):
                    pass
        return sets - other

    def where(n):
        return n.lineno, lines[n.lineno - 1].strip()[:150]

    def check(nodes, setnames, ctx):
        par = {}
        for n in nodes:
            for m in ast.walk(n):
                for c in ast.iter_child_nodes(m):
                    par[c] = m
        for n in nodes:
            for m in ast.walk(n):
                it = None
                if isinstance(m, (ast.For, ast.AsyncFor)):
                    it = m.iter
                elif isinstance(m, ast.comprehension):
                    it = m.iter
                    # a set or dict-of-set comprehension whose result is itself a set: still ordered input to a set
                    owner = par.get(m)
                    if isinstance(owner, ast.SetComp) or (isinstance(owner, ast.GeneratorExp) and isinstance(
                            par.get(owner), ast.Call) and isinstance(par[owner].func, ast.Name)
                            and par[owner].func.id in ("set", "frozenset", "any", "all", "sorted", "len", "min", "max")):
                        continue
                    if isinstance(owner, (ast.ListComp, ast.DictComp, ast.GeneratorExp)):
                        q = par.get(owner)
                        if isinstance(q, ast.Call) and isinstance(q.func, ast.Name) and q.func.id == "sorted":
                            continue
                elif isinstance(m, ast.Call):
                    f = m.func
                    name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
                    if name in CONSUMERS and m.args and is_set_expr(m.args[0], setnames):
                        q = par.get(m)
                        if not (isinstance(q, ast.Call) and isinstance(q.func, ast.Name) and q.func.id == "sorted"):
                            ln, txt = where(m)
                            hits.append((ln, ctx, f"{name}(set)", txt))
                    continue
                if it is not None and is_set_expr(it, setnames):
                    ln, txt = where(m if hasattr(m, "lineno") else it)
                    hits.append((ln, ctx, "for/comprehension over a set", txt))

    mod_sets = scope_setnames([n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                                             ast.ClassDef))])
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            check(n.body, scope_setnames(n.body) | mod_sets, n.name)
    check([n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))],
          mod_sets, "<module>")
    return sorted(set(hits))


rows = []
for p in sorted(ROOT.rglob("*.py")):
    if "tests" in p.parts:
        continue
    for ln, ctx, kind, txt in scan(p):
        rows.append((p.relative_to(ROOT.parent).as_posix(), ln, ctx, kind, txt))
print(len(rows), "places in", len({r[0] for r in rows}), "modules")
if OUT:
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["module", "line", "function", "kind", "code"])
        w.writerows(rows)
