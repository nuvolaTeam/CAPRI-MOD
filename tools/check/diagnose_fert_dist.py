"""Why CAPRI's crop-group fertiliser allocation fails in a region: an exact feasibility test at the region's solution.

The supply module saves, where the allocation fails (env CAPRI_FD_DUMP = a directory; supply_module._fd_dump), the
region's crop-group block (_fert_dist_spec) and its solution. At that solution - areas, herds, mineral N M, manure N
applied E, arable residues C fixed - CAPRI's inner fertiliser distribution model (supply_model.gms with
useInnerFertDistModel) needs flows x_gs (crop group g, source s) with

    NUTNED_        sum_s e_s x_gs = N_g,  N_g = w_g / W x (e_M M + e_E E + e_C C)
    fertDistExcr_  sum_g x_g,EXCR = E;  the arable residue pool likewise
    bounds         0.001 m_gs <= x_gs <= 1000 m_gs  (m_gs: CAPRI's prior mode, prep_sim.gms)
    regulations    x_gs <= cap_g x area_g          (e.g. the Green Deal's mineral caps by crop group)

and its posterior mode (e_focFertDist) exists exactly when this linear system has a point strictly inside the bounds:
the inner model's objective is strictly concave (gamma priors with shape >= 1, beta regulations) and goes to minus
infinity at the bounds. So the test is a linear program - definitive, unlike a local NLP solver's verdict.

Phase 1: minimise the violation of the equalities (slack per row, in t N) with x inside the bounds - zero means the
allocation exists at this solution. Phase 2 (if it exists): the largest margin t with x_gs within [lb + t m, ub - t m]
- how far from the bounds the allocation can stay. Per group it also prints what the bounds allow: the N a group can
receive at most (all sources at their upper bounds or caps) and at least, against its need.

    python tools/check/diagnose_fert_dist.py DUMP_DIR [--region SE22]
"""
from __future__ import annotations
import argparse, glob, os, pickle, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

SOURCES = ("MINE", "EXCR", "CRES")


def block_at(d):
    """The allocation's data at the saved solution: groups, flows (g, s, m0, lb, ub), needs N_g, pools."""
    fd, y = d["fd"], np.asarray(d["y"], float)
    lin = lambda pairs: float(sum(float(v) * y[int(c)] for c, v in pairs)) if pairs else 0.0
    e = fd["e"]
    M, E, C = float(fd["M"]), float(fd["Etot"]), float(fd["Ctot"])
    T = e["MINE"] * M + e["EXCR"] * E + e["CRES"] * C
    G = fd["groups"]
    A = [lin(g["crops"]) for g in G]
    w = [float(g["per"]) * lin(g["need"]) for g in G]
    W = sum(w)
    N = [wi / W * T if W > 0 else 0.0 for wi in w]
    flows = []
    for gi, g in enumerate(G):
        Aref = float(g.get("Aref", fd["A0"][gi]))
        for s, spec in g["flows"].items():
            p, acc, cap = spec[0], spec[1], spec[2] if len(spec) > 2 else None
            m0 = max(float(p) * Aref, 1e-6)
            lb, ub = 1e-3 * m0, 1e3 * m0
            capv = None
            if cap is not None:
                capv = float(cap[0]) * A[gi]
                ub = min(ub, capv)
            flows.append(dict(g=gi, s=s, m0=m0, lb=lb, ub=ub, cap=capv))
    return dict(groups=[g["g"] for g in G], A=A, N=N, M=M, E=E, C=C, T=T, e=e, flows=flows)


def feasibility(b):
    from scipy.optimize import linprog
    F, G = b["flows"], b["groups"]
    nf = len(F)
    rows, rhs, fam = [], [], []
    for gi, g in enumerate(G):
        r = np.zeros(nf)
        for i, f in enumerate(F):
            if f["g"] == gi:
                r[i] = b["e"][f["s"]]
        rows.append(r); rhs.append(b["N"][gi]); fam.append(("need", g))
    for s, tot in (("EXCR", b["E"]), ("CRES", b["C"])):
        r = np.array([1.0 if f["s"] == s else 0.0 for f in F])
        if r.any() or tot > 0:
            rows.append(r); rhs.append(tot); fam.append(("pool", s))
    Aeq = np.array(rows); beq = np.array(rhs)
    m = len(rows)
    # phase 1: x within bounds, equalities with slacks (+/-), minimise the total slack (t N)
    c = np.concatenate([np.zeros(nf), np.ones(2 * m)])
    A1 = np.hstack([Aeq, np.eye(m), -np.eye(m)])
    bounds = [(f["lb"], f["ub"]) if f["ub"] >= f["lb"] else (f["lb"], f["lb"]) for f in F] + [(0, None)] * (2 * m)
    r1 = linprog(c, A_eq=A1, b_eq=beq, bounds=bounds, method="highs")
    viol = r1.x[nf:nf + m] - r1.x[nf + m:] if r1.success else np.full(m, np.nan)
    capbad = [f for f in F if f["cap"] is not None and f["cap"] < f["lb"]]
    out = dict(status=r1.status, total_violation=float(r1.fun) if r1.success else np.nan,
               rows=[(fa, float(v), float(bq)) for fa, v, bq in zip(fam, viol, beq)], caps_below_lb=capbad)
    # phase 2: largest margin from the bounds (in units of the prior mode) with the equalities exact
    if r1.success and r1.fun <= 1e-6 * max(1.0, float(np.abs(beq).sum())):
        c2 = np.concatenate([np.zeros(nf), [-1.0]])
        Aub, bub = [], []
        for i, f in enumerate(F):
            r = np.zeros(nf + 1); r[i] = -1.0; r[-1] = f["m0"]; Aub.append(r); bub.append(-f["lb"])
            r = np.zeros(nf + 1); r[i] = 1.0; r[-1] = f["m0"]; Aub.append(r); bub.append(f["ub"])
        r2 = linprog(c2, A_ub=np.array(Aub), b_ub=np.array(bub), A_eq=np.hstack([Aeq, np.zeros((m, 1))]), b_eq=beq,
                     bounds=[(None, None)] * nf + [(0, None)], method="highs")
        out["margin"] = float(r2.x[-1]) if r2.success else np.nan
    return out


def group_ranges(b):
    """Per group: need N_g against the N the bounds allow (sum_s e_s x at its upper / lower bound)."""
    out = []
    for gi, g in enumerate(b["groups"]):
        fl = [f for f in b["flows"] if f["g"] == gi]
        hi = sum(b["e"][f["s"]] * f["ub"] for f in fl)
        lo = sum(b["e"][f["s"]] * f["lb"] for f in fl)
        out.append((g, b["A"][gi], b["N"][gi], lo, hi, ",".join(f["s"] for f in fl),
                    [round(f["cap"], 1) for f in fl if f["cap"] is not None]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump_dir")
    ap.add_argument("--region", default="")
    ap.add_argument("--first", action="store_true", help="only the first dump of each region and kind")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.dump_dir, "*.pkl")))
    seen = set()
    for f in files:
        d = pickle.load(open(f, "rb"))
        if a.region and d["region"] != a.region:
            continue
        if a.first and (d["region"], d["why"]) in seen:
            continue
        seen.add((d["region"], d["why"]))
        b = block_at(d)
        r = feasibility(b)
        print(f"\n== {Path(f).name}: {d['why']}, CAPRI region {d['fd'].get('capri_region')} | M {b['M']:.0f} t, "
              f"E {b['E']:.0f} t, C {b['C']:.0f} t, N to distribute {b['T']:.0f} t")
        ex = r["total_violation"] <= 1e-6 * max(1.0, b["T"])
        print(f"   allocation exists: {ex}  (least violation of the equalities {r['total_violation']:.3g} t N"
              + (f"; margin from the bounds {r.get('margin', float('nan')):.3g} x prior mode)" if ex else ")"))
        if not ex:
            for fa, v, bq in r["rows"]:
                if abs(v) > 1e-6 * max(1.0, abs(bq)):
                    print(f"   violated {fa[0]:5s} {fa[1]:6s}: {v:+.1f} t of {bq:.1f} t")
            if r["caps_below_lb"]:
                print(f"   caps below CAPRI's lower bound 0.001 x mode: "
                      f"{[(b['groups'][x['g']], x['s']) for x in r['caps_below_lb']]}")
            for g, A, N, lo, hi, srcs, caps in group_ranges(b):
                flag = " <-- need above what the bounds allow" if N > hi + 1e-9 else (
                    " <-- need below the bounds' minimum" if N < lo - 1e-9 else "")
                print(f"     {g:6s} area {A:8.2f} kha  need {N:9.1f} t  bounds allow [{lo:9.1f}, {hi:10.1f}] t  "
                      f"sources {srcs:15s} caps {caps}{flag}")


if __name__ == "__main__":
    main()
