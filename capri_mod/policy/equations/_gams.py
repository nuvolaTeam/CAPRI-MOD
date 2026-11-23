"""GAMS's special values and conditions as CAPRI's premium code relies on them, shared by the policy's statement
functions (this package) and their callers: EPS and NA as values, a $-condition on a value, "gt eps" and GAMS's sum
of values that may be EPS. Not CAPRI statements: GAMS's semantics (moved here from capri_mod/policy/premium_cut.py,
declared.py and mtr.py in the refactor's block A2, which import them from here)."""
from __future__ import annotations

#: CAPRI's EPS as a value (a ceiling written EPS: the scheme pays nothing in the region)
EPS = "EPS"
#: GAMS's NA in p_premDataE (agenda.gms l. 1225: "treated as a missing value" by policy.gms l. 25)
NA = "NA"


def nonzero(x) -> bool:
    """A GAMS $-condition on a value: true for EPS and any number but zero."""
    return x == EPS or (x is not None and x != 0)


def above_eps(x) -> bool:
    """GAMS's "x gt eps": a positive number (EPS and zero are not)."""
    return x is not None and x != EPS and x > 0


def gams_sum(values):
    """GAMS's sum of values that may be EPS: the sum of the numbers; EPS where the terms are EPS and zeros only; None
    (no record) for no term or a zero sum."""
    total, eps = 0.0, False
    for v in values:
        if v == EPS:
            eps = True
        elif v:
            total += v
    if total != 0.0:
        return total
    return EPS if eps else None


def as_number(v) -> float:
    """A value in GAMS arithmetic: EPS 0, no record 0 (NA, which propagates, does not reach the rules that compute)."""
    if v is None or v == EPS:
        return 0.0
    if v == NA:
        raise ValueError("mtr: NA in arithmetic")
    return float(v)
