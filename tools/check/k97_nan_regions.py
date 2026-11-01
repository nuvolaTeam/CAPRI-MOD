"""K97: which regions' solves meet the NaN in a constraint row (CasADi's "nlp_g failed: NaN detected"), diagnostics only.

Runs tools/run/run_f2f_2030.py with CapriRegionalNLP.solve wrapped: each solve's C-level output (stdout and stderr,
where CasADi writes its warnings) goes to a temporary file, the NaN warnings in it are counted with the row, and one
line per solve with any is appended to the report: region, start (warm or cold), rows, count, status, iterations. The
region is the calling supply model's (self.data.region_id two frames up). The wrapper is installed before the worker
processes fork, so it acts in them too. Results are those of the plain run (the wrapper only redirects output).

    python tools/check/k97_nan_regions.py REPORT.csv -- [run_f2f_2030.py arguments, e.g. --scenario greendeal2030 OUT.pkl]
"""
from __future__ import annotations

import collections
import inspect
import os
import re
import runpy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
NAN = re.compile(r"NaN detected for output (\w+), at \(row (\d+)")


def main():
    if "--" not in sys.argv:
        sys.exit(__doc__)
    i = sys.argv.index("--")
    report, run_args = Path(sys.argv[1]), sys.argv[i + 1:]
    report.write_text("region,start,rows,count,status,iterations\n")
    from capri_mod.supply import capri_regional_nlp as M
    orig = M.CapriRegionalNLP.solve

    def solve(self, x0, max_iter=None, tol=1e-8, print_level=0, lam=None):
        region = "?"
        for fr in inspect.stack()[1:4]:
            obj = fr.frame.f_locals.get("self")
            rid = getattr(getattr(obj, "data", None), "region_id", None)
            if rid:
                region = rid
                break
        sys.stdout.flush(); sys.stderr.flush()
        with tempfile.TemporaryFile(mode="w+b") as tmp:
            saved = os.dup(1), os.dup(2)
            os.dup2(tmp.fileno(), 1); os.dup2(tmp.fileno(), 2)
            try:
                r = orig(self, x0, max_iter=max_iter, tol=tol, print_level=print_level, lam=lam)
            finally:
                sys.stdout.flush(); sys.stderr.flush()
                os.dup2(saved[0], 1); os.dup2(saved[1], 2); os.close(saved[0]); os.close(saved[1])
            tmp.seek(0)
            text = tmp.read().decode("utf-8", "replace")
        hits = NAN.findall(text)
        if hits:
            rows = collections.Counter(f"{o}{r_}" for o, r_ in hits)
            with open(report, "a") as fh:
                fh.write(f"{region},{'warm' if lam is not None else 'cold'},{'+'.join(sorted(rows))},{len(hits)},"
                         f"{r['status']},{r['iterations']}\n")
        # what the solve printed apart from the NaN warnings goes to the run's log as before
        rest = "\n".join(l for l in text.splitlines() if "NaN detected" not in l)
        if rest.strip():
            print(rest, file=sys.stderr)
        return r

    M.CapriRegionalNLP.solve = solve
    sys.argv = [str(ROOT / "tools" / "run" / "run_f2f_2030.py")] + run_args
    runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    main()
