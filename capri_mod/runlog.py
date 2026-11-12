"""The run's log in CAPRI's style (the project lead's request, 11 November 2026).

CAPRI writes two kinds of lines while CAPMOD runs:
  - a title per section (util/title.gms): "title CAPMOD: <section> Last: <previous section> - ( <s> sec. <min> min. )",
    the seconds since the previous title and the minutes since the start;
  - the run log caplog (capmod.gms l. 81, 229, 1276, 1427-1428, 1705; supply/simu_supply.gms l. 18, 217-221;
    capmod/report_supply_model.gms l. 126-128, 302; arm/simu_market.gms l. 22, 122-124, 283-301): "*** CAPRI run
    started", "*** Data preparation", "*** CAPRI enters simulation loop Nr. 5 of 30", "*** --- Solve supply side of
    simulation loop Nr. 5", "*** --- Supply side of simulation loop Nr. 5 properly solved", "*** --- Global market model
    of simulation loop Nr. 5 solved", its number and sum of infeasibilities, "*** CAPRI went through all steps and is
    now finished";
and, per step, the step report (capmod/step_report.gms: p_iterChg, p_itemsInIters, p_timElap, p_INFES in cur_step.gdx,
shown as tables by the GUI).

Here, with the setting run.verbosity:
  quiet     warnings and the run's last line only
  capri     CAPRI's titles and run-log lines, with one line of step report per iteration (the default)
  detailed  also the model's own timed lines (each stage, the inner balances, the regions not solved to optimality,
            the Hessian's progress)
  solver    also each solve, as CAPRI's GUI shows GAMS's output while a task runs (gui2014.pdf, "Interaction with
            GAMS": GAMS's log piped into the GUI's window, its title lines into the title bar): per regional supply
            model its size, IPOPT's own iteration log (run.solver_log_print_level) and status, in region order after the
            supply side (the regions solve in parallel); per market solve each iteration's largest residual; per manure
            pool market its QP's size and status
  debug     also the model's verbose prints (CAPRIModel.verbose)
Beyond CAPRI (the project lead's choice of 11 November 2026): the same lines written to a file (run.log_file), and the
step report as CSV per iteration (run.step_report: <stem>_steps.csv, one row per iteration with its times and stop
tests; <stem>_iterchg.csv, every item's change between iterations as CAPRI's p_iterChg, with its sign). Each title
line also carries the wall-clock time.

A log line never stops a run: a failure to write the file or the CSV is reported once as a warning.
"""
from __future__ import annotations

import csv
import time
import warnings
from pathlib import Path
from typing import Dict, Iterable, List, Optional

#: run.verbosity's levels, in order
LEVELS = ["quiet", "capri", "detailed", "solver", "debug"]
#: the program name in the title lines (CAPRI's %PGMNAME%)
PROGRAM = "CAPRI-MOD"

STEP_FIELDS = ["run", "iteration", "t_supply_s", "t_between_s", "t_market_s", "t_stop_tests_s", "t_iteration_s",
               "t_since_start_s", "capri_max_change_pct", "capri_rows_above", "capri_go_on", "supply_regions",
               "supply_not_optimal", "market_converged", "market_iterations", "market_products_above_tol",
               "market_max_rel_residual", "market_max_residual_item", "nbal_price_update", "manure_pools",
               "young_animals", "base_calibration", "stop"]
ITERCHG_FIELDS = ["run", "iteration", "kind", "region", "item", "change_pct"]


class RunLog:
    """One run's log (see the module's docstring)."""

    def __init__(self, level: str = "capri", file: Optional[str] = None, step_report: Optional[str] = None,
                 t0: Optional[float] = None):
        if level not in LEVELS:
            raise ValueError(f"run.verbosity {level!r}: one of {LEVELS}")
        self.level = LEVELS.index(level)
        self.t0 = time.time() if t0 is None else t0
        self.t_last = self.t0
        self.last_title = ""
        self.file = Path(file) if file else None
        self.step_stem = Path(step_report) if step_report else None
        self._failed = set()
        self._started = set()
        if self.file:
            self._try("log file", lambda: (self.file.parent.mkdir(parents=True, exist_ok=True),
                                           self.file.write_text("")))

    # --- levels
    def at(self, name: str) -> bool:
        return self.level >= LEVELS.index(name)

    # --- writing
    def _try(self, what, fn):
        try:
            fn()
        except OSError as exc:
            if what not in self._failed:
                self._failed.add(what)
                warnings.warn(f"run log: the {what} could not be written ({exc!r}); the run goes on", RuntimeWarning,
                              stacklevel=3)

    def _emit(self, line: str) -> None:
        print(line, flush=True)
        if self.file:
            def w():
                with open(self.file, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            self._try("log file", w)

    def title(self, text: str, level: str = "capri") -> None:
        """util/title.gms: the section, the previous one, the seconds since it and the minutes since the start."""
        if not self.at(level):
            return
        now = time.time()
        last = f"  Last: {self.last_title}" if self.last_title else ""
        self._emit(f"[{time.strftime('%H:%M:%S')}] title {PROGRAM}: {text}{last} - ({now - self.t_last:6.0f} sec. "
                   f"{(now - self.t0) / 60:6.2f} min. )")
        self.t_last, self.last_title = now, text

    def log(self, text: str, level: str = "capri") -> None:
        """A caplog line: "*** text"."""
        if self.at(level):
            self._emit(f"*** {text}")

    def sub(self, text: str, level: str = "capri") -> None:
        """A caplog line of a step: "*** --- text"."""
        if self.at(level):
            self._emit(f"*** --- {text}")

    def detail(self, text: str) -> None:
        """The model's own timed line (level detailed): wall clock and time since the start."""
        if self.at("detailed"):
            el = int(time.time() - self.t0)
            self._emit(f"[{time.strftime('%H:%M:%S')} +{el // 3600}:{el % 3600 // 60:02d}:{el % 60:02d}] {text}")

    def solver(self, text: str) -> None:
        """A solver's line (level solver), as GAMS writes it to its log."""
        if self.at("solver"):
            self._emit(text)

    def supply_solves(self, supply_results: Dict) -> None:
        """Each regional model's solves (level solver), as GAMS's log shows a solve: generation, the solver's own log,
        its status. The regions solve in parallel; their logs are written in region order once all have solved."""
        for r in sorted(supply_results or {}):
            logs = getattr(supply_results[r], "solver_log", None) or []
            if logs:
                # written here, not kept with the results
                supply_results[r].solver_log = []
            if not self.at("solver"):
                continue
            for s in logs:
                self._emit(f"--- Generating NLP model supply {r} ({s.get('start', '')} start): {s.get('n_x', 0):,} "
                           f"variables, {s.get('n_g', 0):,} constraints")
                self._emit(f"--- Executing IPOPT ({s.get('linear_solver', '')})")
                for ln in str(s.get("log", "")).rstrip().splitlines():
                    self._emit(ln)
                self._emit(f"--- {r}: {s.get('status', '')}, {s.get('iterations', 0)} iterations, "
                           f"{float(s.get('seconds', 0.0)):.2f} s")

    def always(self, text: str) -> None:
        """A line written at every level, quiet included (the run's last line)."""
        self._emit(text)

    def since_start(self) -> float:
        return time.time() - self.t0

    # --- the simulation loop's lines (capmod.gms l. 1425-1428, supply/simu_supply.gms, arm/simu_market.gms)
    def loop_start(self, n: int, n_max: int, label: str, year=None) -> None:
        self.title(f"Working for {label}{f', year {year}' if year else ''}, iteration number {n}")
        self.log(f"{PROGRAM} enters simulation loop Nr. {n} of at most {n_max}")
        self.log(f"Since {PROGRAM} has been started, {self.since_start():.0f} seconds have passed")
        self.sub(f"Solve supply side of simulation loop Nr. {n}")

    def supply_solved(self, n: int, supply_results: Dict) -> Dict:
        """The supply side's line (capmod/report_supply_model.gms l. 126-128, 302). CAPRI aborts when a supply model
        is not solved; this model keeps IPOPT's last point (supply_module, a departure) and names the regions."""
        res = supply_results or {}
        self.supply_solves(res)
        bad = sorted(r for r, x in res.items() if not bool(getattr(x, "converged", True)))
        if not bad:
            self.sub(f"Supply side of simulation loop Nr. {n} properly solved ({len(res)} regional models)")
        else:
            show = bad if self.at("detailed") else bad[:5]
            more = f" and {len(bad) - len(show)} more" if len(bad) > len(show) else ""
            self.sub(f"Supply side of simulation loop Nr. {n}: {len(res) - len(bad)} of {len(res)} regional models "
                     f"optimal; IPOPT's last point kept in {', '.join(show)}{more}")
            if self.at("detailed"):
                for r in bad:
                    self.detail(f"  {r}: {str(getattr(res[r], 'solver_message', '') or '').split(': ', 1)[-1]}")
        return {"supply_regions": len(res), "supply_not_optimal": len(bad)}

    def market_solved(self, n: int, market_eq, market=None, tol: Optional[float] = None) -> Dict:
        """The market's lines (arm/simu_market.gms l. 22, 283-285). CAPRI reports its solver's number and sum of
        infeasibilities; this market's counterpart is its balance residuals, the largest relative residual of each
        product's equations at the solution (market._bilat_errs; its stop test: every one below market.tol): the
        number of products above the tolerance and the largest, with its region."""
        self.sub(f"Solve global market model of simulation loop Nr. {n}", level="detailed")
        conv = bool(getattr(market_eq, "converged", True))
        it = int(getattr(market_eq, "iterations", 0) or 0)
        errs = dict(getattr(market, "_bilat_errs", None) or {})
        worst = getattr(market, "_bilat_worst", None)
        mx = max(errs.values()) if errs else None
        item = max(errs, key=errs.get) if errs else ""
        above = sum(1 for v in errs.values() if tol is not None and v >= tol)
        self.sub(f"Global market model of simulation loop Nr. {n} " + ("solved" if conv else
                 "not solved to its tolerance: its last point kept") + (f" ({it} iterations)" if it else ""))
        if mx is not None:
            where = f" in {worst[1]}" if worst and worst[0] == item else ""
            self.sub(f"Nr of products with balance residuals above the tolerance{f' {tol:g}' if tol else ''}: {above}; "
                     f"largest relative residual {mx:.3g} ({item}{where})")
        return {"market_converged": conv, "market_iterations": it, "market_products_above_tol": above,
                "market_max_rel_residual": mx if mx is not None else "", "market_max_residual_item": item}

    def step_report(self, n: int, label: str, verdict: Optional[Dict], times: Dict, extra: Dict,
                    min_iter_chg: Optional[float], signed: Optional[Dict]) -> None:
        """One line of step report (capmod/step_report.gms's p_iterChg, p_timElap) and the CSV rows."""
        if verdict and verdict.get("step") == 1:
            self.sub(f"Step report Nr. {n}: the first step, nothing to compare with -> CAPRI goes on")
        elif verdict:
            top = ", ".join(f"{r} {w} {v:.3f}%" for r, w, v in verdict.get("top", [])[:3])
            lim = f" above {min_iter_chg:g}%" if min_iter_chg is not None else ""
            self.sub(f"Step report Nr. {n}: {verdict['count']} row(s){lim}, largest changes {top or '-'}"
                     + (" -> CAPRI goes on" if verdict.get("go_on") else " -> CAPRI's stop rule met"))
        self.sub(f"Times of loop Nr. {n}: supply {times['t_supply_s']:.0f} s, market {times['t_market_s']:.0f} s, "
                 f"other {times['t_between_s'] + times['t_stop_tests_s']:.0f} s, loop {times['t_iteration_s']:.0f} s")
        row = {"run": label, "iteration": n, **{k: round(v, 3) for k, v in times.items()},
               "t_since_start_s": round(self.since_start(), 1), **extra}
        if verdict:
            row.update(capri_max_change_pct=verdict["max"], capri_rows_above=verdict["count"],
                       capri_go_on=verdict["go_on"])
        self.step(row)
        if signed:
            self.iterchg({"run": label, "iteration": n, "kind": k, "region": who, "item": r, "change_pct": v}
                         for (k, who, r), v in signed.items())

    # --- the step report as CSV
    def _append(self, suffix: str, fields: List[str], rows: Iterable[Dict]) -> None:
        if not self.step_stem:
            return
        path = self.step_stem.with_name(self.step_stem.name + suffix)

        def w():
            new = suffix not in self._started
            self._started.add(suffix)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w" if new else "a", newline="", encoding="utf-8") as fh:
                wr = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
                if new:
                    wr.writeheader()
                for r in rows:
                    wr.writerow({k: r.get(k, "") for k in fields})
        self._try(f"step report {path.name}", w)

    def step(self, row: Dict) -> None:
        """One iteration's row of <stem>_steps.csv."""
        self._append("_steps.csv", STEP_FIELDS, [row])

    def iterchg(self, rows: Iterable[Dict]) -> None:
        """One iteration's item changes, rows of <stem>_iterchg.csv."""
        self._append("_iterchg.csv", ITERCHG_FIELDS, rows)


_current: Optional[RunLog] = None


def configure(level: Optional[str] = None, file: Optional[str] = None, step_report: Optional[str] = None,
              t0: Optional[float] = None) -> RunLog:
    """The run's log, from the arguments, else the settings run.verbosity, run.log_file, run.step_report."""
    global _current
    from capri_mod.settings import current as _settings
    st = _settings()
    _current = RunLog(level=str(st.get("run.verbosity")) if level is None else level,
                      file=(str(st.get("run.log_file") or "") or None) if file is None else file,
                      step_report=(str(st.get("run.step_report") or "") or None) if step_report is None
                      else step_report, t0=t0)
    return _current


def solver_log_size(path: str) -> int:
    """The size of a solver's log file (run.verbosity "solver"): where the next solve's log starts."""
    p = Path(path)
    return p.stat().st_size if p.exists() else 0


def read_solver_log(path: str, start: int) -> str:
    """A solver's log from byte start on (one solve's: IPOPT appends each solve of a solver object to its file)."""
    try:
        with open(path, "rb") as fh:
            fh.seek(start)
            return fh.read().decode("utf-8", errors="replace")
    except OSError as exc:
        return f"(the solver's log not read: {exc!r})"


def current() -> RunLog:
    """The run's log (configured from the settings on first use)."""
    return _current if _current is not None else configure()
