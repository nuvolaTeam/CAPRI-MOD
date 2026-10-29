"""MarketModule: CAPRI's welfare report for the market's agents (reports/welfare.gms; audit M7).

Part of capri_mod.market.market_module.MarketModule (a mixin). Reporting only: nothing here feeds back into the
solve.

CAPRI measures each agent's welfare with the agent's own behavioural function, integrated over the price changes
from the calibration point to the simulation (reports/welfare.gms):

  CSSP          consumers: the money metric of the Generalised Leontief demand system per behavioural region, one
                good's price after the other (l. 95-140)
  ProfitProc    processing industry: the normalised quadratic processing functions (ProcNQ_) and oilseed crushing
                (margins, ProcMargO_) per behavioural region (l. 155-200), the biofuel processors' margin x output and
                the value of the residual feeds of the regions with supply models (l. 186-213)
  ProfitDairy   dairies: the normalised quadratic dairy function (DairyNQ_) in the processing margins (ProcMargM_),
                raw milk an input (l. 205-260)
  ProfitAgr     farms of the regions without supply models: CAPRI's NQ supply function (l. 265-300). The regions
                with supply models (the EU, Norway) take the supply models' gross value added (l. 360-380, l. 800-806);
                that is not a market quantity (model level, capri_mod/model.py)
  ProfitFeed    feed users of the regions without supply models (FeedNQ_; l. 455-540)
  TariffRev     tariffs on every bilateral flow (l. 545-605)
  TRQRents      quota rents, half to the importer, half to the exporter (l. 610-650)

The model's functions are CAPRI's where the model has them (GL demand, ProcNQ_, crushing, DairyNQ_, the non-EU raw
milk supply, the bilateral import prices, TRQs); its non-EU supply and feed demand are constant-elasticity functions
(CAPRI: NQ functions; docs/design/ARCHITECTURE_REFACTOR.md 5.1, M3), so their integrals are the integrals of those
functions. Each component is the exact integral of the function the market solved with:
  - a linear (NQ) function with a symmetric Hessian: integral = sum_i (q0_i + dq_i / 2) dp_i, the value CAPRI's
    good-by-good sum gives for a quadratic profit function (independent of the order);
  - the GL money metric: CAPRI's good-by-good sequence (it depends on the order: the goods in CAPRI's order,
    gl_demand_goods.csv);
  - the constant-elasticity non-EU feed demand with cross-price terms: good by good in the model's commodity order
    (its integral depends on the order, as CAPRI's GL money metric does).

Values are levels, as CAPRI reports them (EUR million; the project lead's decision, 28 October 2026): the change from
the market's calibration point plus CAPRI's base value of each component, set by its conventions (welfare.gms):
household expenditure at the calibration point (CSSP), processing x price or crushing margin (ProfitProc), dairy
products x processing margin (ProfitDairy), the revenue of the regions without supply models less their land and
feed-energy netputs (ProfitAgr, with CAPRI's SUPREMA land accounts, as its 2030 reference), minus 20% of their feed
cost (ProfitFeed). The base values per CAPRI region are CAPRI's own data, computed with those formulas by
tools/build/build_welfare_base.py (welfare_base_2030.csv); CSSP and ProfitDairy reproduce the levels of CAPRI's 2030
reference run exactly. TariffRev and TRQRents are levels by construction. A comparison of two runs takes the difference
of the levels (CAPRIModel.compare), in which the base values cancel.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd


class WelfareMixin:
    """MarketModule methods for CAPRI's welfare report (reports/welfare.gms)."""

    #: the components of the market's welfare report (EUR million, levels as CAPRI's: base value plus change)
    WELFARE_COMPONENTS = ("CSSP", "ProfitProc", "ProfitDairy", "ProfitAgr", "ProfitFeed", "TariffRev", "TRQRents")

    # ------------------------------------------------------------------
    # consumers: the GL money metric (reports/welfare.gms l. 95-140)
    # ------------------------------------------------------------------
    @staticmethod
    def _gl_money_metric(e: dict, p_sim: np.ndarray) -> np.ndarray:
        """CAPRI's equivalent variation of one behavioural region, good by good (EUR per head): the prices move from
        the calibration point to the simulation one good after the other, in CAPRI's order; step k is
            G(P_cal) / G(P_y) x (Y - sum_j d_j P_y,j) - (Y - sum_j d_j P_cal,j)
        with P_cal the prices before the step and P_y after it (G = sum_ij b_ij sqrt(p_i p_j)); a good without an
        own b term (p_pbGL(XX1,XX1) = 0) has no step of its own, its price moves all the same. Returns the step
        values per good."""
        B, d, Y = e["B"], e["d"], e["Y"]
        ps_cal = e["p0"].astype(float).copy()
        ps_y = ps_cal.copy()
        G = lambda p: float(np.sqrt(p) @ B @ np.sqrt(p))
        ev = np.zeros(len(ps_cal))
        for k in range(len(ps_cal)):
            ps_y[k] = p_sim[k]
            if B[k, k] != 0.0:
                ev[k] = G(ps_cal) / G(ps_y) * (Y - float(d @ ps_y)) - (Y - float(d @ ps_cal))
            ps_cal[k] = ps_y[k]
        return ev

    def _welfare_cssp(self, PR: np.ndarray) -> Dict[str, float]:
        """CSSP per model region (EUR million): CAPRI's money metric per behavioural region at the consumer prices
        the GL demand saw (gl_food_ratio: CPRI0 + (PR - 1) ARM1P0, floored at 5% of CPRI0), x inhabitants."""
        prm = self._gl_params()
        Rr = {r: i for i, r in enumerate(self.regions)}
        out: Dict[str, float] = {}
        for mr, ents in (prm.get("groups") or {}).items():
            i = Rr[mr]
            for e in ents:
                col = e["col"]
                p = e["p0"].copy()
                m = col >= 0
                p[m] = p[m] + (PR[i, col[m]] - 1.0) * e["arm1p"][m]
                p = np.maximum(p, 0.05 * e["p0"])
                ev = self._gl_money_metric(e, p)
                out[mr] = out.get(mr, 0.0) + float(ev.sum()) * e["inha"] / 1000.0
        return out

    # ------------------------------------------------------------------
    # processing industry (l. 155-200)
    # ------------------------------------------------------------------
    def _welfare_proc_tables(self) -> dict:
        """Per behavioural region: the processing Hessian h / INPE (symmetric) and the Armington prices ARM1P of its
        goods, and CAPRI's base processing (processing_nq_hessian.csv, processing_nq_base.csv)."""
        cached = getattr(self, "_welf_proc_cache", None)
        if cached is not None:
            return cached
        inp = self._inp()
        hh = inp.csv("processing_nq_hessian.csv", keep_default_na=False, na_values=[""])
        bb = inp.csv("processing_nq_base.csv", keep_default_na=False, na_values=[""])
        inpe = bb.groupby("rms")["inpe"].first().to_dict()

        def mreg(rms, mr):
            if mr == "EU27" and self.eu_blocks:
                return self.eu_region_of_ms(rms) or mr
            return mr
        H, ap, reg = {}, {}, {}
        for r in hh.itertuples(index=False):
            R = mreg(r.rms, r.model_region)
            reg[r.rms] = R
            k = H.setdefault(r.rms, {})
            v = float(r.h) / float(inpe[r.rms])
            k[(r.x, r.y)] = k.get((r.x, r.y), 0.0) + v
            if r.x != r.y:
                k[(r.y, r.x)] = k.get((r.y, r.x), 0.0) + v
            ap[(r.rms, r.x)] = float(r.arm1p_x)
            ap[(r.rms, r.y)] = float(r.arm1p_y)
        q = {}
        for r in bb.itertuples(index=False):
            q[(r.rms, r.commodity)] = float(r.proc_kt)
            reg.setdefault(r.rms, mreg(r.rms, r.model_region))
        out = {"H": H, "arm1p": ap, "q": q, "region": reg}
        self._welf_proc_cache = out
        return out

    def _welfare_proc_nq(self, PR: np.ndarray, P0: np.ndarray) -> Dict[str, float]:
        """ProfitProc of the ProcNQ_ processing (the products other than oilseeds and biofuels) per model region: per
        behavioural region, the processed goods are inputs priced at the Armington price, so
            change = - sum_x (q0_x + dq_x / 2) dp_x,   dp_x = ARM1P_x (PR_x - 1),   dq_x = - sum_y H_xy dp_y
        (the model's ProcNQ_, before ProcFudge_ as in CAPRI's report); q0 the model region's base processing P0
        spread over its behavioural regions by CAPRI's processing; for the dairy products (processed in the dairy
        blocks, ProcNQ_ per member state since audit M9) the behavioural region's own base processing."""
        pq = self._proc_nq_params() or {}
        tb = self._welfare_proc_tables()
        Rr = {r: i for i, r in enumerate(self.regions)}
        Cc = {c: j for j, c in enumerate(self.commodities)}
        skip = set(self.CRUSH_CHAINS) | set(self._PROC_NQ_SKIP)
        dairy = set(self.DAIRY_TRADED.values())
        active = {k for k in (pq.get("share") or {}) if k[1] not in skip and k[1] in Cc and k[0] in Rr
                  and P0[Rr[k[0]], Cc[k[1]]] > 0}
        tot = {}
        for (rms, c), v in tb["q"].items():
            R = tb["region"].get(rms)
            if (R, c) in active and rms in tb["H"]:
                tot[(R, c)] = tot.get((R, c), 0.0) + v
        out: Dict[str, float] = {}
        for rms, Hr in tb["H"].items():
            R = tb["region"].get(rms)
            if R not in Rr:
                continue
            i = Rr[R]
            dp = {}
            for (x, y) in Hr:
                for g in (x, y):
                    if g not in dp and g in Cc and g not in self.CRUSH_CHAINS:
                        dp[g] = tb["arm1p"].get((rms, g), 0.0) * (PR[i, Cc[g]] - 1.0)
            val = 0.0
            for x in {x for (x, _) in Hr}:
                if x in dairy:
                    q0 = tb["q"].get((rms, x), 0.0)
                    if q0 <= 0 or x not in dp:
                        continue
                elif (R, x) not in active or tot.get((R, x), 0.0) <= 0:
                    continue
                else:
                    q0 = P0[i, Cc[x]] * tb["q"].get((rms, x), 0.0) / tot[(R, x)]
                dq = -sum(h * dp.get(y, 0.0) for (x_, y), h in Hr.items() if x_ == x)
                val -= (q0 + 0.5 * dq) * dp.get(x, 0.0)
            out[R] = out.get(R, 0.0) + val / 1000.0
        return out

    def _welfare_crush(self, crush_prices: pd.DataFrame) -> Dict[str, float]:
        """ProfitProc of oilseed crushing per model region: per behavioural region and seed, the crush is linear in
        the crushing margins (ProcNQ_ on ProcMargO_), so change = sum_s (q0_s + dq_s / 2) dm_s (q0 the region's base
        crush spread as _crush_state spreads it, dq before ProcFudge_)."""
        det: dict = {}
        self._crush_state(crush_prices, detail=det)
        out: Dict[str, float] = {}
        for (r, s, rms), (q0, dq, dm) in det.items():
            out[r] = out.get(r, 0.0) + (q0 + 0.5 * dq) * dm / 1000.0
        return out

    def _welfare_biofuel_byproducts(self, r: pd.DataFrame, S: pd.DataFrame) -> Dict[str, float]:
        """The other two parts of CAPRI's ProfitProc (welfare.gms l. 186-213), per model region, EUR million:
          biofuel processors: margin x first-generation output, simulation less reference, the margin the biofuel's
              producer price less the feedstock cost per t of biofuel (reports/sol_market.gms l. 695: v_prodPrice -
              v_BiofFeedCost; here PPRI0 x the price ratio - mu_b, the CES feedstock cost of biofuel_state);
          residual feeds of the regions with supply models (RESIMPX: FENI, FPRI; the EU): the change of their output
              value, output x producer price."""
        out: Dict[str, float] = {}
        st = self.ev.biof_state
        bm = self._biofuel_market_params() or {}
        bp = self._biofuel_params() or {}
        if st is not None and bm:
            rows = bm.get("rows", {})
            scale = self.biofuel_output_scale or {}
            for g in bp.get("groups", []):
                key = (g["ms"], g["fuel"])
                d = rows.get(key)
                reg = g["region"]
                if d is None or key not in st["X"] or key not in st["mub"] or reg not in r.index or g["fuel"] not in r.columns:
                    continue
                mub0 = self._biofuel_feed_group(g, {}, 1.0, 1.0)[1]
                x0 = g["X0"] * float(scale.get(g["fuel"], 1.0))
                m1 = float(d["ppri"]) * float(r.at[reg, g["fuel"]]) - float(st["mub"][key])
                m0 = float(d["ppri"]) - mub0
                out[reg] = out.get(reg, 0.0) + (m1 * float(st["X"][key]) - m0 * x0) / 1000.0
        fp = self._feed_byproduct_params() or {}
        dom0 = self._dom0()
        for reg in self.EU:
            if reg not in S.index:
                continue
            for p in (fp.get("products") or {}):
                if p not in S.columns or p not in r.columns or reg not in dom0.index:
                    continue
                p0 = float(dom0.at[reg, p])
                q0 = float(self.par.base_production.at[reg, p])
                out[reg] = out.get(reg, 0.0) + (float(S.at[reg, p]) * p0 * float(r.at[reg, p]) - q0 * p0) / 1000.0
        return out

    # ------------------------------------------------------------------
    # dairies (l. 205-260) and the non-EU raw milk supply (part of ProfitAgr)
    # ------------------------------------------------------------------
    @staticmethod
    def _dairy_profit(prm: dict, z: np.ndarray) -> float:
        """One dairy block (one behavioural region): netputs = the products' output and minus the raw milk taken,
        prices = their processing margins (ProcMargM_: price less the fat and protein values; for raw milk CAPRI's
        welfare reverses the sign of its row, l. 227-229); with the block's linear DairyNQ_,
        change = sum_k n0_k dm_k + 1/2 sum_k dn_k dm_k, EUR 1000."""
        Mm = prm.get("Mm")
        if Mm is None:
            return 0.0
        dm = Mm @ z
        dQ = prm["G"] @ z
        sgn = np.ones(len(prm["items"]))
        sgn[prm["iM"]] = -1.0
        return float(np.sum(sgn * (prm["Q0"] + 0.5 * dQ) * dm))

    def _welfare_dairy(self) -> Dict[str, Dict[str, float]]:
        """ProfitDairy per model region from the last dairy solutions (the EU member states' blocks and the non-EU
        trade regions' blocks), and the non-EU farms' profit from raw milk (CAPRI's raw milk supply function, ProdNQ_
        MILK: change = sum over the behavioural regions of (Q0 + dQ / 2) dp_MILK, dQ with the cross-price terms; the
        other products' share of the integral is in ProfitAgr). {"dairy": {...}, "milk": {...}}."""
        out = {"dairy": {}, "milk": {}}
        dp = self._dairy_params() or {}
        last = self.ev.dairy_last or {}
        msz = last.get("ms_z") or {}
        for ms, prm in (dp.get("ms") or {}).items():
            z = msz.get(ms)
            if z is None:
                continue
            rg = self.eu_region_of_ms(ms) or self.EU[0]
            out["dairy"][rg] = out["dairy"].get(rg, 0.0) + self._dairy_profit(prm, z) / 1000.0
        wp = self._dairy_world_params() or {}
        wl = self.ev.dairy_world_last or {}
        for tr, prm in wp.items():
            res = wl.get(tr)
            if res is None or "z" not in res:
                continue
            z = res["z"]
            for rms, a in (prm.get("rms") or {}).items():
                out["dairy"][tr] = out["dairy"].get(tr, 0.0) + self._dairy_profit(a, z) / 1000.0
                if res.get("milk_supply_ratio") is not None and a.get("SM", 0.0) > 0:
                    # CAPRI's raw milk supply function: its own-price change and its change from the other prices
                    dQ = a["SM"] * z[a["iM"]] + float((res.get("milk_shift_rms") or {}).get(rms, 0.0))
                    dpm = a["pM"] * z[a["iM"]]
                    out["milk"][tr] = out["milk"].get(tr, 0.0) + (a["Q0"][a["iM"]] + 0.5 * dQ) * dpm / 1000.0
        return out

    # ------------------------------------------------------------------
    # farms and feed users of the regions without supply models (l. 265-300, 455-540)
    # ------------------------------------------------------------------
    def _welfare_agr_feed(self, r: pd.DataFrame, S: pd.DataFrame, PR: np.ndarray, F0: np.ndarray,
                          REF: np.ndarray) -> Dict[str, Dict[str, float]]:
        """ProfitAgr and ProfitFeed of the market regions without supply models (CAPRI: not RMSSUP).

        ProfitAgr: with CAPRI's market supply functions (market.noneu_supply_nq) the integral of the linear supply
        over the price changes, p0 (rr - 1) (q0 + dq / 2) per product; otherwise the integral of the model's
        constant-elasticity supply S = S0 rr^e over the region's own price,
        S0 p0 (rr^(e+1) - 1) / (e + 1), for the cells whose supply is that function at the solution (crushing, the
        dairy blocks, raw milk, biofuels and residual feeds have their own blocks: their supply differs from it).
        ProfitFeed: minus the integral of the feed demand F = F0 prod_j PR_j^e_cj (p_ElasFeed), good by good in the
        model's commodity order."""
        out = {"agr": {}, "feed": {}}
        dom0 = self._dom0()
        ev_regs, cols, EVm = getattr(self, "_welf_supply_EV", (None, None, None))
        skip = set(self.EU) | set(getattr(self, "SUP", ()))
        for reg in S.index:
            if (reg in skip or reg not in r.index or reg not in self.par.base_production.index or ev_regs is None
                    or reg not in ev_regs):
                continue
            EV = EVm[ev_regs.index(reg)]
            nq = (getattr(self, "_welf_noneu_nq", None) or {}).get(reg) or {}
            v = 0.0
            for j, c in enumerate(cols):
                s0 = float(self.par.base_production.at[reg, c])
                p0 = float(dom0.at[reg, c]) if (reg in dom0.index and c in dom0.columns) else 0.0
                rr = max(float(r.at[reg, c]), 1e-6) if c in r.columns else 1.0
                if c == "MILK" or s0 <= 0 or not p0 > 0 or rr == 1.0:
                    continue                                  # raw milk: the dairy blocks' (or fixed, not traded)
                if c in nq:
                    # CAPRI's market supply function (ProdNQ_, linear in the prices): the profit change is the
                    # integral of the supply over the price change, p0 (r - 1) (q0 + dq / 2) on the straight path
                    # (exact for the linear function with CAPRI's symmetric Hessian)
                    q0_, dq_ = nq[c]
                    if abs(float(S.at[reg, c]) - max(q0_ + dq_, 0.0)) <= 1e-9 * max(1.0, q0_):
                        v += p0 * (rr - 1.0) * (q0_ + 0.5 * dq_)
                    continue
                e = float(EV[j])
                if abs(float(S.at[reg, c]) - s0 * rr ** e) > 1e-9 * max(1.0, s0):
                    continue                                  # not the elasticity function: another block's
                v += s0 * p0 * (np.log(rr) if abs(e + 1.0) < 1e-12 else (rr ** (e + 1.0) - 1.0) / (e + 1.0))
            out["agr"][reg] = v / 1000.0
        Rr = {x: i for i, x in enumerate(self.regions)}
        Cc = {c: j for j, c in enumerate(self.commodities)}
        fdp = self._feed_demand_params() or {}
        by_reg: Dict[str, list] = {}
        for (reg, c), prm in fdp.items():
            by_reg.setdefault(reg, []).append((c, prm))
        for reg, items in by_reg.items():
            if reg in skip or reg not in Rr:
                continue
            i = Rr[reg]
            v = 0.0
            for c, prm in items:
                j = Cc[c]
                if not (F0[i, j] > 0 and REF[i, j] > 0):
                    continue
                rc = PR[i, j]
                ec = float(prm["elasticities"].get(c, 0.0))
                # the goods before c in the order are at their simulation prices, the later ones at base
                C = 1.0
                for jn, e in prm["elasticities"].items():
                    if jn != c and jn in Cc and Cc[jn] < j and REF[i, Cc[jn]] > 0:
                        C *= PR[i, Cc[jn]] ** e
                I = np.log(rc) if abs(ec + 1.0) < 1e-12 else (rc ** (ec + 1.0) - 1.0) / (ec + 1.0)
                v -= F0[i, j] * REF[i, j] * C * I
            out["feed"][reg] = v / 1000.0
        return out

    # ------------------------------------------------------------------
    # tariffs and quota rents (l. 545-650)
    # ------------------------------------------------------------------
    def _welfare_trade(self, r: pd.DataFrame, D: pd.DataFrame, pc: dict) -> Dict[str, Dict[str, float]]:
        """TariffRev and TRQRents per model region (EUR million, levels: CAPRI's are levels too, no base offset).

        Per flow from exporter j to importer i (i != j, not between the EU's trade blocks): the importer pays the
        import price p_ij (CAPRI impPrice_: (Fob + transport)(1 + ad valorem) + specific, with the TRQ regime);
        exporter's price and transport are a0_ij r_j + tc_ij; the wedge X_ij (p_ij - a0_ij r_j - tc_ij) is tariffs
        plus, under an EU quota, the quota rent: CAPRI's rent = (import price - in-quota price) x min(imports under
        the quota, quota) (reports/sol_market.gms l. 1127), here gap x sigmoid(fill) x min(share x imports, quota),
        the import price under the sigmoid regime being the in-quota price plus sigmoid x gap. The rent goes half to
        the importer, half to the exporter (welfare.gms l. 614-620); tariffs to the importer."""
        tar: Dict[str, float] = {}
        rent: Dict[str, float] = {}
        R = list(self.regions)
        eu = set(self.EU)
        for c, sc in (self.par.bilat or {}).items():
            if c not in r.columns or c not in pc:
                continue
            rc = r[c].reindex(R).to_numpy(dtype=float)
            p = pc[c]
            X, _ = sc.flows(D[c].reindex(R).to_numpy(dtype=float), rc, p)
            tc = sc.tc if sc.tc is not None else np.zeros_like(sc.a0)
            wedge = p - sc.a0 * rc[None, :] - tc
            n = len(R)
            rent_ij = np.zeros((n, n))
            if sc.trq_row is not None and sc.trq_Q is not None:
                rows = sc._rows()
                for j in np.where(sc.trq_Q > 0)[0]:
                    xj = float(X[rows, j].sum())
                    if xj <= 0 or sc.trq_gap[j] <= 0:
                        continue
                    q_in = min(float(sc.trq_share[j]) * xj, float(sc.trq_Q[j]))
                    sig = float(sc._sig(float(sc.trq_share[j]) / float(sc.trq_Q[j]) * xj))
                    tot = float(sc.trq_gap[j]) * sig * q_in
                    for i_ in rows:
                        rent_ij[i_, j] = tot * float(X[i_, j]) / xj
            for i, imp in enumerate(R):
                for j, exp in enumerate(R):
                    if i == j or X[i, j] <= 0 or (imp in eu and exp in eu):
                        continue
                    w = float(X[i, j] * wedge[i, j])
                    rt = max(0.0, float(rent_ij[i, j]))
                    tar[imp] = tar.get(imp, 0.0) + (w - rt) / 1000.0
                    rent[imp] = rent.get(imp, 0.0) + 0.5 * rt / 1000.0
                    rent[exp] = rent.get(exp, 0.0) + 0.5 * rt / 1000.0
        return {"tariff": tar, "rent": rent}

    def _welfare_base(self) -> Dict[str, Dict[str, float]]:
        """CAPRI's base value of each component per model region (welfare_base_2030.csv: per CAPRI region, summed
        to the model's market regions; the EU's member states to their trade block with eu_blocks)."""
        cached = getattr(self, "_welf_base_cache", None)
        if cached is not None:
            return cached
        bb = self._inp().csv("welfare_base_2030.csv")
        out: Dict[str, Dict[str, float]] = {}
        for rms, mr, comp, v in bb[["rms", "model_region", "component", "value"]].itertuples(index=False):
            if mr == "EU27" and self.eu_blocks:
                mr = self.eu_region_of_ms(rms) or mr
            d = out.setdefault(str(mr), {})
            d[str(comp)] = d.get(str(comp), 0.0) + float(v)
        self._welf_base_cache = out
        return out

    # ------------------------------------------------------------------
    # the report
    # ------------------------------------------------------------------
    def _capri_welfare(self, r: pd.DataFrame, PAr: pd.DataFrame, S: pd.DataFrame, D: pd.DataFrame,
                       pc: dict) -> pd.DataFrame:
        """CAPRI's welfare components per market region at the market solution (EUR million, levels: CAPRI's base
        value plus the change from the calibration point), and their sum, Welfare. The EU's and Norway's
        farm profit, land rents and budget (ProfitAgr, ProfitLandUse, PSEs of the regions with supply models) come
        from the supply models (model level)."""
        ev = getattr(self, "_welfare_eval", None) or {}
        PR, P0, F0, REF = ev.get("PR"), ev.get("P0"), ev.get("F0"), ev.get("REF")
        rows = {reg: dict.fromkeys(self.WELFARE_COMPONENTS, 0.0) for reg in self.regions}
        if PR is None:
            return pd.DataFrame.from_dict(rows, orient="index")

        def add(comp, d):
            for reg, v in (d or {}).items():
                if reg in rows:
                    rows[reg][comp] += float(v)
        add("CSSP", self._welfare_cssp(PR))
        add("ProfitProc", self._welfare_proc_nq(PR, P0))
        if self._crush_params():
            dom0 = self._dom0()
            dp = dom0.reindex(index=r.index, columns=r.columns) * PAr
            oc = sorted({x for v in self.CRUSH_CHAINS.values() for x in v if x in r.columns})
            dp[oc] = dom0.reindex(index=r.index, columns=oc) * r[oc]
            add("ProfitProc", self._welfare_crush(dp))
        add("ProfitProc", self._welfare_biofuel_byproducts(r, S))
        dy = self._welfare_dairy()
        add("ProfitDairy", dy["dairy"])
        add("ProfitAgr", dy["milk"])
        af = self._welfare_agr_feed(r, S, PR, F0, REF)
        add("ProfitAgr", af["agr"])
        add("ProfitFeed", af["feed"])
        tr = self._welfare_trade(r, D, pc)
        add("TariffRev", tr["tariff"])
        add("TRQRents", tr["rent"])
        for reg, comps in self._welfare_base().items():           # CAPRI's levels: the base values
            if reg in rows:
                for comp, v in comps.items():
                    if comp in rows[reg]:
                        rows[reg][comp] += float(v)
        df = pd.DataFrame.from_dict(rows, orient="index")
        df["Welfare"] = df[list(self.WELFARE_COMPONENTS)].sum(axis=1)
        df.index.name = "region"
        return df
