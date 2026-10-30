"""CAPRI's land-use change (LUC) transition model (supply/supply_model.gms e_landTypes_to_LUclass, e_luClassInitial,
e_luClassFinal, e_FocLUC, e_derivativeOfGammaLUC; priors supply/prep_sim_luc.gms), for one region at the land types of
its regional solution.

  classes   CROP = ARAC + FRUN; GRSLND = GRAS + shG OLND; WETLND = INLW + shW OLND; RESLND = shR OLND; FORE; ARTIF
  T_ij      transitions from initial class i to final class j (1000 ha per year for changes, remaining in full)
  e_luClassInitial   sum_j T_ij f_ij = initial area of i
  e_luClassFinal     sum_i T_ij f_ij = final area of j     (f = the step length for changes, 1 for remaining)
  e_FocLUC           (alpha_ij - 1) / T_ij - beta_ij + dual_j + dual_i = 0   (gamma priors, relative standard error 1;
                     a transition with prior mode 0 is fixed at 0, CAPRI's spike density)
The first-order conditions with the adding-up constraints are those of the posterior mode - the maximum of
sum (alpha - 1) log T - beta T under the adding-up constraints - which is solved here (concave, unique).

Data: capri_data/2017/environment/luc_2030.csv (tools/build/build_luc_2030.py, CAPRI's 2030 reference). Initial classes
and prior modes are CAPRI's 2030 solution for the region (its posterior, as the inner fertiliser model's priors);
final classes are CAPRI's 2030 classes moved by the change in the model's land types from its base.

Solved after the regional supply model, not inside it: without a price on LULUCF emissions the block enters neither
the objective nor any other equation of the regional model, so its solution given the land types is the same
(docs/NLP_PORT_DESIGN.md).
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

CLS = {"CRP": "CROP", "FOR": "FORE", "ART": "ARTIF", "GRS": "GRSLND", "WET": "WETLND", "RES": "RESLND"}


class LUCModel:
    _inst = None

    def __init__(self, data_dir: Optional[str] = None):
        from capri_mod.data.inputs import RunInputs, current
        inp = RunInputs(data_dir, current().base_year) if data_dir else current()
        t = inp.csv("luc_2030.csv", "environment")
        self.v = {r: dict(zip(d.item, d.value)) for r, d in t.groupby("capri_region")}

    @classmethod
    def get(cls) -> "LUCModel":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def solve(self, capri_region: str, d_land: Dict[str, float]) -> Optional[dict]:
        """Transitions of the region at land types changed by d_land {ARAC, FRUN, GRAS, FORE, OLND: 1000 ha} from
        the base. Returns {"transitions": {from+to: 1000 ha per year}, "initial": {...}, "final": {...}, "ok"}."""
        v = self.v.get(capri_region)
        if v is None:
            return None
        from scipy.optimize import minimize
        f = float(v.get("step", 1.0))
        final = {c: float(v.get(c, 0.0)) for c in CLS.values()}
        dl = {k: float(d_land.get(k, 0.0) or 0.0) for k in ("ARAC", "FRUN", "GRAS", "FORE", "OLND")}
        final["CROP"] += dl["ARAC"] + dl["FRUN"]
        final["GRSLND"] += dl["GRAS"] + float(v["shG"]) * dl["OLND"]
        final["WETLND"] += float(v["shW"]) * dl["OLND"]
        final["RESLND"] += float(v["shR"]) * dl["OLND"]
        final["FORE"] += dl["FORE"]
        ini = {CLS[i]: float(v.get("INI" + i, 0.0)) for i in CLS}
        if any(x < 0 for x in final.values()):
            return {"transitions": {}, "initial": ini, "final": final, "step": f, "ok": False, "violation": float("nan")}
        # the region's total area is fixed (ARTO); land types moved among themselves keep it, rounding aside
        s_f, s_i = sum(final.values()), sum(ini.values())
        if s_f > 0:
            final = {k: x * s_i / s_f for k, x in final.items()}
        keys = [i + j for i in CLS for j in CLS]
        mode = np.array([max(float(v.get(k, 0.0)), 0.0) for k in keys])
        free = mode > 0                                             # spike density at a zero mode
        fac = np.array([1.0 if k[:3] == k[3:] else f for k in keys])
        # gamma prior with relative standard error 1 (prep_sim_luc.gms): var = mode^2,
        # temp = (sqrt(m^2 (m^2 + 4 var)) + m^2) / (2 var), alpha = temp + 1, beta = temp / mode
        m = mode[free]
        var = m * m
        temp = (np.sqrt(m * m * (m * m + 4 * var)) + m * m) / (2 * var)
        a1, beta = temp, temp / m
        A, b = [], []
        idx = np.where(free)[0]
        cl = list(CLS)
        for i in cl:                                                # initial classes
            row = np.array([fac[k] if keys[k][:3] == i else 0.0 for k in idx])
            A.append(row); b.append(ini[CLS[i]])
        for j in cl:                                                # final classes
            row = np.array([fac[k] if keys[k][3:] == j else 0.0 for k in idx])
            A.append(row); b.append(final[CLS[j]])
        A, b = np.array(A), np.array(b)
        import casadi as ca
        z = ca.SX.sym("z", len(m))                                 # T / mode
        obj = -ca.sum1(ca.DM(a1) * ca.log(z) - ca.DM(beta * m) * z)
        g = ca.mtimes(ca.DM(A * m[None, :]), z) / ca.DM(np.maximum(1.0, np.abs(b)))
        rhs = b / np.maximum(1.0, np.abs(b))
        from capri_mod.settings import current as _settings
        S = ca.nlpsol("L", "ipopt", {"x": z, "f": obj, "g": g},
                      {"ipopt.print_level": 0, "print_time": 0,
                       "ipopt.tol": float(_settings().get("environment.luc_ipopt_tol")),
                       "ipopt.max_iter": int(_settings().get("environment.luc_max_iter")),
                       "ipopt.bound_relax_factor": 0.0})
        sol = S(x0=np.ones(len(m)), lbx=1e-8 / np.maximum(m, 1e-12), ubx=np.inf, lbg=rhs, ubg=rhs)
        zz = np.asarray(sol["x"]).ravel()
        res = type("R", (), {"success": S.stats()["success"], "x": zz})()
        sc = m
        T = np.zeros(len(keys))
        T[idx] = res.x * sc
        viol = float(np.max(np.abs(A @ T[idx] - b))) if len(b) else 0.0
        return {"transitions": dict(zip(keys, T.tolist())), "initial": ini, "final": final, "step": f,
                "ok": bool(res.success) and viol <= 1e-6 * max(1.0, float(np.max(np.abs(b)))), "violation": viol}
