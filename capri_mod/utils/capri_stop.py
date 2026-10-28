"""CAPRI's stop rule for the supply-market iterations (capmod/price_forecast.gms l. 96-371; thresholds capmod.gms
l. 384-388; the loop's condition capmod.gms l. 1369).

Per iteration ("step") CAPRI computes p_iterChg, the relative change (in %) of each item against the previous step,
2 |x_t - x_t-1| / (x_t + x_t-1) x 100:

- prices (IOE), at the trade aggregates REGAGGU (EU_West, EU_East, ...): the members' prices weighted by their first
  step's production, over members producing more than 10 x p_minAbsProdIterChg; counted where the aggregate
  produces more than that and the price moved by more than p_minAbsPriceIterChg (EUR 0.05) (l. 76-125);
- production of the final outputs (OM_OUTPUT) per member state, where it moved by more than p_minAbsProdIterChg
  (0.5 kt) (l. 127-141);
- feed use per member state (FEED, without straw and fodder), where it moved by more than p_minAbsFeedIterChg
  (2.5 kt) (l. 143-159);
- Norway (NO000000) out from the 15th step (l. 317).

Per row the change is the largest over member states and aggregates; the step's maximum leaves out the young
animals (OIYANI) and manure (l. 328-346); the first step counts at least 1% (l. 363). The loop goes on while the
maximum exceeds p_minIterChg (0.05%) and more than two rows exceed it (l. 366-371, 1369).

What this module needs from the caller, per step: production (kt) and feed use (kt) per member state and row, and the
market's prices per member state and row (EUR/t; CAPRI's p_itemsInIters "UVAG" is the market's solution of the step,
before the price forecast's averaging), and the aggregates' members. Differences from CAPRI's items are the caller's
and are listed where it builds them (model.CAPRIModel._capri_stop_step).

Not CAPRI's: CapriStopRule.drift, a report of the items still moving one way when the loop ends
(outer_loop.drift_report_steps); it decides nothing."""
from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Set

Table = Mapping[str, Mapping[str, float]]          # {member state or aggregate: {row: value}}


def _chg(x1: float, x0: float) -> float:
    s = abs(x1 + x0)
    return 200.0 * abs(x1 - x0) / s if s > 0 else 0.0


def _schg(x1: float, x0: float) -> float:
    """_chg with the sign of x1 - x0 (for the drift report)."""
    s = abs(x1 + x0)
    return 200.0 * (x1 - x0) / s if s > 0 else 0.0


class CapriStopRule:
    """CAPRI's p_iterChg and its stop decision, step by step."""

    def __init__(self, aggregates: Mapping[str, Iterable[str]], yani_rows: Iterable[str] = (),
                 no_abs_price_rows: Iterable[str] = (), min_abs_prod: float = 0.5, min_abs_feed: float = 2.5, min_abs_price: float = 0.05,
                 min_iter_chg: float = 0.05, norway: str = "NO000000", norway_last_step: int = 15):
        self.aggregates = {a: list(ms) for a, ms in aggregates.items()}
        self.yani_rows: Set[str] = set(yani_rows)
        # rows whose prices are given as ratios to base (no price level at hand): p_minAbsPriceIterChg not applied
        self.no_abs_price_rows: Set[str] = set(no_abs_price_rows)
        self.min_abs_prod, self.min_abs_feed = float(min_abs_prod), float(min_abs_feed)
        self.min_abs_price, self.min_iter_chg = float(min_abs_price), float(min_iter_chg)
        self.norway, self.norway_last_step = norway, int(norway_last_step)
        self.steps: List[dict] = []

    def _agg_prices(self, price: Table, prod: Table, prod1: Table) -> Dict[str, Dict[str, float]]:
        """CAPRI l. 76-91: the aggregate's price, its members' prices weighted by their first step's production,
        members with production now and more than 10 x p_minAbsProdIterChg in the first step."""
        out = {}
        for a, mss in self.aggregates.items():
            rows = {r for ms in mss for r in (price.get(ms) or {})}
            d = {}
            for r in rows:
                if r in self.no_abs_price_rows:
                    # a common ratio across the members (the young animals' market ratios): their mean
                    vals = [float((price.get(ms) or {})[r]) for ms in mss if (price.get(ms) or {}).get(r) is not None]
                    if vals:
                        d[r] = sum(vals) / len(vals)
                    continue
                w = [(float((prod1.get(ms) or {}).get(r, 0.0)), float((price.get(ms) or {}).get(r, 0.0))) for ms in mss
                     if float((prod.get(ms) or {}).get(r, 0.0)) and float((prod1.get(ms) or {}).get(r, 0.0)) > 10 * self.min_abs_prod
                     and (price.get(ms) or {}).get(r) is not None]
                sw = sum(x for x, _ in w)
                if sw > 0:
                    d[r] = sum(x * p for x, p in w) / sw
            out[a] = d
        return out

    def record(self, prod: Table, feed: Table, price: Table) -> dict:
        """One step: production and feed (kt) and prices (EUR/t) per member state and row. Returns the step's
        verdict: {"max": the step's maximum change (%), "cur": CAPRI's p_iterChg("TOT","MAX","CUR"), "count": rows
        above p_minIterChg, "go_on": whether CAPRI iterates again, "rows": {row: largest change}, "top": the largest}."""
        k = len(self.steps) + 1
        prod1 = self.steps[0]["prod"] if self.steps else prod
        aggp = self._agg_prices(price, prod, prod1)
        rec = {"prod": {m: dict(v) for m, v in prod.items()}, "feed": {m: dict(v) for m, v in feed.items()},
               "aggp": aggp}
        chg: Dict[str, Dict[str, float]] = {}
        # the same changes with their sign, per item (kind, member state or aggregate, row): the drift report
        sgn: Dict[tuple, float] = {}
        if self.steps:
            prev = self.steps[-1]
            # prices at the aggregates (l. 103-125)
            for a, d in aggp.items():
                d0 = prev["aggp"].get(a, {})
                gprod = {r: sum(float((prod.get(ms) or {}).get(r, 0.0)) for ms in self.aggregates[a]) for r in d}
                for r, p in d.items():
                    p0 = d0.get(r)
                    if r in self.no_abs_price_rows:
                        if p and p0:
                            chg.setdefault(a, {})[r] = _chg(p, p0)
                            sgn[("price", a, r)] = _schg(p, p0)
                    elif p and p0 and gprod.get(r, 0.0) > 10 * self.min_abs_prod and abs(p - p0) > self.min_abs_price:
                        chg.setdefault(a, {})[r] = _chg(p, p0)
                        sgn[("price", a, r)] = _schg(p, p0)
            # production per member state (l. 127-141)
            for ms, d in prod.items():
                d0 = prev["prod"].get(ms, {})
                for r, x in d.items():
                    x0 = float(d0.get(r, 0.0))
                    if x and x0 and abs(x - x0) > self.min_abs_prod:
                        c = chg.setdefault(ms, {})
                        c[r] = max(c.get(r, 0.0), _chg(x, x0))
                        sgn[("prod", ms, r)] = _schg(x, x0)
            # feed per member state (l. 143-159)
            for ms, d in feed.items():
                d0 = prev["feed"].get(ms, {})
                for r, x in d.items():
                    x0 = float(d0.get(r, 0.0))
                    if x and x0 and abs(x - x0) > self.min_abs_feed:
                        c = chg.setdefault(ms, {})
                        c[r] = max(c.get(r, 0.0), _chg(x, x0))
                        sgn[("feed", ms, r)] = _schg(x, x0)
            # Norway out from the 15th step (l. 317)
            if k >= self.norway_last_step:
                chg.pop(self.norway, None)
                sgn = {key: v for key, v in sgn.items() if key[1] != self.norway}
        rec["signed"] = sgn
        # per row: the largest over member states and aggregates (l. 321, 354-355)
        rows: Dict[str, float] = {}
        for _who, d in chg.items():
            for r, v in d.items():
                rows[r] = max(rows.get(r, 0.0), v)
        mx = max((v for r, v in rows.items() if r not in self.yani_rows), default=0.0)
        if k == 1:
            mx = max(1.0, mx)                                  # l. 363
        count = sum(1 for v in rows.values() if v > self.min_iter_chg)
        cur = mx if (k == 1 or count > 2) else 0.0             # l. 366-371 (the first step always goes on)
        top = sorted(((v, r, w) for w, d in chg.items() for r, v in d.items() if r not in self.yani_rows),
                     reverse=True)[:5]
        verdict = {"step": k, "max": mx, "cur": cur, "count": count, "go_on": cur > self.min_iter_chg,
                   "rows": rows, "top": [(r, w, round(v, 4)) for v, r, w in top]}
        rec["verdict"] = verdict
        self.steps.append(rec)
        return verdict

    def drift(self, n: int = 3) -> List[dict]:
        """Not CAPRI's (a report, it decides nothing): the items whose last n changes all had the same sign and whose
        last change still exceeds p_minIterChg, each change having passed the rule's filters. CAPRI's rule can stop
        with up to two rows above p_minIterChg, also rows moving steadily one way (a price forecast still approaching
        its equilibrium). Per item: its last n changes (%, signed, oldest first), the rate r at which they shrink
        ((|last| / |first|) ** (1 / (n - 1))) and, where r < 1, a rough estimate of the movement still to come in the
        same measure, |last| r / (1 - r) (a geometric tail; None where the changes do not shrink). Young-animal rows
        are left out as from the step's maximum. Sorted by the last change, largest first."""
        n = int(n)
        if n < 2 or len(self.steps) < n + 1:
            return []
        last = [s.get("signed") or {} for s in self.steps[-n:]]
        out = []
        for key, v in last[-1].items():
            if key[2] in self.yani_rows or abs(v) <= self.min_iter_chg:
                continue
            ch = [d.get(key) for d in last]
            if any(c is None or c == 0.0 for c in ch) or len({c > 0 for c in ch}) != 1:
                continue
            r = (abs(ch[-1]) / abs(ch[0])) ** (1.0 / (n - 1))
            out.append({"kind": key[0], "where": key[1], "row": key[2], "changes": [round(c, 4) for c in ch],
                        "rate": round(r, 4), "to_come": (round(abs(ch[-1]) * r / (1.0 - r), 4) if r < 1.0 else None)})
        return sorted(out, key=lambda e: -abs(e["changes"][-1]))
