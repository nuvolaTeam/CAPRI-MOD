"""CAPRI's farm-structure estimation for the Western Balkans and Turkey (envind/prep_farm_size_data_for_miti.gms),
ported 4 November 2026.

CAPRI has Eurostat's farm structure (AD_basedata.gdx p_Heads, p_sf; holdingsLSU.gdx p_holdLSU) for the EU and the UK
only. For the six Western Balkan countries and Turkey's twelve units it estimates them, per region, with two small
least-squares models, solved in a loop over rloop = MSnoEU + Turkey's units, less the UK, Norway and WBA (l. 439-531):

  targets   fallback_Balkan (sets.gms l. 8111-8119): the unweighted average over Romania, Bulgaria, Croatia and their
            NUTS 2 units having a value, cell by cell, of the animals' size-class shares (p_Heads_shares), the farms'
            shares (p_farm_shares, from heads x p_LUunit_assumed / p_sf), the average farm size p_sf, the heads per
            holding (p_heads_per_hold, cattle pooled) and the holdings' shares (p_holdLSU_shares) (l. 200-266)
  m_fsclass        (l. 328-373): the region's animals in LSU (2030 levels x 1000 x days / 365 x p_LUUnits) split into
            the size classes, the farm total p_farmsTotal split by farm shares, the farm size in each class within the
            class bounds; least squares on the farm size (relative), the animal shares and the farm shares
  m_heads_per_hold (l. 378-436): the animals in heads split by the shares, holdings per animal group and class at most
            p_farm_multiplier x farm total / 9 x holding share, heads = heads per holding x holdings (dairy and other
            cattle pooled on the same holdings), heads per holding within the class bounds x p_corLSUfactor; least
            squares on the heads per holding (relative) and, x 1000, on the two share sets
  results   p_sf <- m_fsclass's farm sizes; p_heads_per_hold, p_holdLSU and p_Heads (heads) <- m_heads_per_hold (l. 481,
            520-527)

The farm totals (p_farmsTotal: Serbia 631,552, Albania 340,000, Bosnia 390,000, Kosovo 100,000, Montenegro 50,000,
North Macedonia 70,000, Turkey 2,560,000 split equally over its 12 units), p_LUunit_assumed, p_corLSUfactor,
p_sizeControl and p_farm_multiplier are written in CAPRI's code; they are read from it here, not copied.

The animals: CAPRI uses data(region, activity, "LEVL"/"DAYS", "y"), the simulation year's base: here CAPRI's Green
Deal 2030 ini levels (capri_marginal_terms_ini_2030) and 2030 days (capri_mann_days_2030), the run the model
calibrates on. Solved with IPOPT (CasADi), from CAPRI's starting point (l. 464-511; CAPRI keeps a variable's level from
the previous region of the loop where it sets none: here the holdings of dairy cattle start at heads / heads per
holding as the other groups') and from a second one; the lowest objective is kept (estimate_best, REGISTERED).

Written (capri_data/2017/abatement/ammonia/):
  farm_size_noneu.csv     region, ad_activity, size_class, heads (p_Heads), holdings (p_holdLSU),
                          heads_per_hold (p_heads_per_hold)
  farm_size_noneu_sf.csv  region, size_class, sf (p_sf, LSU per farm)

    python tools/build/build_farm_size_noneu.py [--gams-dir capri_sources/gams]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import casadi as ca
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import gams_text as G  # noqa: E402
import _model_regions as mr  # noqa: E402
from paths import SOURCES  # noqa: E402

SRC = ROOT / "capri_data" / "sources"
AMM = ROOT / "capri_data" / "2017" / "abatement" / "ammonia"
LEVELS = ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_marginal_terms_ini_2030.csv.xz"


def _rd(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def capri_constants(gams_dir: Path) -> dict:
    """The constants CAPRI writes in prep_farm_size_data_for_miti.gms and the region sets of sets.gms."""
    t = G.read_text(gams_dir / "envind" / "prep_farm_size_data_for_miti.gms")
    up = str.upper
    c = {
        "farms_total": {r: float(v) for r, v in G.parameter_records(t, "p_farmsTotal", 1)},
        "lu_assumed": {up(a): float(v) for a, v in G.parameter_records(t, "p_LUunit_assumed", 1)},
        "size": defaultdict(dict), "cor": defaultdict(dict),
        "animals": [(up(m), up(a)) for m, a in G.set_pairs(t, "map_animals_all")],
    }
    for f, k, v in G.table_records(t, "p_sizeControl", 1):
        c["size"][f][k] = float(v)
    for a, k, v in G.table_records(t, "p_corLSUfactor", 1):
        c["cor"][up(a)][k] = float(v)
    m = re.search(r"Scalar\s+p_farm_multiplier[^/]*/\s*([0-9.]+)\s*/", t, re.I)
    c["multiplier"] = float(m.group(1))
    m = re.search(r"set\s+fsclass_red\(fsclass\)[^/]*/(.*?)/", t, re.I | re.S)
    c["fs_red"] = [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]
    s = G.read_text(gams_dir / "sets.gms")
    fb = G.set_pairs(s, "fallback_Balkan")
    c["fallback_to"] = list(dict.fromkeys(a for a, _b in fb))
    c["fallback_from"] = list(dict.fromkeys(b for _a, b in fb))
    split = lambda x: [v.strip() for v in x.replace("\n", ",").split(",") if v.strip()]
    m = re.search(r"SET\s+MSnoEU\(RALL\)[^/]*/(.*?)/", s, re.I | re.S)
    c["msnoeu"] = split(m.group(1))
    m = re.search(r"SET\s+NUTS0_WBA6\s*/(.*?)/\s*;", s, re.I | re.S)
    c["wba6"] = [ln.split()[0] for ln in m.group(1).splitlines() if ln.strip()]
    return c


def loop_regions(c: dict) -> list:
    """rloop $ rs (l. 439-454): MSnoEU (SET.R_NUTS0_WBA6 expanded) and Turkey's units, less the UK, Norway, WBA; the
    supply regions among them (the model's units)."""
    names = []
    for x in c["msnoeu"]:
        names += c["wba6"] if x.upper() == "SET.R_NUTS0_WBA6" else [x]
    units = set(mr.UNITS)
    out = [r for r in names if r not in ("UK000000", "NO000000", "WBA") and r in units]
    out += sorted(u for u in units if mr.national_code(u) == "TUR")
    return out


def _fallback(table: dict, regions_from: list, key_cells) -> dict:
    """CAPRI's fallback_Balkan average of one cell: over the source regions with a non-zero value, unweighted."""
    out = {}
    for k in key_cells:
        vals = [table[r][k] for r in regions_from if table.get(r, {}).get(k)]
        if vals:
            out[k] = sum(vals) / len(vals)
    return out


def targets(c: dict):
    """CAPRI's l. 200-266 for the fallback regions: {name: {cell: value}} shared by every loop region (none has data
    of its own)."""
    heads = defaultdict(dict)
    for r in _rd(SRC / "raw" / "capri" / "dat" / "scen" / "ghgtech" / "AD_basedata_p_Heads.csv"):
        heads[r["dim1"]][(r["dim2"].upper(), r["dim3"])] = float(r["level"])
    sf = defaultdict(dict)
    for r in _rd(SRC / "raw" / "capri" / "dat" / "scen" / "ghgtech" / "AD_basedata_p_sf.csv"):
        sf[r["dim1"]][r["dim2"]] = float(r["level"])
    hold = defaultdict(lambda: defaultdict(float))
    for r in _rd(AMM / "p_holdLSU.csv"):
        a, f, v = r["animal_group"].upper(), r["size_class"], float(r["value"])
        if f == "100_500":                                      # l. 131-132
            hold[r["region"]][(a, "100_200")] += v / 4
            hold[r["region"]][(a, "200_500")] += v * 3 / 4
        else:
            hold[r["region"]][(a, f)] += v
    F = list(c["size"])
    A = sorted({a for _m, a in c["animals"]})
    cells = [(a, f) for a in A for f in F]
    hsh = {}
    for r, d in heads.items():
        for a in A:
            tot = sum(d.get((a, f), 0.0) for f in F)
            if tot:
                hsh.setdefault(r, {}).update({(a, f): d.get((a, f), 0.0) / tot for f in F})
    farms = {r: {f: sum(heads[r].get((a, f), 0.0) * c["lu_assumed"][a] for a in A) / sf[r][f]
                 for f in F if sf.get(r, {}).get(f)} for r in heads}
    fsh = {}
    for r, d in farms.items():
        tot = sum(d.values())
        if tot:
            fsh[r] = {f: v / tot for f, v in d.items()}
    hph = {}
    for r, d in hold.items():
        for (a, f), h in d.items():
            if not h:
                continue
            num = (heads[r].get(("DAIRY", f), 0.0) + heads[r].get(("NDAIRY", f), 0.0) if a in ("DAIRY", "NDAIRY")
                   else heads[r].get((a, f), 0.0))
            hph.setdefault(r, {})[(a, f)] = num / h
    hosh = {}
    for r, d in hold.items():
        for a in A:
            tot = sum(d.get((a, f), 0.0) for f in F)
            if tot:
                hosh.setdefault(r, {}).update({(a, f): d.get((a, f), 0.0) / tot for f in F})
    src = c["fallback_from"]
    return {"hsh": _fallback(hsh, src, cells), "fsh": _fallback(fsh, src, F), "sf": _fallback(sf, src, F),
            "hph": _fallback(hph, src, cells), "hosh": _fallback(hosh, src, cells)}, A, F


def animals(region: str, c: dict, lev: dict, days: dict, lu: dict):
    """{group: heads} and {group: LSU} of a region (e_heads, e_headsLSU: levels x 1000 x days / 365 [x p_LUUnits])."""
    H, L = defaultdict(float), defaultdict(float)
    for m, a in c["animals"]:
        h = lev.get((region, m), 0.0) * 1000.0 * days.get((region, m), 0.0) / 365.0
        H[a] += h
        L[a] += h * lu.get(m, 0.0)
    return H, L


IPOPT_OPTS = {"ipopt.print_level": 0, "print_time": 0, "ipopt.tol": 1e-10, "ipopt.max_iter": 3000,
              "ipopt.bound_relax_factor": 0.0}


def _solve(x, x0, lbx, ubx, obj, g, lbg, ubg, name, scaling="gradient-based"):
    S = ca.nlpsol(name, "ipopt", {"x": x, "f": obj, "g": g}, {**IPOPT_OPTS, "ipopt.nlp_scaling_method": scaling})
    r = S(x0=x0, lbx=lbx, ubx=ubx, lbg=lbg, ubg=ubg)
    st = S.stats()
    if not st["success"]:
        raise RuntimeError(f"{name}: {st['return_status']}")
    return np.array(r["x"]).ravel(), float(r["f"])


def estimate(region, T, H, L, tg, A, F, c, dairy_start="own", scaling="gradient-based"):
    """The two models of one region; returns (sf {f}, heads {(a, f)}, holdings {(a, f)}, hph {(a, f)})."""
    nA, nF = len(A), len(F)
    red = [f in c["fs_red"] for f in F]
    lo = np.array([c["size"][f].get("lower", 0.0) for f in F])
    hi = np.array([c["size"][f].get("upper", np.inf) if r else np.inf for f, r in zip(F, red)])
    shsh = np.array([[tg["hsh"].get((a, f), 0.0) for f in F] for a in A])
    sfsh = np.array([tg["fsh"].get(f, 0.0) for f in F])
    ssf = np.array([tg["sf"].get(f, 0.0) for f in F])
    Lv = np.array([L[a] for a in A])
    # --- m_fsclass: x = sf, farms, fsh, hsh (nA x nF), hlsu (nA x nF)
    sf, fa, fs = ca.SX.sym("sf", nF), ca.SX.sym("fa", nF), ca.SX.sym("fs", nF)
    hs, hl = ca.SX.sym("hs", nA, nF), ca.SX.sym("hl", nA, nF)
    obj = (ca.sum1((sf - ssf) ** 2 / np.maximum(10.0, ssf ** 2)) + ca.sum1(ca.sum2((hs - shsh) ** 2))
           + ca.sum1((fs - sfsh) ** 2))
    g = [ca.vec(hl - ca.repmat(Lv, 1, nF) * hs), ca.sum2(hs), fa - T * fs, ca.sum1(fs), ca.sum1(hl).T - sf * fa]
    lbg = [np.zeros(nA * nF), np.ones(nA), np.zeros(nF), [1.0], np.zeros(nF)]
    x = ca.vertcat(sf, fa, fs, ca.vec(hs), ca.vec(hl))
    x0 = np.concatenate([ssf, T * sfsh, sfsh, shsh.ravel(order="F"), (Lv[:, None] * shsh).ravel(order="F")])
    lbx = np.concatenate([lo, np.zeros(nF * 2 + nA * nF * 2)])
    ubx = np.concatenate([hi, np.full(nF * 2 + nA * nF * 2, np.inf)])
    sol, _ = _solve(x, x0, lbx, ubx, obj, ca.vertcat(*g), np.concatenate(lbg), np.concatenate(lbg), f"fs_{region}")
    sf_l = sol[:nF]
    hs_l = sol[3 * nF:3 * nF + nA * nF].reshape((nA, nF), order="F")
    # --- m_heads_per_hold: x = hph, hold, heads, hosh, hsh (each nA x nF)
    shph = np.array([[tg["hph"].get((a, f), 0.0) for f in F] for a in A])
    shosh = np.array([[tg["hosh"].get((a, f), 0.0) for f in F] for a in A])
    Hv = np.array([H[a] for a in A])
    corlo = np.array([c["cor"][a]["lower"] for a in A])
    corhi = np.array([c["cor"][a]["upper"] for a in A])
    hp, ho, hd, os_, hs2 = (ca.SX.sym(n, nA, nF) for n in ("hp", "ho", "hd", "os", "hs2"))
    obj2 = (ca.sum1(ca.sum2((hp - shph) ** 2 / np.maximum(10.0, shph ** 2)))
            + 1000.0 * ca.sum1(ca.sum2((hs2 - shsh) ** 2)) + 1000.0 * ca.sum1(ca.sum2((os_ - shosh) ** 2)))
    iD, iN = A.index("DAIRY"), A.index("NDAIRY")
    rd = [i for i, a in enumerate(A) if a not in ("DAIRY", "NDAIRY")]
    g2, lb2, ub2 = [], [], []
    g2.append(ca.vec(hd - ca.repmat(Hv, 1, nF) * hs2)); lb2.append(np.zeros(nA * nF)); ub2.append(np.zeros(nA * nF))
    g2.append(ca.sum2(hs2)); lb2.append(np.ones(nA)); ub2.append(np.ones(nA))
    g2.append(ca.sum2(os_)); lb2.append(np.ones(nA)); ub2.append(np.ones(nA))
    g2.append(ca.vec(ho * nF - T * c["multiplier"] * os_)); lb2.append(np.full(nA * nF, -np.inf)); ub2.append(np.zeros(nA * nF))
    for i in rd:
        g2.append((hd[i, :] - hp[i, :] * ho[i, :]).T); lb2.append(np.zeros(nF)); ub2.append(np.zeros(nF))
    g2.append((ho[iD, :] - ho[iN, :]).T); lb2.append(np.zeros(nF)); ub2.append(np.zeros(nF))
    g2.append((hd[iD, :] + hd[iN, :] - hp[iD, :] * ho[iD, :]).T); lb2.append(np.zeros(nF)); ub2.append(np.zeros(nF))
    x2 = ca.vertcat(ca.vec(hp), ca.vec(ho), ca.vec(hd), ca.vec(os_), ca.vec(hs2))
    hd0 = Hv[:, None] * hs_l
    ho0 = np.where(shph > 0, hd0 / np.where(shph > 0, shph, 1.0), 0.0)
    if dairy_start == "zero":
        ho0[[iD, iN], :] = 0.0
    x20 = np.concatenate([m.ravel(order="F") for m in (shph, ho0, hd0, shosh, hs_l)])
    hplo = lo[None, :] * corlo[:, None]
    hphi = np.where(np.array(red)[None, :], np.where(np.isfinite(hi), hi, 0.0)[None, :] * corhi[:, None], np.inf)
    lbx2 = np.concatenate([hplo.ravel(order="F"), np.zeros(4 * nA * nF)])
    ubx2 = np.concatenate([hphi.ravel(order="F"), np.full(4 * nA * nF, np.inf)])
    sol2, f2 = _solve(x2, x20, lbx2, ubx2, obj2, ca.vertcat(*g2), np.concatenate(lb2), np.concatenate(ub2),
                      f"hph_{region}", scaling)
    n = nA * nF
    hp_l, ho_l, hd_l = (sol2[k * n:(k + 1) * n].reshape((nA, nF), order="F") for k in range(3))
    cell = lambda M: {(a, f): float(M[i, j]) for i, a in enumerate(A) for j, f in enumerate(F)}
    return f2, (dict(zip(F, map(float, sf_l))), cell(hd_l), cell(ho_l), cell(hp_l))


def estimate_best(region, T, H, L, tg, A, F, c):
    """m_heads_per_hold is not convex (heads = heads per holding x holdings): CAPRI takes the one local solution its
    solver reaches from its start. Here four solves (CAPRI's start and one with the dairy holdings at zero, each with
    and without IPOPT's gradient scaling) and the lowest objective (REGISTERED). They agree to 1e-6 in 16 of the 18
    regions; in TR100000 and TR800000, the two without sheep, the objectives differ (18.95-19.04, 127.77-128.50) through
    the sheep cells, which hold no animals: the groups with animals are the same (checked 4 November 2026)."""
    sols = []
    for st in ("own", "zero"):
        for sc in ("gradient-based", "none"):
            try:
                sols.append(estimate(region, T, H, L, tg, A, F, c, st, sc))
            except RuntimeError:
                pass
    if not sols:
        raise RuntimeError(f"{region}: no solve of the farm-structure models succeeded")
    f = sorted(s[0] for s in sols)
    best = min(sols, key=lambda s: s[0])
    return best[1], f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gams-dir", type=Path, default=SOURCES / "gams")
    a = ap.parse_args()
    c = capri_constants(a.gams_dir)
    tg, A, F = targets(c)
    lu = {r["act"].upper(): float(r["value"]) for r in _rd(SRC / "raw" / "capri" / "dat" / "policy" / "livestock_units_p_LUUnits.csv")}
    t = pd.read_csv(LEVELS, dtype=str)
    t = t[t["item"] == "LEVL"]
    lev = {(r.region, r.activity): float(r.value) for r in t.itertuples()}
    days = {(r["region"], r["activity"]): float(r["value"]) for r in _rd(AMM / "capri_mann_days_2030.csv")
            if r["item"] == "DAYS"}
    regions = loop_regions(c)
    n_tur = sum(1 for r in regions if mr.national_code(r) == "TUR")
    rows, rows_sf, spread = [], [], {}
    for r in regions:
        T = (c["farms_total"]["TUR"] / n_tur if mr.national_code(r) == "TUR" else c["farms_total"][r])
        H, L = animals(r, c, lev, days, lu)
        (sf, hd, ho, hp), objs = estimate_best(r, T, H, L, tg, A, F, c)
        spread[r] = (objs[0], objs[-1], len(objs))
        rows += [(r, ad, f, hd[(ad, f)], ho[(ad, f)], hp[(ad, f)]) for ad in A for f in F]
        rows_sf += [(r, f, sf[f]) for f in F]
    AMM.mkdir(parents=True, exist_ok=True)
    with open(AMM / "farm_size_noneu.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["region", "ad_activity", "size_class", "heads", "holdings", "heads_per_hold"])
        w.writerows([r_, ad, f, repr(h), repr(o), repr(p)] for r_, ad, f, h, o, p in rows)
    with open(AMM / "farm_size_noneu_sf.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["region", "size_class", "sf"])
        w.writerows([r_, f, repr(v)] for r_, f, v in rows_sf)
    print(f"farm_size_noneu.csv: {len(regions)} regions, {len(rows)} rows; objectives (best, worst, solves) where the "
          f"solves differ: " + "; ".join(f"{r} {a:.4f} {b:.4f} {n}" for r, (a, b, n) in spread.items()
                                          if b - a > 1e-6 * max(1.0, a)))


if __name__ == "__main__":
    main()
