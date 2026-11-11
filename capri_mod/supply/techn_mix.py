"""CAPRI's two crop technologies T1 (high yield) and T2 (low yield) as mix columns (S1, docs/design/S1_MIX_COLUMNS.md).

For a crop a with both technologies in the region, the model's activity X and one column z, x_T1 = X/2 + z,
x_T2 = X/2 - z (z = 0 at CAPRI's 50-50 calibration point); -X/2 <= z <= X/2 as two rows. Per unit of z, the
differences T1 - T2 of what CAPRI's technology factors move (capri_data/baselines/capri_greendeal_ref/2017_2030/supply/techn_mix_2030.csv,
tools/build/build_techn_mix_2030.py): output +yield_diff x yield, the factored inputs' costs, plant protection, other
inputs, the fertiliser need (need_diff, NUTNED_'s SQRT(1 + y)(1 + y)) and the rural-development premiums; PMP CAPRI's
2x2 technology block in (X, z) (pmp_capri_2030_mix.csv: X's diagonal + g_xx_extra / x^2, the X-z and z-z terms).
The column's linear term is calibrated with the activities (CapriRegionalNLP.calibrate: not a free column), so the
base is a first-order point at z = 0, as CAPRI's p_pmpCnst per technology makes it.

On with supply.crop_technologies at the 2030 market year with CAPRI's 2030 PMP terms (the mix terms are CAPRI's 2030
calibration's); off, the model is the collapsed form (DEP-9).

RegionalSupplyModel's methods (refactor stage 3a pattern); the module-level names they use are supply_module's
(capri_mod.utils.mixins.inject_names).
"""
from __future__ import annotations

import numpy as np

#: the items of techn_mix_2030.csv that move a coefficient (a crop where all are 0 gets no column: with nothing
#: depending on z, z optimised out leaves X's curvature unchanged, the Schur complement)
MOVING = ("yield_diff", "need_diff", "rest_cost_diff_eur_ha", "inpo_diff", "plap_diff", "prem_diff_share")


class TechnMixBlock:
    def _mix_on(self) -> bool:
        tm = getattr(self.data, "techn_mix", None)
        return tm is not None and len(tm) > 0 and bool(_settings().get("supply.crop_technologies"))

    def _mix_rows(self, labels) -> dict:
        """{crop: row of techn_mix} of the crops that get a column in this solve: both technologies, a base level,
        a coefficient that moves, the crop neither held at its level (fixed_ rows: no own PMP term) nor absent."""
        if not self._mix_on():
            return {}
        tm = self.data.techn_mix
        base = self._base_levels()
        out = {}
        for a in tm.index:
            if a not in CROPS or a not in self.acts or f"fixed_{a}_up" in labels or f"bound_{a}_absent" in labels:
                continue
            if not float(base.get(a, 0.0) or 0.0) > 1e-6:
                continue
            r = tm.loc[a]
            if any(float(r[k]) != 0.0 for k in MOVING) and float(r["g_zz"]) > 0:
                out[a] = r
        return out

    def _mix_linear(self, a, r) -> float:
        """The column's linear objective coefficient: minus the net revenue of T1 less T2 per ha, at this solve's prices,
        yields and Green Deal input costs, as the crop's own (the revenue p x y, the factored inputs, plant protection
        and other inputs with their Green Deal changes, the fertiliser cost x need_diff, the premium x
        prem_diff_share)."""
        ps = getattr(self.ev, "price_shock_now", None)
        p = float(self.data.producer_prices.get(a, 0.0) or 0.0)
        if ps is not None and hasattr(ps, "get"):
            p *= 1.0 + float(ps.get(a, 0.0) or 0.0)
        y = float(self.data.yields.get(a, 0.0) or 0.0) if hasattr(self.data.yields, "get") else 0.0
        d_p, d_i = (getattr(self.ev, "greendeal_crop_delta", None) or {}).get(a, (0.0, 0.0))
        plap = (self._input_row(a, "plap_eur_ha") or 0.0) + d_p
        inpo = (self._input_row(a, "inpo_eur_ha") or 0.0) + d_i
        oc = float((getattr(self.ev, "organic_conv", None) or {}).get(a, 1.0))
        fert = float(self._input_cost(a, "fert", self.FERT_COST_SHARE)) * oc
        prem = float(self.premiums.get(a, 0.0) or 0.0) if getattr(self, "premiums", None) is not None else 0.0
        dnr = (float(r["yield_diff"]) * p * y - float(r["rest_cost_diff_eur_ha"]) - float(r["inpo_diff"]) * inpo
               - float(r["plap_diff"]) * plap - float(r["need_diff"]) * fert + float(r["prem_diff_share"]) * prem)
        return -dnr

    def _mix_fert_cost(self, a, r) -> float:
        """The column's fertiliser cost per unit (need_diff x the crop's), which the NLP form takes out of the linear
        term as it does for the crop (the purchases are priced in the fertilisation block)."""
        oc = float((getattr(self.ev, "organic_conv", None) or {}).get(a, 1.0))
        return float(r["need_diff"]) * float(self._input_cost(a, "fert", self.FERT_COST_SHARE)) * oc

    def _mix_n_terms(self, a, r):
        """(N surplus, mineral N input) of T1 less T2 per ha, from the environmental accounts' unit balance (the
        function the N_balance and mineral_N rows are built from) at the technologies' yields, y (1 +- yield_diff / 2);
        (0, 0) without the accounts."""
        env_ = getattr(self.seen, "env_for_surplus", None)
        yc = self.data.yields
        if env_ is None or not hasattr(yc, "copy") or a not in yc:
            return 0.0, 0.0
        mint = dict(getattr(self.ev, "n_intensity", {}) or {})
        mi = {k_: v_ for k_, v_ in mint.items() if k_ in (a, "__credit__")}
        ys0 = self._yields_scen_now()
        h = 0.5 * float(r["yield_diff"])
        out = []
        for f in (h, -h):
            y_ = yc.copy(); y_[a] = float(yc[a]) * (1.0 + f)
            ys_ = None
            if ys0 is not None:
                ys_ = dict(ys0) if isinstance(ys0, dict) else ys0.copy()     # a dict or a Series of yields
                if a in ys_:
                    ys_[a] = float(ys_[a]) * (1.0 + f)
            u = env_.unit_nitrogen_balance(a, y_, self.data.region_id, mi, yields_scen=ys_)
            out.append((float(u.get("n_surplus", 0.0)), float(u.get("n_mineral_input", 0.0))))
        return out[0][0] - out[1][0], out[0][1] - out[1][1]

    def _mix_columns(self, Qa, ca, Aa, ba, start, labels, n):
        """Append the mix columns (after the histosol columns): PMP, linear term, the bound rows z - X/2 <= 0 and
        -z - X/2 <= 0, and the rows z enters: fodder (yield_diff x the crop's u), crop_need (need_diff x the crop's),
        N_balance and mineral_N (the unit balances' T1 - T2, _mix_n_terms)."""
        self.ev.mix_cols = {}
        self.ev.mix_n_min = {}
        self.ev.mix_dnr = {}
        rows = self._mix_rows(labels)
        if not rows:
            return Qa, ca, Aa, ba, start
        base = self._base_levels()
        acts = list(self.acts)
        i_nb = labels.index("N_balance") if "N_balance" in labels else None
        i_mn = labels.index("mineral_N") if "mineral_N" in labels else None
        mcap = getattr(self.ev, "mineral_cap", None) or {}
        fod = [i for i, l in enumerate(labels) if l.startswith("fodder_")]
        i_cn = labels.index("crop_need") if "crop_need" in labels else None
        for a, r in rows.items():
            j = acts.index(a)
            x0 = float(base[a])
            col = np.zeros(Aa.shape[0])
            for i in fod:
                if Aa[i, j] != 0.0:
                    col[i] = float(r["yield_diff"]) * float(Aa[i, j])
            if i_cn is not None and Aa[i_cn, j] != 0.0:
                col[i_cn] = float(r["need_diff"]) * float(Aa[i_cn, j])
            if i_nb is not None or i_mn is not None:
                d_s, d_m = self._mix_n_terms(a, r)
                if i_nb is not None:
                    col[i_nb] = d_s
                    self.ev.mix_n_min[a] = d_m
                if i_mn is not None:
                    col[i_mn] = float((mcap.get("capped_share") or {}).get(a, 0.0)) * d_m
            Aa = np.hstack([Aa, col[:, None]])
            k = Aa.shape[1] - 1
            up = np.zeros(Aa.shape[1]); up[k] = 1.0; up[j] = -0.5
            lo = np.zeros(Aa.shape[1]); lo[k] = -1.0; lo[j] = -0.5
            Aa = np.vstack([Aa, up, lo]); ba = np.concatenate([ba, [0.0, 0.0]])
            labels.extend([f"mix_{a}_up", f"mix_{a}_lo"])
            Qa = np.pad(Qa, ((0, 1), (0, 1)))
            Qa[j, j] += float(r["g_xx_extra"]) / x0 ** 2
            Qa[j, k] = Qa[k, j] = float(r["g_xz"]) / x0 ** 2
            Qa[k, k] = float(r["g_zz"]) / x0 ** 2
            c_z = self._mix_linear(a, r)
            self.ev.mix_dnr[a] = -c_z
            ca = np.concatenate([ca, [c_z]])
            start = np.concatenate([start, [0.0]])
            self.ev.mix_cols[a] = k
        return Qa, ca, Aa, ba, start

    def _mix_record(self, y) -> None:
        """z of the mix columns from a solution vector (1000 ha moved from T2 to T1)."""
        self.res.last_mix_z = {a: float(y[k]) for a, k in (getattr(self.ev, "mix_cols", None) or {}).items()
                               if k < len(y)}
