"""CAPRI's feed block of the non-EU market regions in CasADi: market programme step G2d (docs/design/
MARKET_IPOPT_DESIGN.md sections 5-6).

Written once, here, and evaluated from here by FeedMixin.noneu_fede and noneu_feed_change (capri_mod/market/feed.py):
the project lead's choice of one implementation per block (section 7, 30 October 2026). Per non-EU behavioural region s
(audit M3; CAPRI's arm/market_model.gms FeedNQ_, FeedBal_):

    FeedNQ_    feed_x = q0_x + sum_y h_xy (ra_y - 1) + h_xF (FEDE_s - 1)
    ProdNQ_    prod_a = p0_a + sum_y g_ay (rp_y - 1) + g_aM (m - 1) + sum_u l_au dr_u + g_aF (FEDE_s - 1)
    FeedBal_   sum_x kcal_x feed_x = sum_a conv_a prod_a

ra the trade region's Armington price ratios, rp its producer price ratios, m its dairy block's raw milk price ratio, dr
the land rents' changes of the region (EUR/ha; the land block). FeedBal_ is linear in FEDE, so FEDE has a closed form;
fedebal_function gives it and the balance's residual at any FEDE (the residual is G3's equation, with FEDE an unknown).
Floating point: CasADi's sums run in their own order, so the values differ from feed.py's loops before the move by
rounding only (capri_mod/tests/test_feed_ad.py measures it).
"""
from __future__ import annotations

from typing import List

import numpy as np


def fedebal_arrays(d: dict, cols: List[str], land_types: List[str]) -> dict:
    """The arrays of one behavioural region's FeedBal_ from FeedMixin._noneu_feed_params' entry d: the calories' row
    over the feeds' price terms, the conversion factors' row over the animal supply's terms."""
    ci = {c: j for j, c in enumerate(cols)}
    li = {u: j for j, u in enumerate(land_types)}
    ke = np.zeros(len(cols))            # sum_x kcal_x h_xy
    e_const = aF = 0.0
    for x, q0 in d["feed0"].items():
        k = d["kcal"].get(x, 0.0)
        if not k:
            continue                    # no calories (p_noCal): not in the balance
        e_const += k * q0
        for y, h in d["terms"].get(x, {}).items():
            if y == "FEDE":
                aF += k * h
            elif y in ci:
                ke[ci[y]] += k * h
    kn = np.zeros(len(cols))            # sum_a conv_a g_ay
    kl = np.zeros(len(land_types))
    n_const = aN = km = 0.0
    for a, cv in d["conv"].items():
        n_const += cv * d["prod0"].get(a, 0.0)
        for y, h in d["sterms"].get(a, {}).items():
            if y == "FEDE":
                aN += cv * h
            elif y == "MILK":
                km += cv * h
            elif y in ci:
                kn[ci[y]] += cv * h
        for u, h in (d.get("lterms") or {}).get(a, {}).items():
            if u in li:
                kl[li[u]] += cv * h
    return {"ke": ke, "e_const": e_const, "aF": aF, "kn": kn, "kl": kl, "km": km, "n_const": n_const, "aN": aN}


def fedebal_function(name: str, a: dict, n_cols: int, n_land: int):
    """CasADi Function (ra[n_cols], rp[n_cols], m, dr[n_land], fede) -> (fede_star, residual): the feed energy price
    ratio clearing FeedBal_ (1 where the balance has no FEDE response, aF - aN <= 0) and the balance's residual
    (energy fed - energy needed, Mcal x 1000) at fede."""
    import casadi as ca
    ra, rp = ca.SX.sym("ra", n_cols), ca.SX.sym("rp", n_cols)
    m, dr, fede = ca.SX.sym("m"), ca.SX.sym("dr", n_land), ca.SX.sym("fede")
    e0 = a["e_const"] + ca.dot(ca.DM(a["ke"]), ra - 1.0)
    n0 = a["n_const"] + ca.dot(ca.DM(a["kn"]), rp - 1.0) + a["km"] * (m - 1.0) + (ca.dot(ca.DM(a["kl"]), dr)
                                                                                   if n_land else 0)
    den = a["aF"] - a["aN"]
    star = 1.0 + (n0 - e0) / den if den > 0 else ca.SX(1.0)
    res = (e0 + a["aF"] * (fede - 1.0)) - (n0 + a["aN"] * (fede - 1.0))
    return ca.Function(name, [ra, rp, m, dr, fede], [star, res], ["ra", "rp", "m", "dr", "fede"], ["fede_star", "res"])


def feednq_arrays(d: dict, cols: List[str]) -> dict:
    """The arrays of one behavioural region's FeedNQ_ changes (the feeds with a model commodity): rows x, H (rows x
    cols), hF (rows), and the rows' model commodities."""
    ci = {c: j for j, c in enumerate(cols)}
    rows = [x for x in d["feed0"] if d["xm"].get(x)]
    H = np.zeros((len(rows), len(cols)))
    hF = np.zeros(len(rows))
    for i, x in enumerate(rows):
        for y, h in d["terms"].get(x, {}).items():
            if y == "FEDE":
                hF[i] += h
            elif y in ci:
                H[i, ci[y]] += h
    return {"rows": rows, "xm": [d["xm"][x] for x in rows], "H": H, "hF": hF}


def feednq_function(name: str, a: dict, n_cols: int):
    """CasADi Function (ra[n_cols], fede) -> dq[rows]: FeedNQ_'s change of each feed from its base (kt)."""
    import casadi as ca
    ra, fede = ca.SX.sym("ra", n_cols), ca.SX.sym("fede")
    dq = ca.mtimes(ca.DM(a["H"]), ra - 1.0) + ca.DM(a["hF"]) * (fede - 1.0)
    return ca.Function(name, [ra, fede], [dq], ["ra", "fede"], ["dq"])
