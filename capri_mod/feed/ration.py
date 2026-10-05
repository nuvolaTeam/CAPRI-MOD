"""EU ration choice — CAPRI's feed PMP, per region and animal (docs/FEED_RATION.md).

For each region and animal activity the ration per head (kg of each feed group
per year) solves

    min  sum_f (p_f + CNST_f) x_f + 1/2 SLOP_f x_f^2
    s.t. energy  e.x  >= E          protein  cp.x >= P
         DMIN <= dm.x <= DMAX       x >= 0

at the current feed prices p, as in CAPRI's supply models (REQSN_/REQSE_,
MINSHR_/MAXSHR_; feed PMP in pmp_terms/define_const_pmp_param.gms, Part I).

Calibration, so the OBSERVED base ration is exactly optimal at base prices:
  * requirements trimmed to the data (CAPRI p_trimFeed): each bound is widened
    just enough to contain the base ration;
  * SLOP_f = (1/|eps_f|) x max(p_f, 10% of the cereal price) / x_ref_f, with
    CAPRI's assumed feed elasticities (supply/pmp_elas.gms): fodder and cereals
    -10, protein-rich -5, other -1, energy-rich, milk feeds and straw -0.5.
    x_ref_f = the base feeding. (CAPRI: at least 10% of the sector's dry-matter
    share - identical for feeds with >= 10% of dry matter; REGISTERED.)
  * CNST_f from the first-order conditions at base with nutrient shadow prices
    lambda >= 0 fitted to the feed prices (non-negative least squares over the
    constraints that bind at base) - standing in for the duals of CAPRI's
    calibration step (REGISTERED).
Feeds with no assumed elasticity in CAPRI (FRMI, FPRI, FENI) have no PMP term
there; here they are held at their base quantity.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

#: CAPRI supply/pmp_elas.gms: FODDI (incl. straw, overridden) and named feeds
FEED_ELAS = {"FGRA": -10.0, "FMAI": -10.0, "FOFA": -10.0, "FROO": -10.0, "FCOM": -10.0,
             "FSGM": -10.0, "FCER": -10.0, "FPRO": -5.0, "FOTH": -1.0, "FENE": -0.5,
             "FMIL": -0.5, "FSTR": -0.5}
#: CAPRI's FIXED feed-share rules on a DRY-MATTER basis (feed/req_or_man_fnc.gms,
#: 'Define maximum and minimum share of feed stuffs'), mapped to model animals:
#: (min, max) share of each feed's dry matter in the CURRENT total intake.
#: Ruminants: protein <= 0.3, energy-rich <= 0.1; dairy cows, fattening bulls,
#: calves: cereals >= 0.2, protein >= 0.1; heifers cereals and protein >= 0.05;
#: suckler cows cereals >= 0.05; non-ruminants: cereals >= 0.6, protein <= 0.2
#: (sows 0.3 - pigs here are sows + fattening, 0.2 used, REGISTERED), energy-rich
#: 0.05-0.15, no fodder; other feeds >= 0.005 (0.001 sheep, suckler cows).
#: NOT YET: CAPRI's data-driven rules - maximum 'other' feed share from member-
#: state feed balances, minimum fibre-rich (fodder) shares from regional fodder
#: energy shares (REGISTERED, pending).
_RUMI = ("DCOW", "BCOW", "BULL", "HFRS", "CALV", "SHGP")
_NRUMI = ("PIGS", "BROI", "LAYS")
_FODDI = ("FGRA", "FMAI", "FOFA", "FROO", "FCOM", "FSGM", "FSTR")


_FIBRE = ("FOFA", "FGRA", "FMAI")              # CAPRI fibreRichFeed (without straw)
#: CAPRI factor x regional fodder-energy share = minimum share of each fibre feed;
#: the model's calves (raising + fattening: 0.4 / 0.2) and sheep and goats
#: (milk + fattening: 0.8 / 0.5) take the mean factor (REGISTERED)
_FIBRE_FACTOR = {"DCOW": 0.6, "BCOW": 0.9, "BULL": 0.5, "HFRS": 0.6, "CALV": 0.3, "SHGP": 0.65}


def share_rules(act: str, ctx: dict | None = None) -> dict:
    """feed -> (min share, max share) of dry matter in the current total intake.

    CAPRI feed/req_or_man_fnc.gms, 'Define maximum and minimum share of feed
    stuffs'. ``ctx`` carries the data-driven inputs: 'fibre_share' (feed ->
    share of the region's fodder energy supply), 'straw' (straw produced),
    'foth_max' (member-state rule for other feeds).
    """
    ctx = ctx or {}
    r = {}
    def setr(f, lo=None, hi=None):
        a, b = r.get(f, (0.0, 1.0))
        r[f] = (a if lo is None else lo, b if hi is None else hi)
    if act in _RUMI:
        setr("FPRO", hi=0.3); setr("FENE", hi=0.1)
    if act in _NRUMI:
        setr("FPRO", hi=0.2); setr("FCER", lo=0.6); setr("FENE", lo=0.05, hi=0.15)
        for f in _FODDI:
            setr(f, hi=0.0)
    if act in ("DCOW", "BULL", "CALV"):
        setr("FCER", lo=0.20); setr("FPRO", lo=0.10)
    if act == "HFRS":
        setr("FCER", lo=0.05); setr("FPRO", lo=0.05)
    if act == "BCOW":
        setr("FCER", lo=0.05)
    setr("FOTH", lo=0.001 if act in ("SHGP", "BCOW") else 0.005)
    # --- data-driven rules
    fs = ctx.get("fibre_share") or {}
    if act in _FIBRE_FACTOR and fs:
        for f in _FIBRE:
            if fs.get(f, 0.0) > 0:
                setr(f, lo=_FIBRE_FACTOR[act] * fs[f])
    if act in _RUMI and ctx.get("straw"):
        setr("FSTR", lo=0.01, hi=0.05)
    if act == "SHGP":
        for f in ("FCER", "FPRO", "FENE", "FOTH", "FMIL", "FROO", "FSTR", "FCOM"):
            a, b = r.get(f, (0.0, 1.0)); r[f] = (a, min(b, 0.20))
    if act == "CALV":
        setr("FMIL", lo=0.05); setr("FCOM", lo=0.10, hi=1.0)
    elif act in ("BULL", "HFRS"):
        setr("FCOM", hi=0.01)
    elif act in ("DCOW", "BCOW"):
        setr("FCOM", hi=0.0)
    if act != "SHGP":
        setr("FSGM", hi=0.0)
    fm = ctx.get("foth_max")
    if fm:
        setr("FOTH", hi=min(1.0, fm * (2.0 if act in _RUMI else 1.0)))
    return r


#: feed groups whose price follows a market: cereals -> cereal mix, protein -> cakes
MARKET_FEEDS = ("FCER", "FPRO")


def _nnls(A: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Small non-negative least squares (Lawson-Hanson) - no scipy dependency."""
    n = A.shape[1]
    x = np.zeros(n)
    P = np.zeros(n, dtype=bool)
    for _ in range(50):
        w = A.T @ (b - A @ x)
        if P.all() or w[~P].max(initial=-1.0) <= 1e-12:
            break
        j = int(np.argmax(np.where(P, -np.inf, w)))
        P[j] = True
        while True:
            z = np.zeros(n)
            z[P] = np.linalg.lstsq(A[:, P], b, rcond=None)[0]
            if (z[P] > 0).all():
                x = z
                break
            neg = P & (z <= 0)
            alpha = np.min(x[neg] / (x[neg] - z[neg]))
            x = x + alpha * (z - x)
            P &= x > 1e-12
    return x


class Ration:
    """One region-animal ration problem, calibrated to its base."""

    def __init__(self, rec: dict, cereal_price: float):
        self.feeds = list(rec["ration"])
        x0 = np.array([rec["ration"][f] for f in self.feeds])
        e = np.array([rec["content"][f]["ENNE"] for f in self.feeds])
        cp = np.array([rec["content"][f]["CRPR"] for f in self.feeds])
        dm = np.array([rec["content"][f]["DRMA"] for f in self.feeds])
        p0 = np.array([rec["price"][f] for f in self.feeds])
        flex = np.array([f in FEED_ELAS for f in self.feeds])
        self.x0, self.p0, self.flex = x0, p0, flex
        E0, P0, D0 = e @ x0, cp @ x0, dm @ x0
        req = rec["req"]
        # trimmed requirements (CAPRI p_trimFeed): the base ration is feasible
        self.E = min(req["ENNE"], E0)
        self.P = min(req["CRPR"], P0)
        self.DMIN = (req["DMIN"] if req["DMIN"] <= D0 else D0 * (1 - 1e-6)) if req["DMIN"] > 0 else 0.0
        self.DMAX = (req["DMAX"] if req["DMAX"] >= D0 else D0 * (1 + 1e-6)) if req["DMAX"] > 0 else np.inf
        self.e, self.cp, self.dm = e, cp, dm
        # share bounds, trimmed to the base ration (CAPRI's corrector factor):
        # a bound the observed ration violates is widened to the base share
        self.shares = []
        act = rec.get("_act")
        if act and D0 > 0:
            for f, (lo, hi) in share_rules(act, rec.get("_ctx")).items():
                if f not in self.feeds:
                    continue
                i = self.feeds.index(f)
                s0 = dm[i] * x0[i] / D0
                # widened by a tiny relative margin when trimmed to the base
                # (CAPRI's corrector widens by a tolerance): bounds pinned exactly
                # at base shares bound redundantly with the nutrient constraints
                # and made the KKT system singular (pigs: 5 active on 3 feeds)
                lo_e = lo if lo <= s0 else s0 * (1 - 1e-6)
                hi_e = hi if hi >= s0 else s0 * (1 + 1e-6)
                if lo_e > 0:
                    self.shares.append((i, "min", lo_e))
                if hi_e < 1.0:
                    self.shares.append((i, "max", hi_e))
        # feed PMP slope
        eps = np.array([abs(FEED_ELAS.get(f, 1.0)) for f in self.feeds])
        peff = np.maximum(p0, 0.1 * cereal_price)
        xref = np.maximum(x0, 1e-9)
        own = peff / (eps * xref)
        # CAPRI's OWN calibrated slope where available (pmppar p_pmpFeedInpCoeff,
        # aggregated by tools/build_feed_ration.py); the reconstruction of its
        # formula above is the fallback
        cs = rec.get("capri_slope", {})
        capri = np.array([float(cs.get(f, 0.0)) for f in self.feeds])
        self.slope_source = np.where(capri > 0, "capri", "formula")
        self.slope = np.where(flex, np.where(capri > 0, capri, own), 0.0)
        # nutrient shadow prices: NNLS over constraints binding at base
        tol = 1e-9
        rows, idx = [], []
        if E0 <= self.E * (1 + tol) and self.E > 0:
            rows.append(e); idx.append("E")
        if P0 <= self.P * (1 + tol) and self.P > 0:
            rows.append(cp); idx.append("P")
        if self.DMIN > 0 and D0 <= self.DMIN * (1 + tol):
            rows.append(dm); idx.append("DMIN")
        lam = np.zeros(len(rows))
        if rows and flex.any():
            A = np.array(rows).T[flex]
            lam = _nnls(A, p0[flex])
        self.lam = dict(zip(idx, lam))
        shadow = sum(self.lam.get(k, 0.0) * v for k, v in (("E", e), ("P", cp), ("DMIN", dm)))
        # CNST from the first-order conditions at base: p + CNST + SLOP x0 = shadow
        self.cnst = np.where(flex, shadow - p0 - self.slope * x0, 0.0)

    def solve(self, price: np.ndarray):
        """Ration at feed prices ``price`` (aligned with self.feeds)."""
        from capri_mod.supply.qp_solver import solve_qp
        fl = self.flex
        if not fl.any():
            return self.x0.copy(), True
        fixed = ~fl
        # requirements net of the fixed feeds
        E = self.E - self.e[fixed] @ self.x0[fixed]
        P = self.P - self.cp[fixed] @ self.x0[fixed]
        Dlo = self.DMIN - self.dm[fixed] @ self.x0[fixed]
        Dhi = self.DMAX - self.dm[fixed] @ self.x0[fixed]
        Q = np.diag(self.slope[fl])
        c = price[fl] + self.cnst[fl]
        A, b = [-self.e[fl], -self.cp[fl]], [-E, -P]
        if self.DMIN > 0:
            A.append(-self.dm[fl]); b.append(-Dlo)
        if np.isfinite(Dhi):
            A.append(self.dm[fl]); b.append(Dhi)
        # share constraints on dry matter: dm_i x_i >= lo * sum dm x  /  <= hi * sum dm x
        for i, kind, v in self.shares:
            row = -v * self.dm.copy()
            row[i] += self.dm[i]                  # dm_i x_i - v * sum dm x
            if kind == "min":
                row = -row                        # v * sum dm x - dm_i x_i <= 0
            const = row[fixed] @ self.x0[fixed]
            A.append(row[fl]); b.append(-const)
        A, b = np.array(A), np.array(b)
        xf, ok = solve_qp(Q, c, A, b, x0=self.x0[fl])
        if not ok:
            # fallback, as in the supply model: a general solver when the compact
            # active-set method cannot factor a degenerate working set (several
            # share and nutrient constraints binding together)
            from scipy.optimize import minimize
            res = minimize(lambda z: c @ z + 0.5 * z @ Q @ z, self.x0[fl],
                           jac=lambda z: c + Q @ z, method="SLSQP",
                           bounds=[(0.0, None)] * int(fl.sum()),
                           constraints=[{"type": "ineq", "fun": lambda z: b - A @ z, "jac": lambda z: -A}],
                           options={"maxiter": 500, "ftol": 1e-12})
            z = res.x
            scale = np.maximum(np.abs(b), 1.0)
            if res.success and np.all(A @ z - b <= 1e-6 * scale) and np.all(z >= -1e-9):
                xf, ok = np.maximum(z, 0.0), True
        x = self.x0.copy()
        if ok:
            x[fl] = xf
        return x, ok

    def cost(self, x: np.ndarray, price: np.ndarray) -> float:
        """Feed cost per head incl. the PMP terms (CAPRI's objective contribution)."""
        return float(price @ x + self.cnst @ x + 0.5 * (self.slope * x) @ x)


class RationModel:
    """All EU region-animal rations, from feed_ration_2017.json."""

    def __init__(self, data_dir: str | Path = None):
        root = Path(data_dir) if data_dir else Path(__file__).resolve().parents[2] / "capri_data"
        f = root / "2017" / "feed" / "feed_ration_2017.json"
        raw = json.load(open(f))["regions"] if f.exists() else {}
        self.rations = {}
        ctx = self._contexts(root, raw)
        for reg, acts in raw.items():
            for act, rec in acts.items():
                pc = float(rec["price"].get("FCER", 0.0)) or 0.2
                rec = dict(rec, _act=act, _ctx=ctx.get(reg))
                self.rations[(reg, act)] = Ration(rec, pc)

    @staticmethod
    def _contexts(root, raw) -> dict:
        """Per-region inputs of CAPRI's data-driven share rules.

        fibre_share: each fibre feed's share of the region's fodder ENERGY
        supply. CAPRI uses fodder production (GROF x ENNE); fodder is not
        traded, so regional production = regional use = herds x rations.
        foth_max: 5 x the member state's dry-matter share of other feeds in
        total feed dry matter excluding straw (CAPRI: DCOW rule applied to all).
        """
        import pandas as pd
        try:
            herds = pd.read_csv(Path(root) / "2017" / "supply" / "animal_numbers.csv", index_col=0)
        except Exception:
            return {}
        out, ms_dm, ms_foth = {}, {}, {}
        for reg, acts in raw.items():
            en = {f: 0.0 for f in _FIBRE}
            straw = False
            for act, rec in acts.items():
                h = float(herds.at[reg, act]) if reg in herds.index and act in herds.columns else 0.0
                for f, x in rec["ration"].items():
                    if f in _FIBRE:
                        en[f] += h * x * rec["content"][f]["ENNE"]
                    if f == "FSTR" and x > 0:
                        straw = True
                    dmv = h * x * rec["content"][f]["DRMA"]
                    cc = reg[:2]
                    if f != "FSTR":
                        ms_dm[cc] = ms_dm.get(cc, 0.0) + dmv
                    if f == "FOTH":
                        ms_foth[cc] = ms_foth.get(cc, 0.0) + dmv
            tot = sum(en.values())
            out[reg] = {"fibre_share": {f: v / tot for f, v in en.items()} if tot > 0 else {}, "straw": straw}
        for reg in out:
            cc = reg[:2]
            if ms_dm.get(cc, 0.0) > 0 and ms_foth.get(cc, 0.0) > 0:
                out[reg]["foth_max"] = 5.0 * ms_foth[cc] / ms_dm[cc]
        return out

    def price_vector(self, key, cereal_index: float = 1.0, protein_index: float = 1.0):
        """Feed prices for one ration: base prices with the market feed groups
        scaled by the cereal-mix and cake price indices (others unchanged:
        on-farm fodder and feeds without a market here - REGISTERED)."""
        r = self.rations[key]
        p = r.p0.copy()
        for i, f in enumerate(r.feeds):
            if f == "FCER":
                p[i] *= cereal_index
            elif f == "FPRO":
                p[i] *= protein_index
        return p
