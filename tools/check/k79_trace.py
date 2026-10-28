"""K79: which regions and activities keep moving between outer iterations (a run with
diagnostics.record_regional_levels = true; tools/run/run_f2f_2030.py stores outer_history).

Per member state and activity, the level summed over the member state's regions at each scenario iteration, its
change against the previous iteration in CAPRI's measure (2 |x1 - x0| / (x1 + x0) x 100, capri_mod/utils/capri_stop.py)
and in level; flagged where the change exceeds 0.05% and 0.5 (CAPRI's p_minIterChg and p_minAbsProdIterChg; here
on activity levels, 1000 ha or 1000 head, not on the products in kt that CAPRI's rule reads). For each flagged pair:
the pattern of the last iterations' changes (alternating: signs flip every iteration; drift: one sign; mixed), and the
regions behind the largest moves. Also CAPRI's verdict per iteration as the run recorded it.

    python tools/check/k79_trace.py RUN.pkl [--last 8] [--top 25] [--csv OUT.csv]
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from capri_mod.data.definitions import capri_ms  # noqa: E402

MIN_CHG, MIN_ABS = 0.05, 0.5


def chg(x1, x0):
    s = np.abs(x1 + x0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(s > 0, 200.0 * np.abs(x1 - x0) / s, 0.0)


def pattern(d):
    """d: the level changes of the last iterations (non-zero ones)."""
    s = np.sign(d[np.abs(d) > 0])
    if len(s) < 3:
        return "short"
    flips = int(np.sum(s[1:] != s[:-1]))
    if flips == len(s) - 1:
        return "alternating"
    if flips == 0:
        return "drift"
    return f"mixed ({flips} sign changes in {len(s) - 1})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--last", type=int, default=8, help="iterations for the pattern")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--csv", default="")
    a = ap.parse_args()
    d = pickle.load(open(a.run, "rb"))
    hist = d["outer_history"][1] if isinstance(d["outer_history"], (tuple, list)) and len(d["outer_history"]) == 2 \
        else d["outer_history"]
    print("CAPRI's verdict per scenario iteration (max %, rows above 0.05%, largest rows):")
    for e in hist:
        c = (e.get("conv") or {}).get("capri") or {}
        print(f"  {e.get('it')}: max {c.get('max', float('nan')):.3f} count {c.get('count')} "
              f"{'go on' if c.get('go_on') else 'stop'} | {c.get('top')}")
    its = [e for e in hist if e.get("act_regional")]
    if len(its) < 3:
        sys.exit("no act_regional in the outer history (diagnostics.record_regional_levels)")
    # levels: iteration x (region, activity)
    lv = pd.DataFrame({e["it"]: pd.Series({(r, act): v for r, acts in e["act_regional"].items()
                                           for act, v in acts.items()}) for e in its}).fillna(0.0)
    lv.index = pd.MultiIndex.from_tuples(lv.index, names=["region", "act"])
    ms = lv.groupby([lv.index.get_level_values("region").map(capri_ms), lv.index.get_level_values("act")]).sum()
    ms.index.names = ["ms", "act"]
    it = list(lv.columns)
    dl = ms.diff(axis=1).iloc[:, 1:]
    rc = pd.DataFrame(chg(ms.iloc[:, 1:].to_numpy(), ms.iloc[:, :-1].to_numpy()), index=ms.index, columns=it[1:])
    flag = (rc > MIN_CHG) & (dl.abs() > MIN_ABS)
    print(f"\nmember state x activity pairs above {MIN_CHG}% and {MIN_ABS} per iteration:")
    print("  " + ", ".join(f"{c}: {int(flag[c].sum())}" for c in flag.columns))
    last = it[-a.last:]
    lastc = [c for c in last if c in rc.columns]
    score = rc[lastc].where(dl[lastc].abs() > MIN_ABS, 0.0).max(axis=1).sort_values(ascending=False)
    rows = []
    lvr = lv.diff(axis=1).iloc[:, 1:]
    for (m, act), sc in score.head(a.top).items():
        if sc <= MIN_CHG:
            break
        dd = dl.loc[(m, act), lastc].to_numpy()
        sub = lvr.loc[[i for i in lvr.index if capri_ms(i[0]) == m and i[1] == act], lastc]
        drivers = sub.abs().max(axis=1).sort_values(ascending=False).head(3)
        rows.append({"ms": m, "act": act, "level": float(ms.loc[(m, act), it[-1]]), "max_chg_pct": float(sc),
                     "pattern": pattern(dd), "changes": " ".join(f"{x:+.2f}" for x in dd),
                     "regions": "; ".join(f"{r} {sub.loc[(r, act)].abs().max():.2f}" for (r, _), _v in drivers.items())})
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 90)
    print(f"\nlargest movers over the last {len(lastc)} iterations:")
    print(out.to_string(index=False))
    if a.csv:
        out.to_csv(a.csv, index=False)


if __name__ == "__main__":
    main()
