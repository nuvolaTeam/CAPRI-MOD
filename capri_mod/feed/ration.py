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
from capri_mod.params import param, param_table
from capri_mod.data.definitions import capri_ms

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
#: (sows 0.3, fattening pigs 0.2: PIGS = sows and PIGF = fattening since the pig split), energy-rich
#: 0.05-0.15, no fodder; other feeds >= 0.005 (0.001 sheep, suckler cows).
#: CAPRI's data-driven rules are applied in share_rules through ctx: the maximum 'other' feed share from the
#: member state's feed balance (foth_max) and the minimum fibre-rich shares from the region's fodder energy
#: shares (fibre_share x _FIBRE_FACTOR).
_RUMI = ("DCOW", "BCOW", "BULL", "HFRS", "CALV", "SHGM", "SHGF")
_NRUMI = ("PIGS", "PIGF", "BROI", "LAYS")
_FODDI = ("FGRA", "FMAI", "FOFA", "FROO", "FCOM", "FSGM", "FSTR")


_FIBRE = ("FOFA", "FGRA", "FMAI")              # CAPRI fibreRichFeed (without straw)
#: CAPRI factor x regional fodder-energy share = minimum share of each fibre feed;
#: the model's calves (raising + fattening: 0.4 / 0.2) and sheep and goats
#: (milk + fattening: 0.8 / 0.5) take the mean factor (REGISTERED)
_FIBRE_FACTOR = param_table("FIBRE_FACTOR")


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
        # CAPRI: 0.2 for monogastrics, 0.3 for sows (PIGS, since the pig split)
        setr("FPRO", hi=0.3 if act == "PIGS" else 0.2); setr("FCER", lo=0.6); setr("FENE", lo=0.05, hi=0.15)
        for f in _FODDI:
            setr(f, hi=0.0)
    if act in ("DCOW", "BULL", "CALV"):
        setr("FCER", lo=0.20); setr("FPRO", lo=0.10)
    if act == "HFRS":
        setr("FCER", lo=0.05); setr("FPRO", lo=0.05)
    if act == "BCOW":
        setr("FCER", lo=0.05)
    setr("FOTH", lo=0.001 if act in ("SHGM", "SHGF", "BCOW") else 0.005)
    # --- data-driven rules
    fs = ctx.get("fibre_share") or {}
    if act in _FIBRE_FACTOR and fs:
        for f in _FIBRE:
            if fs.get(f, 0.0) > 0:
                setr(f, lo=_FIBRE_FACTOR[act] * fs[f])
    if act in _RUMI and ctx.get("straw"):
        setr("FSTR", lo=0.01, hi=0.05)
    if act in ("SHGM", "SHGF"):
        for f in ("FCER", "FPRO", "FENE", "FOTH", "FMIL", "FROO", "FSTR", "FCOM"):
            a, b = r.get(f, (0.0, 1.0)); r[f] = (a, min(b, 0.20))
    if act == "CALV":
        setr("FMIL", lo=0.05); setr("FCOM", lo=0.10, hi=1.0)
    elif act in ("BULL", "HFRS"):
        setr("FCOM", hi=0.01)
    elif act in ("DCOW", "BCOW"):
        setr("FCOM", hi=0.0)
    if act not in ("SHGM", "SHGF"):
        setr("FSGM", hi=0.0)
    fm = ctx.get("foth_max")
    if fm:
        setr("FOTH", hi=min(1.0, fm * (2.0 if act in _RUMI else 1.0)))
    return r


#: feed groups whose price follows the market: CAPRI's tradable bulks (FEED_TRD)
MARKET_FEEDS = ("FCER", "FPRO", "FENE", "FOTH", "FMIL")


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


# ---- NITRATE FEED ADDITIVE (CAPRI envind/line_nitr.gms) ------------------------
# A ration ingredient: 1% nitrate in dry matter supplies 1.54% crude protein
# (0.246 N x 6.25), raises N excretion (+0.42% of DM intake at 1.5% dosage) and cuts
# enteric CH4 by 10% per point of DM. Maximum dosage 1.5% of DM (replacement heifers
# 1%), applied only in stables: dairy cows 10/12 of stable time (lactation), fattening
# bulls and heifers 1/2; never calves or suckler cows. Price 873 EUR/t (base year;
# CAPRI inflates to the simulation year - REGISTERED: not inflated). Linseed and 3-NOP
# only cut methane, worthless without a carbon price, so not in the ration (yet).
NITRATE = "NITR"
NITR_PRICE = param("NITR_PRICE")          # EUR/kg
NITR_CP = param("NITR_CP")                # kg crude protein per kg nitrate
NITR_N_EXCR = param("NITR_N_EXCR")        # kg N excreted per kg nitrate
NITR_RULES = {a: (d, param_table("NITR_STABLE_TIME")[a]) for a, d in param_table("NITR_MAX_DOSE").items()}
_STABLE = None


def stable_share(region: str, act: str) -> float:
    """Share of the year in stables: 1 - grazing, grazing = (1 - HD/365)(1 - Et/100)
    (MITERRA RCEmissions, CAPRI's default path; as in the ammonia technologies)."""
    global _STABLE
    if _STABLE is None:
        import csv as _csv
        _STABLE = {}
        f = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "ammonia" / "RCEmissions.csv"
        if f.exists():
            for r in _csv.DictReader(open(f)):
                _STABLE[(r["region"], r["animal_mitt"], r["item"])] = float(r["value"])
    ctry = capri_ms(region)
    cat = "DAICOW_S" if act == "DCOW" else "OCOW_S"
    hd, et = _STABLE.get((ctry, cat, "HD")), _STABLE.get((ctry, cat, "Et"))
    if hd is None:
        return 0.0
    graz = max(0.0, (1 - hd / 365.0) * (1 - (et or 0.0) / 100.0))
    return max(0.0, 1.0 - graz)


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
        # nitrate as an ingredient (zero in the base ration)
        act_, reg_ = rec.get("_act"), rec.get("_region")
        self.nitr_max = 0.0
        if rec.get("_use_nitrate", False) and act_ in NITR_RULES and reg_:
            dose, months = NITR_RULES[act_]
            self.nitr_max = dose * months * stable_share(reg_, act_)
            if self.nitr_max > 0:
                self.feeds.append(NITRATE)
                x0 = np.append(x0, 0.0); e = np.append(e, 0.0); cp = np.append(cp, NITR_CP)
                dm = np.append(dm, 1.0); p0 = np.append(p0, NITR_PRICE); flex = np.append(flex, True)
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
        if self.nitr_max > 0:
            self.shares.append((self.feeds.index(NITRATE), "max", self.nitr_max))
        # feed PMP slope
        eps = np.array([abs(FEED_ELAS.get(f, 1.0)) for f in self.feeds])
        # price per kg, at least 10% of the cereal price: CAPRI supply/pmp_terms/define_const_pmp_param.gms l. 107-110,
        # MAX(0.1*DATA(MS,"UVAG","FCER","Y")/1000, DATA(MS,"UVAG",FEED,"Y")/1000). The quantity CAPRI divides by
        # (l. 111-114: max of 10% of the dry-matter requirement and the feeding) is not reconstructed here; this slope
        # is used only where CAPRI's own calibrated slope is missing (135 cells of FSTR, FCOM, FROO, FSGM and FGRA in
        # 14 regions; PROXY_AUDIT S209)
        peff = np.maximum(p0, 0.1 * cereal_price)
        xref = np.maximum(x0, 1e-9)
        own = peff / (eps * xref)
        # CAPRI's OWN calibrated slope where available (pmppar p_pmpFeedInpCoeff,
        # aggregated by tools/build/build_feed_ration.py); the reconstruction of its
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
        if NITRATE in self.feeds:
            j = self.feeds.index(NITRATE)
            # tiny curvature only for numerical stability (CAPRI: pmpParSqr = 0)
            dmi = float(dm[:j] @ x0[:j]) if j > 0 else 1.0
            self.slope[j] = 1e-6 * NITR_PRICE / max(self.nitr_max * dmi, 1e-6)
            # zero nitrate optimal at base: p + cnst >= shadow at x = 0 (never a gain)
            self.cnst[j] = max(0.0, float(shadow[j]) - NITR_PRICE)


class RationModel:
    #: nitrate as a ration ingredient (CAPRI line_nitr.gms); OFF until its methane and
    #: N-excretion effects reach the emission accounts and the nitrogen balance
    use_nitrate = False

    """All EU region-animal rations, from feed_ration_2017.json."""

    def __init__(self, data_dir: str | Path = None, scale: dict = None, price_scale: dict = None,
                 factor: dict = None, slope_key: str = "capri_slope"):
        """scale: {(region, animal): (f_energy, f_protein, f_dry_matter)} - requirements of a projected year
        (capri_mod/projection: output per head follows the projected yield); the base ration is scaled by
        the largest factor so it stays feasible, and the ration is calibrated to it."""
        root = Path(data_dir) if data_dir else Path(__file__).resolve().parents[2] / "capri_data"
        f = root / "2017" / "feed" / "feed_ration_2017.json"
        raw = json.load(open(f))["regions"] if f.exists() else {}
        self.rations = {}
        ctx = self._contexts(root, raw)
        scale = scale or {}
        price_scale = price_scale or {}
        for reg, acts in raw.items():
            # purchased feed bulks at a projected year's prices: {(member state, bulk): factor} (projection/prices.py)
            _ms = capri_ms(reg)
            for act, rec in acts.items():
                if slope_key != "capri_slope" and rec.get(slope_key):
                    # CAPRI's feed-PMP slopes of another calibration point (capri_slope_2030: its 2030 baseline)
                    rec = dict(rec, capri_slope=rec[slope_key])
                if price_scale:
                    rec = dict(rec, price={f: float(v) * float(price_scale.get((_ms, f), 1.0))
                                           for f, v in rec["price"].items()})
                pc = float(rec["price"].get("FCER", 0.0))
                if not pc > 0:                             # no stand-in (removed 23 October 2026: 0.2)
                    raise ValueError(f"{reg} {act}: no FCER price in the ration data")
                sc = scale.get((reg, act))
                fx = (factor or {}).get((reg, act))
                if fx:
                    # CAPRI's projected ration and requirements (projection: capri_ref_ration_2030.csv): each feed and
                    # requirement by its own factor; the ration is lifted uniformly where it would fall short of the
                    # energy or protein requirement (the rule of the uniform scaling below), so it stays feasible
                    req = dict(rec["req"])
                    for q in ("ENNE", "CRPR", "DMIN", "DMAX"):
                        if float(req.get(q, 0.0) or 0.0) > 0:
                            req[q] = float(req[q]) * float(fx.get("req_" + q, 1.0))
                    ration = {k: float(v) * float(fx.get(k, 1.0)) for k, v in rec["ration"].items()}
                    lift = 1.0
                    for q in ("ENNE", "CRPR"):
                        sup = sum(x * float(rec["content"][k][q]) for k, x in ration.items())
                        if float(req.get(q, 0.0) or 0.0) > 0 and sup > 0:
                            lift = max(lift, float(req[q]) / sup)
                    rec = dict(rec, req=req, ration={k: v * lift for k, v in ration.items()})
                    sc = None
                if sc:
                    fe, fp, fd = (float(x) for x in sc)
                    s_ = max(fe, fp)
                    req = dict(rec["req"])
                    req["ENNE"] = float(req.get("ENNE", 0.0)) * fe
                    req["CRPR"] = float(req.get("CRPR", 0.0)) * fp
                    if float(req.get("DMIN", 0.0) or 0.0) > 0:
                        req["DMIN"] = float(req["DMIN"]) * fd
                    if float(req.get("DMAX", 0.0) or 0.0) > 0:
                        req["DMAX"] = float(req["DMAX"]) * fd
                    rec = dict(rec, req=req, ration={k: float(v) * s_ for k, v in rec["ration"].items()})
                rec = dict(rec, _act=act, _ctx=ctx.get(reg))
                rec["_region"] = reg
                rec.setdefault("_act", act)
                rec["_use_nitrate"] = bool(getattr(type(self), "use_nitrate", False))
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

    def price_vector(self, key, cereal_index: float = 1.0, protein_index: float = 1.0, bulk_ratio=None):
        """Feed prices for one ration: base prices with the market's feed bulks scaled by their price indices
        (CAPRI feedBlkPrice_ of the member state: FCER, FPRO, FENE, FOTH, FMIL; bulk_ratio {bulk: index}, else the
        cereal and protein indices given); on-farm fodder at its base price here (the model values it at its
        balance shadow price separately)."""
        r = self.rations[key]
        p = r.p0.copy()
        br = dict(bulk_ratio) if bulk_ratio is not None else {"FCER": cereal_index, "FPRO": protein_index}
        for i, f in enumerate(r.feeds):
            if f in br:
                p[i] *= float(br[f])
        return p
