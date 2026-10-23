"""Check the regional conic model against CAPRI's original (non-convex) formulation with IPOPT (CasADi).

python tools/check/nlp_check/nlp.py CAPDIR [REGION ...]

For each captured regional problem (tools/check/nlp_check/capture.py) the same data are written in CAPRI's own form and
solved with IPOPT from several starting points:

* feeding per head (CAPRI v_feedingLevl): total feed = feed per head x herd, a bilinear term (the conic model uses total
  feed and the perspective of the feed cost - exact by algebra);
* CAPRI's ammonia technologies (v_Miti, NH3MAN / NH3APP): shares per sub-activity, N saved through CAPRI's loss
  cascade exactly (housing -> storage -> application; supply_model.gms HOUSN_, STORN_, APPLN_), bilinear in the
  manure-management and application shares and in the herd (the conic model linearises the N saved per unit of share
  at the previous solve's shares);
* CAPRI's fertiliser technologies (gainsTechFert): ONE regional share per technology, mineral N = need / (1 + sum
  share x NMIN) (the conic model lets each crop adopt separately - registered departure);
* CAPRI's inhibitor on manure: one regional share s, N relief s x NMAN x sub x manure N (bilinear), cost per t of
  manure N (the conic model: perspective in T = s W - exact by algebra).

Everything else - PMP terms, land, constraints, prices - is the captured problem itself. Reported per region: the
objective of the conic solution evaluated in CAPRI's form (with its violation of CAPRI's constraints), IPOPT's best
objective over the starts, and the main differences (activities, shares, N price).
"""
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


from capri_mod.supply.capri_nlp import RegionNLP, _cascade_loss  # noqa: E402,F401


def report(cap, uniform=True, starts=5, seed=0, cascade="exact", feed="perhead"):
    import time
    P = RegionNLP(cap, uniform_fert=uniform, cascade=cascade, feed=feed)
    n0, nf, nt, nphi, nm = P.sizes
    xc = P.from_conic()
    fc_obj = float(P.f_obj(xc)); vc, vrow = P.violation(xc)
    rng = np.random.default_rng(seed)
    # starting points: the conic solution; the base (herds, rations, base shares); perturbed bases
    xb = np.zeros_like(xc)
    xb[:n0] = np.maximum(np.asarray(cap["kwargs"]["x_base"], float)[:n0], 0.0) / P.sc[:n0]
    xb[n0:n0 + nf] = 1.0
    xb[n0 + nf:n0 + nf + nt] = [t["s0"] for t in P.techs]
    if P.n_t:
        xb[len(xb) - P.n_t:] = 1.0
    pts = [("conic", xc), ("base", xb)] + [(f"rand{i}", xb * rng.uniform(0.7, 1.3, xb.size)) for i in range(starts - 2)]
    res = []
    for lab, x0 in pts:
        t0 = time.time()
        x, f, lam, st, it = P.solve(np.clip(x0, P.lbx, P.ubx))
        v, _ = P.violation(x)
        res.append((lab, f, v, st, it, time.time() - t0, x, lam))
    return P, xc, fc_obj, vc, vrow, res


def _summary(P, xc, fc_obj, res):
    ok = [r for r in res if r[3] in ("Solve_Succeeded", "Solved_To_Acceptable_Level") and r[2] < 1e-3]
    if not ok:
        return None, "no start converged: " + ", ".join(sorted(set(r[3] for r in res)))
    best = min(ok, key=lambda r: r[1])
    spread = max(r[1] for r in ok) - min(r[1] for r in ok)
    return best, f"{len(ok)}/{len(res)} starts, spread {spread / abs(best[1]):.1e}"


def main():
    """Per region: (1) the conic model's own relations in this builder (check of the builder: same optimum);
    (2) CAPRI's exact loss cascade, fertiliser shares per crop; (3) CAPRI's exact cascade and one regional share per
    fertiliser technology; (4) as (3) with feeding per head (CAPRI's literal bilinear form)."""
    capdir = Path(sys.argv[1])
    regs = sys.argv[2:] or sorted(p.stem for p in capdir.glob("*.pkl"))
    cases = [("1 builder check (conic relations)", dict(uniform=False, cascade="linear", feed="total")),
             ("2 exact cascade, fert per crop", dict(uniform=False, cascade="exact", feed="total")),
             ("3 exact cascade, fert regional", dict(uniform=True, cascade="exact", feed="total")),
             ("4 as 3, feeding per head", dict(uniform=True, cascade="exact", feed="perhead"))]
    for reg in regs:
        cap = pickle.load(open(capdir / f"{reg}.pkl", "rb"))
        print(f"\n=== {reg} (tax {cap['tax']})")
        for lab, kw in cases:
            P, xc, fc_obj, vc, vrow, res = report(cap, **kw)
            n0, nf, nt, nphi, nm = P.sizes
            best, note = _summary(P, xc, fc_obj, res)
            print(f"  [{lab}] conic point: objective {fc_obj:.6e}, max violation {vc:.3g} | {note}")
            if best is None:
                continue
            x = best[6]
            yb = np.asarray(P.f_y(x)).ravel(); yc = np.asarray(P.f_y(xc)).ravel()
            print(f"      NLP optimum {best[1]:.6e}: NLP - conic {(best[1] - fc_obj) / abs(fc_obj):+.2e} (relative)")
            d = [(P.acts[i], yc[i], yb[i]) for i in range(len(P.acts)) if max(abs(yc[i]), abs(yb[i])) > 1.0]
            d.sort(key=lambda t: -abs(t[2] - t[1]) / max(abs(t[1]), 1.0))
            print("      activities (conic -> NLP): " + ", ".join(f"{a} {u:.1f}->{v:.1f}" for a, u, v in d[:5]))
            if nt:
                sc_ = xc[n0 + nf:n0 + nf + nt]; sb = x[n0 + nf:n0 + nf + nt]
                k = int(np.argmax(np.abs(sb - sc_)))
                print(f"      ammonia shares: mean |diff| {np.mean(np.abs(sb - sc_)):.3f}, max {abs(sb[k] - sc_[k]):.3f} "
                      f"({P.techs[k]['act']} {P.techs[k]['key'].split('|')[-1]} {P.techs[k]['tech']} {sc_[k]:.3f}->{sb[k]:.3f})")
            if nphi == len(P.ft) and nphi:
                o = n0 + nf + nt
                print("      fertiliser shares: " + ", ".join(f"{P.ft[t][0]} {xc[o + t]:.3f}->{x[o + t]:.3f}"
                                                         for t in range(len(P.ft))))
            if nm:
                o = n0 + nf + nt + nphi
                print(f"      inhibitor on manure: {xc[o]:.4f} -> {x[o]:.4f}")
            if P.n_row is not None and P.n_row in P.row_index:
                print(f"      N price: conic {float(cap['out'][2][P.n_row]):.2f} -> NLP {best[7][P.row_index[P.n_row]]:.2f}")


if __name__ == "__main__":
    main()
