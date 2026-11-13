"""CAPRI's premium cut during a scenario's iterations (capmod/calculate_premiums.gms; P2): at each step up to the
tenth, prmcut.gms on the weighted average of the last steps' activity levels (capmod/define_stepWeights.gms), the
premiums so computed used in the next step's supply solve; after the tenth step they stay.

The model keeps its premium per activity (cap_premium for crops, livestock_premium_coef for animals); this module
gives each a factor, the ported premiums at the weighted levels over the same premiums at CAPRI's trend levels:

    factor(r, a) = sum over a's CAPRI activities m of s_m x PRME_it(r, m) / sum of s_m x PRME_0(r, m)

with s_m the CAPRI activity's share of the model activity's trend level (model_activities.csv: DCOW is DCOL + DCOH,
...), PRME_it prmcut at the weighted levels, PRME_0 prmcut at the trend levels (the baseline's premium, CAPRI's
reference). A CAPRI activity's level during the iterations is its model activity's level times s_m; the CAPRI
activities no model activity holds (NECR, the idled histosols) stay at their trend levels. Only the EU units the
ported schemes cover take factors (not Norway).
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from capri_mod.policy import premiums as _pm
from capri_mod.policy.premium_cut import EPS

ROOT = Path(__file__).resolve().parents[2]


def _members():
    """{model activity: [CAPRI activities]} (codes/model_activities.csv)."""
    with open(ROOT / "capri_data" / "codes" / "model_activities.csv", newline="") as f:
        return {r["code"]: [c for c in r["capri_codes"].split(";") if c] for r in csv.DictReader(f)}


def _per_activity(prme: dict) -> dict:
    out = defaultdict(float)
    for (u, a, s), v in prme.items():
        if v and v != EPS:
            out[(u, a)] += v
    return out


class PremiumResponse:
    """The premium factors of a scenario's iterations."""

    def __init__(self, year: int, base_year: int, weights, max_step: int):
        self.trend = _pm.trend_levels()
        self.units = _pm.eu_units(self.trend)
        self.yp = _pm.year_premiums(self.units, self.trend, year, base_year)
        self.prme0 = _per_activity(self.yp.cut(self.trend))
        self.weights = tuple(float(w) for w in weights)
        self.max_step = int(max_step)
        self.members = _members()
        units = set(self.units)
        self.share = {}
        for ma, ms_ in self.members.items():
            for u in units:
                tot = sum(self.trend.get((u, m), 0.0) for m in ms_)
                if tot > 0:
                    self.share[(u, ma)] = {m: self.trend.get((u, m), 0.0) / tot for m in ms_}
        self.history = []

    def record(self, step: int, activity_levels: dict):
        """The step's (1-based) model levels {region: {model activity: level}} after its supply solve."""
        lev = dict(self.trend)
        for r, acts in activity_levels.items():
            if r not in set(self.units):
                continue
            for ma, x in acts.items():
                sh = self.share.get((r, ma))
                if sh is None:
                    continue
                for m, s in sh.items():
                    lev[(r, m)] = float(x) * s
        self.history.append((step, lev))
        self.history = self.history[-len(self.weights):]

    def factors(self, step: int) -> dict:
        """{region: {model activity: factor}} for the step after `step`, computed when `step` <= max_step (CAPRI's
        "step.pos le 10"); None afterwards (the factors of the tenth step stay)."""
        if step > self.max_step or not self.history:
            return None
        hist = list(reversed(self.history))[:len(self.weights)]
        w = self.weights[:len(hist)]
        tot = sum(w)
        keys = set().union(*(h for _, h in hist))
        lev = {k: sum(wi * h.get(k, 0.0) for wi, (_, h) in zip(w, hist)) / tot for k in keys}
        prme = _per_activity(self.yp.cut(lev))
        out = defaultdict(dict)
        for (u, ma), sh in self.share.items():
            den = sum(s * self.prme0.get((u, m), 0.0) for m, s in sh.items())
            if den > 0:
                num = sum(s * prme.get((u, m), 0.0) for m, s in sh.items())
                out[u][ma] = num / den
        return dict(out)


def merge(base: dict, factors: dict) -> dict:
    """The scenario's own premium factors times the iteration's."""
    out = {r: dict(v) for r, v in (base or {}).items()}
    for r, acts in (factors or {}).items():
        d = out.setdefault(r, {})
        for a, f in acts.items():
            d[a] = d.get(a, 1.0) * f
    return out
