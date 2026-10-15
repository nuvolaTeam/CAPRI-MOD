"""CAPRI's statistical inner fertiliser distribution model (supply/supply_model.gms, "inner model" block;
star 3.0 GUI default useInnerFertDistModel = ON).

Per region, the nitrogen of three sources s - mineral fertiliser (MINE), manure (EXCR), crop residues and deposition
(CRES) - is distributed to the crop groups g (supply/define_ngrp_sets.gms) as the mode of the posterior density of
the flows x_gs given gamma priors, subject to CAPRI's constraints:

  NUTNED_        sum_s e_s x_gs = N_g            each group's need (net of the permanent groups' own residues)
  fertDistExcr_  sum_g x_g,EXCR = E              manure N applied in the region
  fertDistCres_  sum_g x_g,CRES = C              arable residue pool (not to permanent groups)
  fertDistMine_  sum_g x_g,MINE = M              mineral N (follows from the others)

e_s: mineral efficiency (1 - losses), manure availability, residue availability. The first-order conditions
(e_fertDistPartial, e_focFertDist) are

  (alpha_gs - 1) / x_gs - beta_gs [+ regulation terms] = lambda_g e_s - mu_s

with the gamma parameters from the prior mode m_gs and accuracy a (supply/set_fert_priors.gms):
  var = (m / a)^2,  beta = (m + sqrt(m^2 + 4 var)) / (2 var),  alpha = beta^2 var.
In a simulation the prior mode is the baseline's posterior mode per hectare times the group's current area
(sourceStat postMode; capri_data/2017/environment/fert_dist_priors_2030.csv, accuracy 1).

Optional "regulations" (fertDistRegulation; beta densities on per-group flows, e_fertDistPartialRegu): a maximum
per hectare y_max on a flow adds (beta1 - 1) / x - (beta2 - 1) / (Y - x) with Y = y_max x area, mode 0.75 y_max,
accuracy 0.25, beta1 = mode / max x accuracy + 1, beta2 = accuracy + 2 - beta1 (set_fert_priors.gms). The Green
Deal's mineral-fertiliser reduction by crop uses them ("f2f" on MINE, "limCres" on CRES).

Solved by Newton's method on (lambda, mu) with mu_MINE = 0 (the one gauge freedom of the duals; CAPRI fixes it the
same way when it solves the inner model alone, e_fixOneVariable): each flow then solves its own first-order
condition in closed form.
"""
from __future__ import annotations

from math import sqrt
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from capri_mod.params import param, param_table

SOURCES = ("MINE", "EXCR", "CRES")
PERM_NGRP = frozenset({"GRAS", "PERM"})


def gamma_params(mode: float, accuracy: float) -> Tuple[float, float]:
    """(alpha, beta) of CAPRI's gamma prior (set_fert_priors.gms, non-normalised)."""
    var = (mode / accuracy) ** 2
    beta = (mode + sqrt(mode * mode + 4.0 * var)) / (2.0 * var)
    return beta * beta * var, beta


def beta_regulation(accuracy: float = 0.25, mode_share: float = 0.75) -> Tuple[float, float]:
    """(beta1, beta2) of CAPRI's regulation density with its mode at mode_share of the maximum
    (set_fert_priors.gms: beta1 = priModePerHa / priMaxPerHa x accuracy + 1, beta2 = accuracy + 2 - beta1).
    Defaults: CAPRI's generic regulation ("f2f": mode 0.75 x max, accuracy 0.25). "limCres": mode = the baseline's
    residues per ha, max = (1.3 + relaxation) x that, accuracy 10."""
    b1 = mode_share * accuracy + 1.0
    return b1, accuracy + 2.0 - b1


#: the model's simulation year (CAPRI's 2030 reference); CAPRI's year-dependent exemptions apply for simy > year
SIM_YEAR = 2030
#: CAPRI minfert_redu_by_crop.gms: groups below 0.03 t/ha of mineral N at baseline are exempt (capped at baseline)
SMALL_MINE_KG_HA = param("SMALL_MINE_KG_HA")
#: CAPRI minfert_redu_by_crop.gms: limCres maximum = baseline residues per ha x (1.3 + relaxation)
LIMCRES_FACTOR = param("LIMCRES_FACTOR")


def parse_mineral_redu(v) -> Tuple[Optional[str], float]:
    """CAPRI's mineRedu setting -> (kind, reduction share): ("uaa", 0.2) for "20" (minfert_redu_uaa.gms),
    ("crp", 0.2) for "20crp" (minfert_redu_by_crop.gms), (None, 0) for "00"."""
    s = (f"{v:02d}" if isinstance(v, int) else str(v or "00")).lower()
    if s in ("", "0", "00"):
        return None, 0.0
    if s.endswith("crp"):
        return "crp", float(s[:-3]) / 100.0
    return "uaa", float(s) / 100.0


def _flow(a1: float, beta: float, rhs: float, cap: Optional[float], b2: float) -> Tuple[float, float]:
    """Solve a1 / x - beta - b2 / (cap - x) = rhs for x in (0, cap) (cap None: no regulation);
    returns (x, dx/drhs)."""
    k = beta + rhs
    if cap is None or b2 <= 0:
        if k <= 0:
            return float("inf"), float("-inf")
        x = a1 / k
        return x, -x * x / a1
    # k x^2 - (a1 + b2 + k cap) x + a1 cap = 0, root in (0, cap)
    A, B, Cc = k, -(a1 + b2 + k * cap), a1 * cap
    if abs(A) < 1e-14:
        x = Cc / -B
    else:
        disc = max(B * B - 4.0 * A * Cc, 0.0)
        r1, r2 = (-B - sqrt(disc)) / (2 * A), (-B + sqrt(disc)) / (2 * A)
        cand = [r for r in (r1, r2) if 0.0 < r < cap]
        x = min(cand) if cand else min(max(r1, 1e-12), cap * (1 - 1e-12))
    curv = a1 / (x * x) + b2 / ((cap - x) ** 2)
    return x, -1.0 / curv


class InnerFertDist:
    """Priors and solver of CAPRI's inner fertiliser distribution model for the model's regions."""

    def __init__(self, data_dir: Optional[str] = None):
        root = Path(data_dir) if data_dir else Path(__file__).resolve().parents[2] / "capri_data"
        env = root / "2017" / "environment"
        self._root = root
        self.priors = pd.read_csv(env / "fert_dist_priors_2030.csv")
        self.groups = pd.read_csv(env / "fert_dist_crop_groups_2030.csv")
        self._pri = {r: d.set_index("ngrp") for r, d in self.priors.groupby("capri_region")}
        self._grp = {r: d for r, d in self.groups.groupby("capri_region")}
        self._map = {}
        rm = root / "shared" / "region_capri_map.csv"
        if rm.exists():
            for r in pd.read_csv(rm, dtype=str).fillna("").itertuples(index=False):
                if r.capri_region:
                    self._map[r.region] = r.capri_region

    def capri_region(self, region: str) -> Optional[str]:
        """The CAPRI region (8-character NUTS2 code) of a model region (shared/region_capri_map.csv), else its
        country's (CAPRI NUTS0 code)."""
        c = self._map.get(region)
        if c in self._pri:
            return c
        cc = {"GR": "EL", "BE": "BL", "LU": "BL", "IE": "IR", "UK": "UK"}.get(region[:2], region[:2]) + "000000"
        return cc if cc in self._pri else None

    def crop_shares(self, region: str) -> Dict[str, Dict[str, float]]:
        """Model crop -> {CAPRI crop group: area share} of the region (CAPRI's 2030 crop areas). A model crop the
        region's CAPRI data do not grow takes its mean shares over the CAPRI regions that grow it."""
        r = self.capri_region(region)
        if not hasattr(self, "_eu_shares"):
            w = self.groups.groupby(["model_crop", "ngrp"]).share.sum()
            tot = w.groupby(level=0).transform("sum")
            self._eu_shares = {}
            for (mc, ng), v in (w / tot).items():
                self._eu_shares.setdefault(mc, {})[ng] = float(v)
        out = {mc: dict(v) for mc, v in self._eu_shares.items()}
        if r is not None and r in self._grp:
            own = {}
            for t in self._grp[r].itertuples(index=False):
                own.setdefault(t.model_crop, {})[t.ngrp] = float(t.share)
            out.update(own)
        return out

    def group_areas(self, region: str, crop_areas: Dict[str, float]) -> Dict[str, float]:
        """Crop-group areas (1000 ha) from model crop areas, by CAPRI's group shares of the region."""
        if self.capri_region(region) is None:
            return {}
        sh = self.crop_shares(region)
        out = {}
        for c, a in crop_areas.items():
            a = float(a or 0.0)
            if a > 0:
                for g, w in sh.get(c, {}).items():
                    out[g] = out.get(g, 0.0) + a * w
        return out

    def group_factors(self, region: str, crop_areas: Dict[str, float], crop_factor: Dict[str, float]) -> Dict[str, float]:
        """Area-weighted mean of a per-crop factor over each group (e.g. the need factor sqrt(yield / base yield))."""
        sh = self.crop_shares(region)
        num, den = {}, {}
        for c, a in crop_areas.items():
            a = float(a or 0.0)
            if a > 0:
                for g, w in sh.get(c, {}).items():
                    num[g] = num.get(g, 0.0) + a * w * float(crop_factor.get(c, 1.0))
                    den[g] = den.get(g, 0.0) + a * w
        return {g: num[g] / den[g] for g in num if den[g] > 0}

    def allocate(self, region: str, crop_areas: Dict[str, float], M: float, E: float, C: float, e_cres: float,
                 crop_factor: Optional[Dict[str, float]] = None, caps=None) -> Optional[dict]:
        """CAPRI's inner model for a model region: group areas from the crop areas, needs at CAPRI's base per ha
        x area x need factor, mineral efficiency and manure availability of the region's CAPRI data, residue
        availability e_cres; distributes M (mineral), E (manure applied), C (arable residue pool), t N."""
        area = self.group_areas(region, crop_areas)
        if not area:
            return None
        me, ea = self.efficiencies(region)
        e = {"MINE": me if me == me else 1.0, "EXCR": ea if ea == ea else 1.0, "CRES": float(e_cres or 1.0)}
        fac = self.group_factors(region, crop_areas, crop_factor) if crop_factor else None
        w = self.base_need_weight(region, area, e, fac)
        out = self.solve(region, area, w, max(M, 0.0), max(E, 0.0), max(C, 0.0), e, caps=caps)
        if out is not None:
            out["area"] = area
            out["e"] = e
        return out

    def _rules(self):
        if not hasattr(self, "_exm"):
            pol = self._root / "2017" / "policy"
            self._exm = pd.read_csv(pol / "mineral_redu_exemptions.csv")
            self._lim = pd.read_csv(pol / "mineral_redu_limcres.csv")
        return self._exm, self._lim

    def mineral_caps(self, region: str, base: dict, reduction: float, year: int = SIM_YEAR) -> Dict[str, float]:
        """CAPRI minfert_redu_by_crop.gms: maximum mineral N per ha of each crop group (kg/ha), from the
        baseline's allocation `base` (allocate() at the baseline): baseline x (1 - reduction); groups below
        30 kg/ha at baseline, and CAPRI's listed (region, group) pairs for the simulation year (othPol not high),
        capped at factor x baseline instead (no backsliding). Groups without mineral N at baseline: no cap."""
        exm, _ = self._rules()
        r = base.get("capri_region") or self.capri_region(region)
        ex = exm[(exm.capri_region == r) & (exm.after_year < year) & (exm.othpol_high == 0)]
        fx = {}
        for t in ex.itertuples(index=False):
            fx[t.ngrp] = float(t.factor)            # later assignments win, as in the GAMS file
        caps = {}
        for (g, s_), v in base["per_ha"].items():
            if s_ != "MINE" or v <= 0:
                continue
            if g in fx:
                caps[g] = fx[g] * v
            elif v < SMALL_MINE_KG_HA:
                caps[g] = v
            else:
                caps[g] = v * (1.0 - reduction)
        return caps

    def limcres_caps(self, region: str, base: dict, year: int = SIM_YEAR) -> Dict[str, Tuple[float, float, float]]:
        """CAPRI's "limCres" regulation with the crop-specific reduction: residues to a group at most
        (1.3 + relaxation) x the baseline's per ha, mode at the baseline, accuracy 10 -> {group: (max, 10,
        1 / (1.3 + relaxation))}."""
        _, lim = self._rules()
        r = base.get("capri_region") or self.capri_region(region)
        add = {}
        for t in lim[(lim.capri_region == r) & (lim.after_year < year)].itertuples(index=False):
            add[t.ngrp] = add.get(t.ngrp, 0.0) + float(t.add)
        out = {}
        for (g, s_), v in base["per_ha"].items():
            if s_ == "CRES" and v > 0:
                f = LIMCRES_FACTOR + add.get(g, 0.0)
                out[g] = (v * f, 10.0, 1.0 / f)
        return out

    def efficiencies(self, region: str) -> Tuple[float, float]:
        """(mineral efficiency, manure availability) of the region in CAPRI's 2030 reference."""
        p = self._pri.get(self.capri_region(region))
        if p is None:
            return 1.0, 1.0
        me = p["mine_eff"].dropna()
        ea = p["excr_avail"].dropna()
        return (float(me.iloc[0]) if len(me) else 1.0), (float(ea.iloc[0]) if len(ea) else 1.0)

    def solve(self, region: str, area: Dict[str, float], need_weight: Dict[str, float], M: float, E: float,
              C: float, e: Dict[str, float], caps: Optional[Dict[Tuple[str, str], float]] = None,
              accuracy: Optional[float] = None, tol: float = 1e-9, max_iter: int = 100) -> Optional[dict]:
        """Distribute M (mineral), E (manure), C (arable residues) in t N over the region's crop groups.

        area: group areas (1000 ha); need_weight: each group's share key of the distributed need (CAPRI's base
        need per ha met by the three sources x area x need factors); e: {"MINE": efficiency, "EXCR":
        availability, "CRES": residue availability}. Group needs N_g = need_weight_g / sum x (e_M M + e_E E +
        e_C C), so the flows add up to the region's totals exactly. caps: {(group, source): max kg N/ha, or
        (max kg N/ha, accuracy, mode / max)} (regulations, CAPRI's beta densities). Returns {"flows": {(g, s): t N}, "per_ha": {(g, s): kg/ha}, "lambda", "mu", "need",
        "converged", "residual"} or None without priors."""
        r = self.capri_region(region)
        if r is None:
            return None
        P = self._pri[r]
        G = [g for g in P.index if float(area.get(g, 0.0)) > 1e-9 and float(need_weight.get(g, 0.0)) > 0]
        if not G:
            return None
        cols = {"MINE": "mine_kg_ha", "EXCR": "excr_kg_ha", "CRES": "cres_kg_ha"}
        # only groups with at least one prior flow can meet a need (set_fert_priors.gms assertion 1)
        G = [g for g in G if any(float(P.at[g, cols[s]]) > 0 and not (s == "CRES" and g in PERM_NGRP) for s in SOURCES)]
        if not G:
            return None
        Ntot = e["MINE"] * M + e["EXCR"] * E + e["CRES"] * C
        W = sum(float(need_weight[g]) for g in G)
        N = {g: float(need_weight[g]) / W * Ntot for g in G}
        # flows with a prior (CAPRI: only where priMode > 0); permanent groups get no arable residues
        F = []
        for g in G:
            for s in SOURCES:
                m = float(P.at[g, cols[s]]) * float(area[g])           # kg/ha x 1000 ha = t
                if s == "CRES" and g in PERM_NGRP:
                    continue
                if m > 1e-9:
                    acc = float(accuracy if accuracy is not None else P.at[g, "accuracy"])
                    al, be = gamma_params(m, acc)
                    cap, b2, a1 = None, 0.0, al - 1.0
                    if caps and (g, s) in caps:
                        # a regulation: max kg/ha, or (max kg/ha, accuracy, mode / max)
                        cv = caps[(g, s)]
                        mx, racc, msh = (float(cv), 0.25, 0.75) if not isinstance(cv, tuple) else map(float, cv)
                        b1, b2_ = beta_regulation(racc, msh)
                        cap = mx * float(area[g])
                        a1, b2 = a1 + (b1 - 1.0), b2_ - 1.0
                    F.append((g, s, a1, be, cap, b2))
        pools = {"EXCR": E, "CRES": C}
        has = {s: any(f[1] == s for f in F) for s in SOURCES}
        # a pool without a receiving flow must be empty; a group without any flow cannot meet its need
        gi = {g: k for k, g in enumerate(G)}
        dual_pools = [s for s in ("EXCR", "CRES") if has[s]]
        nv = len(G) + len(dual_pools)
        z = np.zeros(nv)

        def eval_(z):
            lam = {g: z[gi[g]] for g in G}
            mu = {s: z[len(G) + k] for k, s in enumerate(dual_pools)}
            res = np.zeros(nv)
            J = np.zeros((nv, nv))
            X = {}
            for g, s, a1, be, cap, b2 in F:
                rhs = lam[g] * e[s] - mu.get(s, 0.0)
                x, dx = _flow(a1, be, rhs, cap, b2)
                if not np.isfinite(x):
                    return None
                X[(g, s)] = x
                i = gi[g]
                res[i] += e[s] * x
                J[i, i] += e[s] * dx * e[s]
                if s in mu:
                    k = len(G) + dual_pools.index(s)
                    J[i, k] += e[s] * dx * (-1.0)
                    res[k] += x
                    J[k, i] += dx * e[s]
                    J[k, k] += dx * (-1.0)
            for g in G:
                res[gi[g]] -= N[g]
            for k, s in enumerate(dual_pools):
                res[len(G) + k] -= pools[s]
            return res, J, X

        out = eval_(z)
        scale = np.array([max(N[g], 1.0) for g in G] + [max(pools[s], 1.0) for s in dual_pools])
        converged = False
        for _ in range(max_iter):
            res, J, X = out
            nrm = float(np.max(np.abs(res / scale)))
            if nrm < tol:
                converged = True
                break
            try:
                dz = np.linalg.solve(J, -res)
            except np.linalg.LinAlgError:
                dz = np.linalg.lstsq(J, -res, rcond=None)[0]
            t = 1.0
            while t > 1e-6:
                cand = eval_(z + t * dz)
                if cand is not None and float(np.max(np.abs(cand[0] / scale))) < nrm:
                    break
                t *= 0.5
            if cand is None:
                break
            z = z + t * dz
            out = cand
        res, J, X = out
        per_ha = {k: v / float(area[k[0]]) for k, v in X.items()}
        return {"flows": X, "per_ha": per_ha, "need": N, "converged": converged,
                "residual": float(np.max(np.abs(res / scale))),
                "lambda": {g: float(z[gi[g]]) for g in G},
                "mu": {s: float(z[len(G) + k]) for k, s in enumerate(dual_pools)}, "mineral": M,
                "capri_region": r}

    def base_need_weight(self, region: str, area: Dict[str, float], e: Dict[str, float],
                         factor: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Each group's distributed need at CAPRI's base per hectare (e_M mine + e_E excr + e_C cres, kg/ha) x
        its area x a need factor (square root of the yield change, fertiliser intensity)."""
        P = self._pri.get(self.capri_region(region))
        if P is None:
            return {}
        out = {}
        for g, A in area.items():
            if g not in P.index:
                continue
            per = e["MINE"] * float(P.at[g, "mine_kg_ha"]) + e["EXCR"] * float(P.at[g, "excr_kg_ha"]) \
                + (0.0 if g in PERM_NGRP else e["CRES"] * float(P.at[g, "cres_kg_ha"]))
            out[g] = per * float(A) * float((factor or {}).get(g, 1.0))
        return out
