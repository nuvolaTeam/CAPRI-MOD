"""CAPRI's premium cut during a scenario's iterations (capmod/calculate_premiums.gms; P2): at each step up to the
tenth, prmcut.gms on the weighted average of the last steps' activity levels (capmod/define_stepWeights.gms), the
premiums so computed used in the next step's supply solve; after the tenth step they stay.

The model keeps its premium per activity (cap_premium for crops, livestock_premium_coef for animals); this module
gives each a factor, the ported premiums at the step's levels over the same premiums at CAPRI's trend levels:

    factor(r, a) = sum over a's CAPRI activities m of s_m x PRME_it(r, m) / sum of s_m x PRME_0(r, m)

with s_m the CAPRI activity's share of the model activity's trend level (model_activities.csv: DCOW is DCOL + DCOH,
...), PRME_0 prmcut at the trend levels (CAPRI's baseline premium, the model's reference) and PRME_it prmcut at the
step's levels. A CAPRI activity's level at a step is its trend level times its model activity's level over the
model's own baseline level (DEP-48): the model's baseline is its own projection, not CAPRI's trend, and its
baseline premiums are CAPRI's at CAPRI's trend levels, so the factors are 1 at the model's baseline and the cut
responds to the scenario's change; the levels' units (the model's stalls against CAPRI's produced heads, poultry in
thousands against millions) cancel. Where the model splits an animal into CAPRI's activities itself (the dairy cows'
DCOL / DCOH, Sprint 7b; the bulls' and heifers' intensity pairs, Sprint 7c; the replacement heifers and calves with
supply.use_cattle_member_splits, K65), the change is the CAPRI activity's own: its stalls x_m = s_m X + sum_k E_mk z_k
(s_m its stall share, z_k the split's shift, E_mk +1 for the activity gaining the stalls, -1 for the one giving them
up; supply/livestock.py) now over the baseline's. The CAPRI activities no model activity holds (NECR, the idled
histosols), and those of a model activity without a baseline level, stay at their trend levels. Only the EU units the ported schemes
cover take factors (not Norway).
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


def model_splits(data: dict, region: str) -> dict:
    """The model's own split of its animals into CAPRI's activities in a region: {model animal: {CAPRI activity:
    (stall share, {split key: E})}} from dairy_intensity (DCOW: DCOL share_low, DCOH the rest; key "DCOW") and
    cattle_intensity (each split's member_low / member_high stall shares, codes/model_cattle_splits.csv)."""
    from capri_mod.data.definitions import CATTLE_SPLITS
    out = {}
    di = data.get("dairy_intensity")
    if di is not None and region in di.index and "share_low" in di.columns:
        s = float(di.at[region, "share_low"])
        out["DCOW"] = {"DCOL": (s, {"DCOW": 1.0}), "DCOH": (1.0 - s, {"DCOW": -1.0})}
    for key, row in ((data.get("cattle_intensity") or {}).get(region) or {}).items():
        if key not in CATTLE_SPLITS:
            continue
        a = key.split(":")[0]
        gains, gives = CATTLE_SPLITS[key]
        d = out.setdefault(a, {})
        for m, sh, e in ((gains, "share_low", 1.0), (gives, "share_high", -1.0)):
            s0, E = d.get(m, (float(row[sh]), {}))
            d[m] = (s0, {**E, key: e})
    return out


def _stalls(split: dict, x: float, z: dict) -> dict:
    """{CAPRI activity: stalls} of a model animal's level x and its splits' shifts z."""
    return {m: s * x + sum(e * float(z.get(k, 0.0) or 0.0) for k, e in E.items()) for m, (s, E) in split.items()}


def shifts(result) -> dict:
    """{split key: shift} of a regional solution (dairy_low_shift as "DCOW", cattle_shift)."""
    out = {k: float(v) for k, v in (getattr(result, "cattle_shift", None) or {}).items()}
    dz = getattr(result, "dairy_low_shift", None)
    if dz:
        out["DCOW"] = float(dz)
    return out


def _per_activity(prme: dict) -> dict:
    out = defaultdict(float)
    for (u, a, s), v in prme.items():
        if v and v != EPS:
            out[(u, a)] += v
    return out


class PremiumResponse:
    """The premium factors of a scenario's iterations, against the model's baseline levels
    {region: {model activity: level}}, the baseline's split shifts {region: {key: z}} and the model's splits
    {region: model_splits(...)}."""

    def __init__(self, year: int, base_year: int, weights, max_step: int, base_levels: dict, base_shifts=None,
                 splits=None):
        self.trend = _pm.trend_levels()
        self.units = _pm.eu_units(self.trend)
        self.yp = _pm.year_premiums(self.units, self.trend, year, base_year)
        self.prme0 = _per_activity(self.yp.cut(self.trend))
        self.weights = tuple(float(w) for w in weights)
        self.max_step = int(max_step)
        self.members = _members()
        units = set(self.units)
        self.base = {r: {a: float(x) for a, x in acts.items()} for r, acts in (base_levels or {}).items()
                     if r in units}
        self.splits = {r: v for r, v in (splits or {}).items() if v}
        self.base_stalls = {}
        for r, sp in self.splits.items():
            for a, split in sp.items():
                x0 = self.base.get(r, {}).get(a, 0.0)
                if x0 > 0:
                    self.base_stalls[(r, a)] = _stalls(split, x0, (base_shifts or {}).get(r, {}))
        self.share = {}
        for ma, ms_ in self.members.items():
            for u in units:
                tot = sum(self.trend.get((u, m), 0.0) for m in ms_)
                if tot > 0:
                    self.share[(u, ma)] = {m: self.trend.get((u, m), 0.0) / tot for m in ms_}
        self.regions = set()
        self.history = []

    def record(self, step: int, activity_levels: dict, step_shifts=None):
        """The step's (1-based) model levels {region: {model activity: level}} and split shifts {region: {key: z}}
        after its supply solve."""
        lev = dict(self.trend)
        for r, acts in activity_levels.items():
            b = self.base.get(r)
            if b is None:
                continue
            self.regions.add(r)
            for ma, x in acts.items():
                x0 = b.get(ma, 0.0)
                if x0 <= 0:
                    continue
                own = {}
                if (r, ma) in self.base_stalls:
                    now = _stalls(self.splits[r][ma], float(x), (step_shifts or {}).get(r, {}))
                    own = {m: now[m] / v for m, v in self.base_stalls[(r, ma)].items() if v > 0}
                for m in self.members.get(ma, ()):
                    if (r, m) in self.trend:
                        lev[(r, m)] = self.trend[(r, m)] * max(own.get(m, float(x) / x0), 0.0)
        self.history.append((step, lev))
        self.history = self.history[-len(self.weights):]

    def factors(self, step: int) -> dict:
        """{region: {model activity: factor}} of the recorded regions for the step after `step`, computed when `step`
        <= max_step (CAPRI's "step.pos le 10"); None afterwards (the factors of the tenth step stay)."""
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
            if u not in self.regions:
                continue
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
