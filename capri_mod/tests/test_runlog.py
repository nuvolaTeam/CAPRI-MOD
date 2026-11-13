"""The run's log (capri_mod/runlog.py): CAPRI's title and run-log lines by verbosity, the file and the step report
CSV."""
from __future__ import annotations

import csv
from types import SimpleNamespace

import pytest

from capri_mod import runlog as RL


def test_levels_file_and_step_report(tmp_path, capsys):
    rl = RL.RunLog(level="capri", file=str(tmp_path / "run.log"), step_report=str(tmp_path / "run"), t0=0.0)
    rl.title("Set policy parameters")
    rl.title("Prepare for market model")
    rl.log("CAPRI-MOD run started")
    rl.detail("not shown at capri")
    res = {"R1": SimpleNamespace(converged=True),
           "R2": SimpleNamespace(converged=False, solver_message="x: Maximum_Iterations_Exceeded")}
    ex = rl.supply_solved(3, res)
    mk = SimpleNamespace(_bilat_errs={"WHEA": 2e-8, "MILK": 5e-7}, _bilat_worst=("MILK", "EU_WEST", 1.0, 2.0, 3.0))
    ex.update(rl.market_solved(3, SimpleNamespace(converged=True, iterations=12), mk, 1e-7))
    rl.step_report(3, "f2f", {"step": 3, "max": 0.3, "count": 4, "go_on": True, "top": [("WHEA", "DE000000", 0.3)]},
                   {"t_supply_s": 10.0, "t_between_s": 1.0, "t_market_s": 5.0, "t_stop_tests_s": 0.5,
                    "t_iteration_s": 16.5}, ex, 0.05, {("prod", "DE000000", "WHEA"): -0.3})
    out = capsys.readouterr().out
    lines = (tmp_path / "run.log").read_text().splitlines()
    assert lines == out.splitlines()                                        # the file holds the screen's lines
    assert lines[1].split("] ", 1)[1].startswith(
        "title CAPRI-MOD: Prepare for market model  Last: Set policy parameters - (")
    assert "*** CAPRI-MOD run started" in lines and not any("not shown" in x for x in lines)
    assert ("*** --- Supply side of simulation loop Nr. 3: 1 of 2 regional models optimal; IPOPT's last point kept "
            "in R2") in lines
    assert any("above the tolerance 1e-07: 1; largest relative residual 5e-07 (MILK in EU_WEST)" in x for x in lines)
    assert any(x.startswith("*** --- Step report Nr. 3: 4 row(s) above 0.05%, largest changes WHEA DE000000 0.300%")
               for x in lines)
    st = list(csv.DictReader(open(tmp_path / "run_steps.csv")))
    assert len(st) == 1 and st[0]["supply_not_optimal"] == "1" and st[0]["market_products_above_tol"] == "1"
    ic = list(csv.DictReader(open(tmp_path / "run_iterchg.csv")))
    assert ic == [{"run": "f2f", "iteration": "3", "kind": "prod", "region": "DE000000", "item": "WHEA",
                   "change_pct": "-0.3"}]


def test_quiet_and_detailed(tmp_path, capsys):
    q = RL.RunLog(level="quiet")
    q.title("x")
    q.log("y")
    q.always("last")
    assert capsys.readouterr().out == "last\n"
    d = RL.RunLog(level="detailed", t0=0.0)
    d.detail("timed")
    assert capsys.readouterr().out.rstrip().endswith("] timed")
    with pytest.raises(ValueError):
        RL.RunLog(level="loud")


def test_solver_level_writes_each_solve_and_drops_the_logs(capsys):
    """run.verbosity "solver": each regional solve as GAMS's log shows it (size, IPOPT's own log, status), in region
    order; the logs are not kept with the results; below the level nothing is written and the logs are dropped too."""
    log = {"log": "iter    objective\n   0  1.0e+00\nEXIT: Optimal Solution Found.\n", "n_x": 505, "n_g": 366,
           "seconds": 0.25, "status": "Solve_Succeeded", "iterations": 38, "start": "cold", "linear_solver": "mumps"}
    res = {"R2": SimpleNamespace(converged=True, solver_log=[dict(log)]),
           "R1": SimpleNamespace(converged=True, solver_log=[dict(log, start="warm")])}
    RL.RunLog(level="solver", t0=0.0).supply_solved(1, res)
    out = capsys.readouterr().out.splitlines()
    gen = [x for x in out if x.startswith("--- Generating NLP model supply")]
    assert gen == ["--- Generating NLP model supply R1 (warm start): 505 variables, 366 constraints",
                   "--- Generating NLP model supply R2 (cold start): 505 variables, 366 constraints"]
    assert "EXIT: Optimal Solution Found." in out and "--- R1: Solve_Succeeded, 38 iterations, 0.25 s" in out
    assert all(v.solver_log == [] for v in res.values())
    res = {"R1": SimpleNamespace(converged=True, solver_log=[dict(log)])}
    RL.RunLog(level="capri", t0=0.0).supply_solved(1, res)
    assert not any(x.startswith("--- ") for x in capsys.readouterr().out.splitlines()) and res["R1"].solver_log == []
