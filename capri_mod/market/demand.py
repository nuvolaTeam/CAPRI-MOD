"""MarketModule: human consumption (the Generalised Leontief food demand system and the demand response).

Part of capri_mod.market.market_module.MarketModule (a mixin); moved out of market_module.py on 24 October 2026
without changing the code. CAPRI references are in the methods' docstrings."""

import numpy as np
import pandas as pd
from scipy.optimize import fsolve  # noqa: F401
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple

from capri_mod.params import param, param_table
from capri_mod.settings import setting, current as _settings
from capri_mod.data.definitions import (
    MARKET_COMMODITIES, ALL_TRADE_REGIONS,
)
from capri_mod.data.definitions import MS_CODE
from capri_mod.market.equilibrium import MarketEquilibrium  # noqa: F401
from capri_mod.market.state import MarketStateMixin


class DemandMixin(MarketStateMixin):
    """MarketModule methods for human consumption (the Generalised Leontief food demand system and the demand response)."""


    #: Human consumption from CAPRI's Generalised Leontief demand system (arm/market_model.gms:826-916) per
    #: behavioural region (EU member states, non-EU countries and country groups), with its cross-price and income
    #: terms; parameters from CAPRI's 2030 calibration (tools/build/build_gl_demand.py)

    def _gl_params(self) -> dict:
        """CAPRI's GL food demand per behavioural region, grouped by model region.

        Returns {model region: [rms entries]} with, per CAPRI region: goods' model commodity column (-1: a good the
        model has no market for; its price stays at CAPRI's, as INPE's), d, B (symmetric), consumer prices at the
        calibration point (EUR/kg), income per head Y, inhabitants; plus "hs": (region, commodity) -> CAPRI's human
        consumption share of total use, and "x0": the demand at the calibration point per (region, commodity)."""
        cached = getattr(self, "_gl_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            inp = self._inp()
            goods = inp.csv("gl_demand_goods.csv", keep_default_na=False, na_values=[""])
            bb = inp.csv("gl_demand_b.csv")
            regs = inp.csv("gl_demand_regions.csv").set_index("rms")
            Cc = {c: j for j, c in enumerate(self.commodities)}
            Rr = {r: i for i, r in enumerate(self.regions)}
            groups, hcon, use, x0 = {}, {}, {}, {}
            bgr = {r: g for r, g in bb.groupby("rms")}
            for rms, g in goods.groupby("rms", sort=True):
                mr = str(g["model_region"].iloc[0])
                if mr == "EU27" and self.eu_blocks:
                    mr = self.eu_region_of_ms(rms) or mr
                if mr not in Rr or rms not in regs.index or rms not in bgr:
                    continue
                names = list(g["good"])
                idx = {n: k for k, n in enumerate(names)}
                n = len(names)
                B = np.zeros((n, n))
                for i_, j_, v in bgr[rms][["i", "j", "b"]].itertuples(index=False):
                    if i_ in idx and j_ in idx:
                        B[idx[i_], idx[j_]] = v
                        B[idx[j_], idx[i_]] = v
                p0 = g["cpri"].to_numpy(dtype=float) / 1000.0
                if not np.all(p0 > 0):
                    continue
                col = np.array([Cc.get(str(m), -1) if isinstance(m, str) and m else -1
                                for m in g["model_commodity"]], dtype=int)
                # CAPRI's consumer price moves with the Armington price of the region's market region (Cpri_ =
                # Arm1P + margins, market_model.gms l. 3032-3039): the change is ARM1P x (price ratio - 1)
                a1 = g["arm1p"].to_numpy(dtype=float) / 1000.0
                if np.any((col >= 0) & ~(a1 > 0)):
                    raise ValueError(f"gl_demand_goods.csv: no CAPRI Armington price (arm1p) for "
                                     f"{rms} {list(np.array(names)[(col >= 0) & ~(a1 > 0)])}")
                e = {"col": col, "d": g["d"].to_numpy(dtype=float), "B": B, "p0": p0, "arm1p": a1,
                     "Y": float(regs.at[rms, "Y"]), "inha": float(regs.at[rms, "inha"]), "rms": rms,
                     "good": np.array(names), "hcon": g["hcon"].to_numpy(dtype=float),
                     "use": g["use"].to_numpy(dtype=float)}
                e["d_cal"] = e["d"].copy()
                e["x0"] = self._gl_eval(e, p0, 1.0)
                groups.setdefault(mr, []).append(e)
                for k, j in enumerate(col):
                    if j < 0:
                        continue
                    key = (mr, int(j))
                    hcon[key] = hcon.get(key, 0.0) + float(g["hcon"].iloc[k])
                    use[key] = use.get(key, 0.0) + float(g["use"].iloc[k])
                    x0[key] = x0.get(key, 0.0) + float(e["x0"][k])
            out = {"groups": groups,
                   "hs": {k: min(1.0, hcon[k] / use[k]) for k in hcon if use[k] > 0 and hcon[k] > 0},
                   "x0": x0, "x0_cal": dict(x0), "use": use}
        except Exception as exc:
            raise RuntimeError(f"market: the GL food demand inputs could not be read ({exc!r})") from exc
        self._gl_cache = out
        return out

    @staticmethod
    def _gl_eval(e: dict, p: np.ndarray, ir: float) -> np.ndarray:
        """CAPRI's GL demand of one region (1000 t): x_i = [G_i/G (Y - F) + d_i] INHA / 1000."""
        sq = np.sqrt(p)
        G = float(sq @ e["B"] @ sq)
        Gi = (e["B"] @ sq) / sq
        F = float(e["d"] @ p)
        return (Gi / G * (e["Y"] * ir - F) + e["d"]) * e["inha"] / 1000.0

    #: CAPRI's re-calibration of the GL commitments to given quantities and prices (arm/recalibrate_commitments.gms,
    #: trim_gl_commits.gms): the commitments d are moved as little as possible (least squares) so that the system
    #: reproduces the model's base human consumption at the calibration prices; b and income stay. The model's base
    #: use per region and commodity sets the target: CAPRI's human consumption of each behavioural region scaled by
    #: the ratio of the model's base use to CAPRI's use of the model region.

    def _gl_refit(self, D0c: np.ndarray) -> None:
        """Re-fit the commitments of every behavioural region to the model's base use D0c (regions x commodities),
        as CAPRI's m_trimGLCommits: min sum (d - d_CAPRI)^2 s.t. x_i(p0, d) = target_i for the goods with human
        consumption (raw milk and INPE free; INPE absorbs the change in spending). The constraints are linear in d:
        d_i - a_i sum_k p_k d_k = q_i - a_i Y, a_i = G_i / G, so the least-squares solution is exact."""
        prm = self._gl_params()
        Rr = {r: i for i, r in enumerate(self.regions)}
        kfac = {}
        for (mr, j), u in prm["use"].items():
            if u > 0:
                kfac[(mr, j)] = float(D0c[Rr[mr], j]) / u
        info = []
        x0 = {}
        for mr, ents in prm["groups"].items():
            i = Rr[mr]
            for e in ents:
                p, d0, col = e["p0"], e["d_cal"], e["col"]
                sq = np.sqrt(p)
                G = float(sq @ e["B"] @ sq)
                a = (e["B"] @ sq) / sq / G
                k = np.array([kfac.get((mr, int(j)), 1.0) if j >= 0 else 1.0 for j in col])
                q = e["hcon"] * k * 1000.0 / e["inha"]                      # per head, kg
                con = (e["hcon"] > 1e-6) & (np.abs(a) > 0) & (e["good"] != "INPE") & (e["good"] != "MILK")
                A = np.where(con[:, None], -np.outer(a, p), 0.0)[con]
                A[np.arange(con.sum()), np.where(con)[0]] += 1.0
                b = (q - a * e["Y"])[con]
                r = b - A @ d0
                d = d0 + A.T @ np.linalg.solve(A @ A.T, r)
                e["d"] = d
                x = self._gl_eval(e, p, 1.0)
                e["x0"] = x
                err = float(np.max(np.abs(x[con] - (q * e["inha"] / 1000.0)[con]) / np.maximum(1e-9, x[con]))) if con.any() else 0.0
                info.append((e["rms"], mr, err, float(np.max(np.abs(d - d0)[con] / np.maximum(np.abs(d0[con]), 1e-9))) if con.any() else 0.0))
                for kk, j in enumerate(col):
                    if j >= 0:
                        x0[(mr, int(j))] = x0.get((mr, int(j)), 0.0) + float(x[kk])
        prm["x0"] = x0
        self.gl_refit_info = info

    def gl_food_ratio(self, PR: np.ndarray, ref: np.ndarray, ir: float = 1.0, D0c: np.ndarray = None):
        """Human consumption relative to the calibration point per (model region, commodity), and CAPRI's human
        consumption share of use. Consumer prices move additively with the Armington price (CAPRI Cpri_: Armington
        price + margins, market_model.gms l. 3032-3039): p = CPRI0 + (PR - 1) x ARM1P0, PR the region's Armington
        price ratio, ARM1P0 CAPRI's Armington price of the CAPRI region's market region at the calibration point.
        (Until 24 October 2026 the change was formed on the model's base world price x (1 + AVE), `ref`; audit M1.)
        `ref` is kept in the signature for the callers."""
        prm = self._gl_params()
        if not prm:
            return None, None
        if D0c is not None:
            key = getattr(self, "_gl_refit_key", None)
            if key is None or key.shape != D0c.shape or not np.array_equal(key, D0c):
                self._gl_refit(D0c)
                self._gl_refit_key = D0c.copy()
        Rr = {r: i for i, r in enumerate(self.regions)}
        num = np.zeros_like(PR, dtype=float)
        for mr, ents in prm["groups"].items():
            i = Rr[mr]
            for e in ents:
                col = e["col"]
                p = e["p0"].copy()
                m = col >= 0
                p[m] = p[m] + (PR[i, col[m]] - 1.0) * e["arm1p"][m]
                p = np.maximum(p, 0.05 * e["p0"])
                x = self._gl_eval(e, p, ir)
                np.add.at(num[i], col[m], np.maximum(x[m], 0.0))
        GLR = np.ones_like(num)
        HS = np.zeros_like(num)
        for (mr, j), v0 in prm["x0"].items():
            i = Rr[mr]
            if v0 > 0:
                GLR[i, j] = num[i, j] / v0
                HS[i, j] = prm["hs"].get((mr, j), 0.0)
        return GLR, HS

    def _use_components(self) -> dict:
        """CAPRI's split of each region's Armington use into its four components (ArmBal1_, market_model.gms
        l. 2602-2620; use_components.csv, tools/build/build_use_components.py): {(region, commodity): {"hcon", "feed",
        "proc", "biof"}} as shares of their sum, summed over the region's behavioural regions."""
        cached = getattr(self, "_usecomp_cache", None)
        if cached is not None:
            return cached
        t = self._inp().csv("use_components.csv")
        tot = {}
        for r in t.itertuples(index=False):
            R = r.model_region
            if R == "EU27" and self.eu_blocks:
                R = self.eu_region_of_ms(r.rms) or R
            if R not in self.regions or r.commodity not in self.commodities:
                continue
            d = tot.setdefault((R, r.commodity), {"hcon": 0.0, "feed": 0.0, "proc": 0.0, "biof": 0.0})
            d["hcon"] += float(r.hcon_kt); d["feed"] += float(r.feed_kt)
            d["proc"] += float(r.proc_kt); d["biof"] += float(r.biof_kt)
        out = {}
        for k, d in tot.items():
            s = sum(d.values())
            if s > 0:
                out[k] = {x: v / s for x, v in d.items()}
        self._usecomp_cache = out
        return out

    def demand_response(
        self,
        domestic_prices: pd.DataFrame,
        world_prices: pd.Series,
    ) -> pd.DataFrame:
        """Use per region and commodity (1000 t), CAPRI's Armington balance ArmBal1_ (market_model.gms
        l. 2602-2620): human consumption + feed + processing + biofuel processing, each with its own equation where
        CAPRI has one and fixed at its base where CAPRI has none.

        Base: the calibrated base use (base_consumption x the demand calibration factor), split by CAPRI's 2030
        component shares (_use_components).
          human consumption  CAPRI's GL demand per behavioural region (gl_food_ratio; Cpri_ on ARM1P)
          feed               EU: the member states' feed bulks (feedBlkPrice_, feedShareEqu_) and the FMIL block for
                             dairy products; Norway: its bulks; other regions: p_ElasFeed (FeedNQ_ not yet ported,
                             docs/design/ARCHITECTURE_REFACTOR.md 5.1 M3) and the FMIL block for dairy products
          processing         oilseeds: crushing (_crush_state); other products: ProcNQ_ (H x ARM1P0 x (ratio - 1)) with
                             ProcFudge_; the dairy products' processing stays fixed for now (CAPRI has ProcNQ_ terms
                             for them; audit M9, open)
          biofuel            the biofuel feedstock CES at the biofuel output
          raw milk           EU and Norway: the milk delivered to their dairies (not traded)
          biofuels' own use  the biofuel market block
        A cell without CAPRI components keeps its base (no generic elasticity: the eta column of
        armington_params.csv and the FAO_agg elasticities are no longer used; until 24 October 2026 about 12% of use
        responded through them, audit M2, K72).
        """
        R = {r: i for i, r in enumerate(self.regions)}
        Cc = {c: j for j, c in enumerate(self.commodities)}
        nR, nC = len(self.regions), len(self.commodities)
        wp0 = pd.Series({c: max(float(self.world_prices_base[c]), 0.01) for c in self.commodities})
        fallback = pd.Series({c: float(world_prices.get(c, self.world_prices_base[c])) for c in self.commodities})
        dp = domestic_prices.reindex(index=self.regions, columns=self.commodities)
        _dv = dp.to_numpy(dtype=float)
        if np.isnan(_dv).any():
            dp = pd.DataFrame(np.where(np.isnan(_dv), fallback.reindex(self.commodities).to_numpy(dtype=float)[None, :],
                                       _dv), index=dp.index, columns=dp.columns)
        dom0 = self._dom0()
        ref = dom0.reindex(index=self.regions, columns=self.commodities)
        ref = ref.where(ref > 0).fillna(pd.DataFrame({c: [wp0[c]] * nR for c in self.commodities}, index=self.regions))
        PR = (dp / ref).to_numpy(dtype=float)                           # Armington price ratios
        DPv = dp.to_numpy(dtype=float)
        REFv = ref.to_numpy(dtype=float)
        cal = np.array([float(self._demand_cal_factor(c)) for c in self.commodities])
        Bv = self.par.base_consumption.reindex(index=self.regions, columns=self.commodities).fillna(0.0).to_numpy(dtype=float)
        D0 = Bv * cal[None, :]                                          # calibrated base use

        # base components (kt) from CAPRI's shares
        uc = self._use_components()
        H0, F0, P0, Bf0 = (np.zeros((nR, nC)) for _ in range(4))
        for (r, c), s in uc.items():
            i, j = R.get(r), Cc.get(c)
            if i is None or j is None:
                continue
            H0[i, j], F0[i, j], P0[i, j], Bf0[i, j] = (D0[i, j] * s[x] for x in ("hcon", "feed", "proc", "biof"))
        FIX = D0 - H0 - F0 - P0 - Bf0                                   # cells without CAPRI components: fixed
        H, F, P, Bf = H0.copy(), F0.copy(), P0.copy(), Bf0.copy()

        # HUMAN CONSUMPTION: CAPRI's GL system
        GLR, HS = self.gl_food_ratio(PR, REFv, 1.0, D0c=D0)
        if GLR is not None:
            m = H0 > 0
            H[m] = H0[m] * GLR[m]
        self._gl_last = (GLR, HS) if GLR is not None else None

        # FEED
        fb = self._feed_bulk_params()
        fdp = self._feed_demand_params()
        for (r, c), prm in (fdp or {}).items():                      # other regions: p_ElasFeed (M3 open)
            i, j = R.get(r), Cc.get(c)
            if i is None or j is None or F0[i, j] <= 0:
                continue
            ft = 1.0
            for jn, e in prm["elasticities"].items():
                jj = Cc.get(jn)
                if jj is not None and REFv[i, jj] > 0:
                    ft *= (DPv[i, jj] / REFv[i, jj]) ** e
            F[i, j] = F0[i, j] * ft
        self._eu_feed_now = None
        self.ev.eu_feed_now_reg = {}
        for _reg in self.EU:
            ie = R.get(_reg)
            if ie is None or not fb:
                continue
            f0r = fb["feed0_reg"].get(_reg, {})
            feed = self.eu_feed_use({c: float(PR[ie, Cc[c]]) for c in fb["feed0"] if c in Cc},
                                    region=_reg if self.eu_blocks else None)
            self.ev.eu_feed_now_reg[_reg] = feed
            if not self.eu_blocks:
                self._eu_feed_now = feed
            for c, q in feed.items():
                j = Cc.get(c)
                f0 = float(f0r.get(c, 0.0))
                if j is not None and f0 > 0 and F0[ie, j] > 0:
                    F[ie, j] = F0[ie, j] * q / f0
        self.ev.sup_feed_now = {}
        _dairy_cs = set(self.DAIRY_TRADED.values())
        for _reg in self.SUP:
            i = R.get(_reg)
            if i is None or not fb or _reg not in (self.ev.sup_active or ()):
                continue
            f0r = (fb.get("feed0_sup") or {}).get(_reg, {})
            feed = self.sup_feed_use(_reg, {c: float(PR[i, Cc[c]]) for c in f0r if c in Cc})
            self.ev.sup_feed_now[_reg] = feed
            for c, q in feed.items():
                j = Cc.get(c)
                f0 = float(f0r.get(c, 0.0))
                if j is not None and f0 > 0 and F0[i, j] > 0 and c not in _dairy_cs:
                    F[i, j] = F0[i, j] * q / f0
        # dairy products fed (FMIL block): EU per market region, non-EU dairy regions
        _P9 = list(self.DAIRY_PRODUCTS)
        if self._dairy_params():
            for _reg in self.EU:
                ie = R.get(_reg)
                if ie is None:
                    continue
                _dl = self.ev.dairy_last or {}
                _rho = np.array([float(PR[ie, Cc[self.DAIRY_TRADED[k]]]) if self.DAIRY_TRADED[k] in Cc
                                 else float((_dl.get("price_ratio") or {}).get(k, 1.0)) for k in _P9])
                _feed = self.dairy_feed_factor(np.maximum(_rho, 0.05))
                _fn = self.ev.eu_feed_now_reg.get(_reg) or {}
                _f0 = (fb or {}).get("feed0_reg", {}).get(_reg, {}) if fb else {}
                for kk, k in enumerate(_P9):
                    c = self.DAIRY_TRADED[k]
                    j = Cc.get(c)
                    if j is None or F0[ie, j] <= 0:
                        continue
                    f = float(_fn[c]) / float(_f0[c]) if (c in _fn and float(_f0.get(c, 0.0)) > 0) else float(_feed[kk])
                    F[ie, j] = F0[ie, j] * f
        _wpar = self._dairy_world_params()
        for _r, _prm in (_wpar or {}).items():
            i = R.get(_r)
            if i is None:
                continue
            _rho = np.maximum(np.array([float(PR[i, Cc[self.DAIRY_TRADED[k]]]) if self.DAIRY_TRADED[k] in Cc else 1.0
                                        for k in _P9]), 0.05)
            _feed = self.dairy_feed_factor(_rho, _prm, 1.0)
            _fs = self.ev.sup_feed_now.get(_r)
            if _fs:
                _f0s = (fb.get("feed0_sup") or {}).get(_r, {})
                for k, c in self.DAIRY_TRADED.items():
                    if c in _fs and float(_f0s.get(c, 0.0)) > 0:
                        _feed[_P9.index(k)] = float(_fs[c]) / float(_f0s[c])
            for kk, k in enumerate(_P9):
                j = Cc.get(self.DAIRY_TRADED[k])
                if j is not None and F0[i, j] > 0:
                    F[i, j] = F0[i, j] * float(_feed[kk])

        # PROCESSING: crushing and ProcNQ_
        cp = self._crush_params()
        if cp:
            _cpn = self.ev.crush_prices_now
            crush = self.crush_quantities(_cpn if _cpn is not None else dp)
            for (r, sd), q in crush.items():
                i, j = R.get(r), Cc.get(sd)
                if i is None or j is None:
                    continue
                P[i, j] = max(0.0, P0[i, j] + (q - cp[(r, sd)]["q0"]))
        pq = self._proc_nq_params()
        if pq:
            for (reg, c), _shp in pq["share"].items():
                i, j = R.get(reg), Cc.get(c)
                if i is None or j is None or c in self.CRUSH_CHAINS or c in self._PROC_NQ_SKIP or P0[i, j] <= 0:
                    continue
                Hra = pq["Ha"].get(reg, {})
                dq = 0.0
                for (x, y), hv in Hra.items():
                    if x != c:
                        continue
                    jy = Cc.get(y)
                    if jy is not None and y not in self.CRUSH_CHAINS and REFv[i, jy] > 0:
                        dq -= hv * (DPv[i, jy] / REFv[i, jy] - 1.0)
                P[i, j] = self._proc_fudge(P0[i, j] + dq, P0[i, j])

        # BIOFUEL PROCESSING (feedstocks)
        bp = self._biofuel_params()
        self.ev.eu_biof_ratio = {}
        if bp:
            for reg in sorted({g["region"] for g in bp["groups"]}):
                i = R.get(reg)
                if i is None:
                    continue
                bq = self.biofuel_feedstock_use_region(reg, {c: float(PR[i, Cc[c]]) for c in self.commodities})
                for c, q in bq.items():
                    j = Cc.get(c)
                    q0 = bp["q0_reg"].get((reg, c), 0.0)
                    if j is None or q0 <= 0 or Bf0[i, j] <= 0:
                        continue
                    Bf[i, j] = Bf0[i, j] * q / q0
                    if reg in self.EU:
                        self.ev.eu_biof_ratio.setdefault(reg, {})[c] = q / q0

        D = FIX + H + F + P + Bf
        # what the welfare report integrates over (market/welfare.py): the Armington price ratios and base levels
        self._welfare_eval = {"PR": PR, "REF": REFv, "F0": F0, "P0": P0}
        # the food response of the EU's use per parent commodity (residual feeds' output, MaprFeed_: HCON + PROC)
        self.ev.eu_food_ratio = {}
        for _reg in self.EU:
            ie = R.get(_reg)
            if ie is None:
                continue
            fr = self.ev.eu_food_ratio.setdefault(_reg, {})
            for c in (self._feed_byproduct_params().get("parents") or ()):
                j = Cc.get(c)
                if j is not None:
                    b0 = H0[ie, j] + P0[ie, j]
                    fr[c] = (H[ie, j] + P[ie, j]) / b0 if b0 > 0 else 1.0
        # RAW MILK: EU and Norway deliver their milk to their own dairies (not traded with third countries)
        _ms_now = self.ev.eu_milk_supply_now
        if "MILK" in Cc and self._dairy_params() and _ms_now:
            for _reg in self.EU:
                ie = R.get(_reg)
                if ie is not None:
                    D[ie, Cc["MILK"]] = float(_ms_now.get(_reg, 0.0) if isinstance(_ms_now, dict) else _ms_now)
        _sup_now = self.ev.sup_milk_now or {}
        for _reg in self.SUP:
            i = R.get(_reg)
            if i is not None and "MILK" in Cc and _reg in _sup_now:
                D[i, Cc["MILK"]] = float(_sup_now[_reg])
        # other regions: raw milk is used by their own dairies (CAPRI: not traded; DairyNQ_ against ProdNQ_ in the
        # region's dairy block, audit M11); without a block it stays at its base
        _wm = self.ev.world_milk_now or {}
        if "MILK" in Cc:
            for _reg, q_ in _wm.items():
                i = R.get(_reg)
                if i is not None:
                    D[i, Cc["MILK"]] = D0[i, Cc["MILK"]] + (float(q_) - float(self.par.base_production.at[_reg, "MILK"]))
        # BIOFUELS' OWN USE (biofDemShare_, biofDem_; non-fuel processing ProcNQ_)
        bm = self._biofuel_market_params()
        if bm:
            st = None
            if self.biofuel_endogenous():
                st = self.biofuel_state(None, pd.DataFrame(PR, index=self.regions, columns=self.commodities),
                                        use_only=True)
            for (reg, fuel), u0 in bm["use0"].items():
                i, j = R.get(reg), Cc.get(fuel)
                if i is None or j is None:
                    continue
                if st is not None:
                    p0 = float(bm["proc0"].get((reg, fuel), 0.0))
                    D[i, j] = max(0.0, D0[i, j] - u0 - p0 + st["use"].get((reg, fuel), u0)
                                  + st["proc"].get((reg, fuel), p0))
                else:
                    D[i, j] = D0[i, j]
        self._rest_share = np.where(D0 > 0, FIX / np.where(D0 > 0, D0, 1.0), 0.0)     # fixed share (diagnostic)
        return pd.DataFrame(D, index=self.regions, columns=self.commodities).clip(lower=0.0).astype(float)

