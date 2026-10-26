"""MarketModule: the biofuel block (feedstock demand, the biofuel markets BIOE and BIOD, blending mandates).

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


class BiofuelMixin:
    """MarketModule methods for the biofuel block (feedstock demand, the biofuel markets BIOE and BIOD, blending mandates)."""


    #: Biofuel output relative to CAPRI's 2030 reference, per biofuel ({"BIOE": 1.0, "BIOD": 1.0}), when biofuel
    #: markets are NOT endogenous: CAPRI then fixes biofuel output (arm/fix_biofuel_market_vars.gms); a mandate
    #: scenario changes these quantities.
    biofuel_output_scale: Dict[str, float] = {"BIOE": 1.0, "BIOD": 1.0}
    #: Endogenous biofuel markets (CAPRI BIOF_M, star 3.0 GUI default ON; arm/prep_market.gms p_endoBioMarket):
    #: biofuel supply from the processing margin (SupplyBiof_), demand from mandates and the price relative to
    #: fossil fuel (biofDemShare_, biofDem_), bilateral trade; feedstock use follows the biofuel output. Off:
    #: biofuel quantities fixed at the reference, only the feedstock mix responds. A scenario setting
    #: (PolicyScenario.biofuel_markets), docs/BIOFUEL_MARKET.md.
    biofuel_markets = setting("market.biofuel_markets", run_state=True)
    BIOFUELS = ("BIOE", "BIOD")

    def _biofuel_params(self) -> dict:
        """First-generation biofuel feedstock demand, CAPRI's market equations (biofFeedCost_, biofFeedCostAgg_,
        Biof_, prodBiof_, prodQuantBiofBy_), per CAPRI market region.

        From capri_data/2017/market/biofuel_feedstock.csv (tools/build/build_biofuel_market.py): per CAPRI region and
        biofuel, the feedstocks' 2030-reference quantities q0, PRCB, PRCBY, by-product, prices and the numeraire;
        and biofuel_use_share.csv: EU biofuel use as a share of the EU use of each model commodity.
        Returns {"groups": [...], "share": {commodity: EU share}, "q0": {commodity: EU kt},
        "q0_reg": {(region, commodity): kt}, "ddgs0": {region: kt}} ({} when the files are absent).
        """
        cached = getattr(self, "_biof_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            f = self._inp().csv("biofuel_feedstock.csv", keep_default_na=False)
            if "region" not in f.columns:
                f["region"] = "EU27"
            sh = self._inp().csv("biofuel_use_share.csv")
            groups = []
            for (ms, fuel), g in f.groupby(["ms", "biofuel"], sort=True):
                reg = str(g["region"].iloc[0])
                if reg == "EU27" and self.eu_blocks:
                    reg = self.eu_region_of_ms(ms) or reg
                if reg not in self.regions:
                    continue
                q0 = g["biof_kt"].astype(float).values
                prcb = g["prcb"].astype(float).values
                p0 = g["feed_price"].astype(float).values
                prcby = g["prcby"].astype(float).values
                pby0 = g["byproduct_price"].astype(float).values
                by = prcby * pby0
                mu0 = p0 - by
                if (mu0 <= 0).any() or (q0 <= 0).any():
                    continue
                X0 = float((q0 * prcb).sum())
                mub0 = float((q0 * mu0).sum()) / X0                  # = CAPRI BiofFeedCost (checked by the builder)
                rho = float(g["rho"].iloc[0])
                dp = q0 / X0 * (mu0 / mub0) ** rho                   # def_biofuel_params.gms p_dpCESBiof
                ddgs = np.array([b_ == "DDGS" for b_ in g["byproduct"].astype(str)])
                groups.append(dict(ms=ms, fuel=fuel, region=reg, comm=list(g["commodity"].astype(str)),
                                   feed=list(g["feedstock"].astype(str)), q0=q0, prcb=prcb, p0=p0, by=by,
                                   prcby=prcby, ddgs=ddgs, X0=X0, mub0=mub0, rho=rho, dp=dp,
                                   num=int(np.argmax(g["numeraire"].astype(int).values))))
            share = {str(r.commodity): float(r.share) for r in sh.itertuples()
                     if r.commodity in self.commodities and float(r.share) > 0}
            q0c, q0r, dd0 = {}, {}, {}
            for gr in groups:
                for c, q in zip(gr["comm"], gr["q0"]):
                    if c and c in self.commodities:
                        q0r[(gr["region"], c)] = q0r.get((gr["region"], c), 0.0) + float(q)
                        if gr["region"] in self.EU and c in share:
                            q0c[c] = q0c.get(c, 0.0) + float(q)
                dd0[gr["region"]] = dd0.get(gr["region"], 0.0) + float((gr["q0"] * gr["prcby"] * gr["ddgs"]).sum())
            # biofuel share of use per EU market region: the region's feedstock use over its use (the EU use of the
            # file split by CAPRI's member-state use); one EU region: the file's share
            use_eu = {str(r.commodity): float(r.use_kt) for r in sh.itertuples()}
            share_reg = {}
            for reg in self.EU:
                for c, sh_ in share.items():
                    if not self.eu_blocks:
                        share_reg[(reg, c)] = sh_
                        continue
                    u = use_eu.get(c, 0.0) * self.eu_split(c)[reg]
                    q = q0r.get((reg, c), 0.0)
                    if u > 0 and q > 0:
                        share_reg[(reg, c)] = min(1.0, q / u)
            out = {"groups": groups, "share": share, "q0": q0c, "q0_reg": q0r, "ddgs0": dd0,
                   "share_reg": share_reg} if groups else {}
        except Exception as exc:
            raise RuntimeError(f"market: the biofuel feedstock inputs could not be read ({exc!r})") from exc
        self._biof_cache = out
        return out

    def _biofuel_market_params(self) -> dict:
        """CAPRI's biofuel supply and demand functions per CAPRI market region (biofuel/def_biofuel_params.gms,
        calibrated by tools/build/build_biofuel_market.py to the 2030 reference): {(ms, fuel): row} plus the region
        totals at the reference (output, biofuel use, non-fuel processing). {} when the file is absent."""
        cached = getattr(self, "_biofm_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            m = self._inp().csv("biofuel_market.csv")
            for col in ("proc_kt", "proc_hess", "inpe"):
                if col not in m.columns:
                    m[col] = 0.0
            gidx = {(g["ms"], g["fuel"]): k for k, g in enumerate(self._biofuel_params().get("groups", []))}
            rows = {}
            for r in m.itertuples(index=False):
                if r.region == "EU27" and self.eu_blocks:
                    r = r._replace(region=self.eu_region_of_ms(r.ms) or r.region)
                if r.region not in self.regions or r.biofuel not in self.commodities:
                    continue
                d = r._asdict()
                d["group"] = gidx.get((r.ms, r.biofuel))
                # CAPRI's mandate scenario (scen/bio_fuels/change_biof_mandate.gms) shifts the EU member states'
                # and the UK's QUTS
                d["mandate_region"] = (r.region in self.EU) or (r.ms == "UK000000")
                rows[(r.ms, r.biofuel)] = d
            prod0, use0, proc0 = {}, {}, {}
            for (ms, fuel), d in rows.items():
                k = (d["region"], fuel)
                prod0[k] = prod0.get(k, 0.0) + float(d["prod_kt"])
                use0[k] = use0.get(k, 0.0) + float(d["biof_kt"])
                proc0[k] = proc0.get(k, 0.0) + float(d["proc_kt"])
            out = {"rows": rows, "prod0": prod0, "use0": use0, "proc0": proc0} if rows else {}
        except Exception as exc:
            raise RuntimeError(f"market: the biofuel market inputs could not be read ({exc!r})") from exc
        self._biofm_cache = out
        return out

    #: CAPRI's mandate scenario (scen/bio_fuels/change_biof_mandate.gms): the EU member states' and the UK's
    #: blending mandates QUTS multiplied by this factor (PolicyScenario.biofuel_mandate; acts with endogenous
    #: biofuel markets, where QUTS enters biofDemShare_)
    biofuel_mandate: float = 1.0

    def biofuel_endogenous(self) -> bool:
        """Endogenous biofuel markets are on: the switch, the bilateral market, both biofuels traded, data."""
        return bool(getattr(self, "biofuel_markets", True)) and getattr(self, "market_structure", "") == "bilateral" \
            and all(b in self.commodities for b in self.BIOFUELS) and bool(self._biofuel_market_params())

    @staticmethod
    def _sigmoid(x):
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500.0, 500.0)))

    def _biofuel_feed_group(self, g, ratio: Dict[str, float], X: Optional[float] = None, ddgs_ratio: float = 1.0):
        """One CAPRI region's feedstock CES for one biofuel at feedstock price ratios (Arm1 prices relative to
        the reference): returns (q per feedstock, mu_b). X = first-generation output (default: the reference
        output x biofuel_output_scale); ddgs_ratio = the region's DDGS producer price relative to the reference.

            mu_f = p_f0 x ratio_c - PRCBY_f x p_by          (biofFeedCost_; DDGS at its producer price, glycerine
                                                             fixed at 600 EUR/t as in CAPRI)
            mu_b = (sum_f dp_f mu_f^(1-rho))^(1/(1-rho))    (biofFeedCostAgg_)
            q_f  = dp_f X (mu_b / mu_f)^rho, f not the numeraire (Biof_)
            q_num = (X - sum_f q_f PRCB_f) / PRCB_num        (prodBiof_)
        """
        r = np.array([float(ratio.get(c, 1.0)) if c else 1.0 for c in g["comm"]])
        by = g["by"] * np.where(g["ddgs"], float(ddgs_ratio), 1.0)
        mu = np.maximum(g["p0"] * r - by, 1e-6)
        rho = g["rho"]
        mub = float((g["dp"] * mu ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))
        if X is None:
            X = g["X0"] * float((self.biofuel_output_scale or {}).get(g["fuel"], 1.0))
        q = g["dp"] * X * (mub / mu) ** rho
        n = g["num"]
        rest = float((q * g["prcb"]).sum() - q[n] * g["prcb"][n])
        q[n] = max(0.0, (X - rest) / g["prcb"][n])
        return q, mub

    def biofuel_state(self, prod_ratio: Optional[pd.DataFrame], arm_ratio: Optional[pd.DataFrame],
                      endogenous: Optional[bool] = None, use_only: bool = False) -> dict:
        """CAPRI's biofuel processing and biofuel markets at producer price ratios (prod_ratio: region x
        commodity, market prices relative to the reference) and Armington price ratios (arm_ratio), per CAPRI
        market region:

          supply  PR = PPRI0 x r_b / mu_b (biofPriceRel_; producer prices move with the market price,
                  multiplicative margin),  X = scale PR + exp(alfa + beta log(PR + 0.01)) SIGMOID(slope (PR - turn))
                  (SupplyBiof_); production = X + NAGR + SECG + EXOG (MaprBiof_, the last three fixed)
          DDGS    output = sum_f q_f PRCBY_f over the cereal feedstocks (prodQuantBiofBy_); its producer price
                  enters the feedstock cost (biofFeedCost_)
          demand  consumer price = CPRI0 + ARM1P0 (ra_b - 1) (Cpri_: additive tax and margins),
                  share = QUTS x mandate + MAX SIGMOID(Slope (CPRI / fossil CPRI - Turn)) (biofDemShare_),
                  BIOF = share x HCON x oilEqu_f / oilEqu_b (biofDem_; total fuel use and fossil prices fixed)
          other   non-fuel processing PROC = PROC0 - hess x ARM1P0 (ra_b - 1) / INPE (ProcNQ_, own term)

        Without endogenous biofuel markets (CAPRI without BIOF_M) biofuel output is the reference x
        biofuel_output_scale and only the feedstock mix and DDGS respond. Regions without a supply function (no
        feedstocks or no price relation) keep their reference output, without a demand function (no fossil fuel
        data or no use above the mandate) their reference use.
        Returns {"X": {(ms, fuel): kt}, "mub": {...}, "prod": {(region, fuel): kt}, "use": {...}, "proc": {...},
        "ddgs": {region: kt}, "ddgs_ratio": {region: ratio}, "endogenous": bool}."""
        endo = self.biofuel_endogenous() if endogenous is None else bool(endogenous)
        bm = self._biofuel_market_params()
        bp = self._biofuel_params()
        groups = bp.get("groups", [])
        scale = self.biofuel_output_scale or {}
        mand = float(1.0 if getattr(self, "biofuel_mandate", None) is None else self.biofuel_mandate)
        has_dd = "DDGS" in self.commodities

        # positional lookups (pandas scalar access here was a sizeable share of the market solve)
        _pi = {r: i for i, r in enumerate(prod_ratio.index)} if prod_ratio is not None else {}
        _pc = {c: j for j, c in enumerate(prod_ratio.columns)} if prod_ratio is not None else {}
        _pa = prod_ratio.to_numpy(dtype=float) if prod_ratio is not None else None
        _ai = {r: i for i, r in enumerate(arm_ratio.index)} if arm_ratio is not None else {}
        _ac = {c: j for j, c in enumerate(arm_ratio.columns)} if arm_ratio is not None else {}
        _aa = arm_ratio.to_numpy(dtype=float) if arm_ratio is not None else None

        def dratio(reg):
            if prod_ratio is None or not has_dd or reg not in _pi:
                return 1.0
            return float(_pa[_pi[reg], _pc["DDGS"]])

        def aratio(reg, c):
            if arm_ratio is None or not c or reg not in _ai or c not in _ac:
                return 1.0
            return float(_aa[_ai[reg], _ac[c]])

        X, MUB, prod, use, proc, ddgs, drat = {}, {}, {}, {}, {}, {}, {}
        rows = bm.get("rows", {})
        # first-generation output and feedstock cost of every feedstock group (not needed for use and processing)
        for g in ([] if use_only else groups):
            reg, key = g["region"], (g["ms"], g["fuel"])
            drat[reg] = dratio(reg)
            ratio = {c: aratio(reg, c) for c in g["comm"] if c}
            q1, mub = self._biofuel_feed_group(g, ratio, 1.0, drat[reg])
            MUB[key] = mub
            d = rows.get(key)
            x = g["X0"] * float(scale.get(g["fuel"], 1.0))
            if endo and d is not None and float(d["pr0"]) > 0:
                rb = float(_pa[_pi[reg], _pc[g["fuel"]]]) if prod_ratio is not None else 1.0
                PR = float(d["ppri"]) * rb / mub
                x = float(d["sup_scale"]) * PR + np.exp(float(d["sup_alfa"]) + float(d["sup_beta"]) * np.log(PR + 1e-2)) \
                    * float(self._sigmoid(float(d["sup_slope"]) * (PR - float(d["sup_turn"]))))
                x = max(0.0, x)
            X[key] = x
            ddgs[reg] = ddgs.get(reg, 0.0) + float((q1 * x * g["prcby"] * g["ddgs"]).sum())
        # output, use and processing of every CAPRI market region
        for (ms, fuel), d in rows.items():
            reg = d["region"]
            ra = aratio(reg, fuel)
            x = X.get((ms, fuel), float(d["x0_kt"]) * (1.0 if endo else float(scale.get(fuel, 1.0))))
            prod[(reg, fuel)] = prod.get((reg, fuel), 0.0) + x + float(d["fixed_kt"])
            u = float(d["biof_kt"])
            if endo and float(d["dem_slope"]) != 0.0 and float(d["fossil_cpri"]) > 0:
                cp = max(1e-6, float(d["cpri"]) + float(d["arm1p"]) * (ra - 1.0))
                quts = float(d["quts"]) * (mand if d["mandate_region"] else 1.0)
                share = quts + float(d["dem_max"]) * float(
                    self._sigmoid(float(d["dem_slope"]) * (cp / float(d["fossil_cpri"]) - float(d["dem_turn"]))))
                u = share * float(d["hcon_kt"]) * float(d["oil_eq_fossil"]) / float(d["oil_eq"])
            use[(reg, fuel)] = use.get((reg, fuel), 0.0) + u
            pc = float(d["proc_kt"])
            if endo and pc > 0 and float(d["proc_hess"]) != 0.0 and float(d["inpe"]) > 0:
                pc = max(0.0, pc - float(d["proc_hess"]) * float(d["arm1p"]) * (ra - 1.0) / float(d["inpe"]))
            proc[(reg, fuel)] = proc.get((reg, fuel), 0.0) + pc
        return {"X": X, "mub": MUB, "prod": prod, "use": use, "proc": proc, "ddgs": ddgs, "ddgs_ratio": drat,
                "endogenous": endo}

    def _biofuel_x(self, g) -> float:
        """First-generation output of a feedstock group: the current biofuel state's (endogenous with biofuel
        markets, else the reference x biofuel_output_scale)."""
        st = getattr(self, "_biof_state", None)
        if st is not None:
            return float(st["X"].get((g["ms"], g["fuel"]), g["X0"]))
        return g["X0"] * float((self.biofuel_output_scale or {}).get(g["fuel"], 1.0))

    def biofuel_feedstock_use_region(self, region: str, price_ratio: Dict[str, float]) -> Dict[str, float]:
        """Feedstock use for biofuels of one trade region by model commodity (kt) at its feedstock price ratios."""
        out = {}
        st = getattr(self, "_biof_state", None)
        dr = float((st or {}).get("ddgs_ratio", {}).get(region, 1.0))
        for g in self._biofuel_params().get("groups", []):
            if g["region"] != region:
                continue
            q, _ = self._biofuel_feed_group(g, price_ratio, self._biofuel_x(g), dr)
            for c, x in zip(g["comm"], q):
                if c:
                    out[c] = out.get(c, 0.0) + float(x)
        return out

    def biofuel_feedstock_use(self, price_ratio: Dict[str, float]) -> dict:
        """EU feedstock use for biofuels at EU feedstock prices (relative to base; with two EU market regions
        {region: {commodity: ratio}}), CAPRI's equations
        (MarketModule._biofuel_feed_group); first-generation output from the biofuel market when endogenous,
        else the 2030-reference output x biofuel_output_scale. Returns {"by_commodity": {c: kt},
        "by_feedstock": {(fuel, feedstock): kt}, "output": {fuel: kt}} (output: first generation).
        """
        byc, byf, outp = {}, {}, {}
        for g in self._biofuel_params().get("groups", []):
            if g["region"] not in self.EU:
                continue
            X = self._biofuel_x(g)
            st = getattr(self, "_biof_state", None)
            pr = (price_ratio.get(g["region"], {}) if any(isinstance(v, dict) for v in price_ratio.values())
                  else price_ratio)
            q, _ = self._biofuel_feed_group(g, pr, X, float((st or {}).get("ddgs_ratio", {}).get(g["region"], 1.0)))
            outp[g["fuel"]] = outp.get(g["fuel"], 0.0) + X
            for c, f, x in zip(g["comm"], g["feed"], q):
                byf[(g["fuel"], f)] = byf.get((g["fuel"], f), 0.0) + float(x)
                if c:
                    byc[c] = byc.get(c, 0.0) + float(x)
        return {"by_commodity": byc, "by_feedstock": byf, "output": outp}
