"""CAPRI's ammonia technologies (v_Miti for NH3MAN and NH3APP) for one animal category of a region.

Data: capri_data/2017/abatement/ammonia/ammonia_tech_model.csv (tools/build_ammonia_tech_model.py),
one block per CAPRI sub-activity (e.g. DCOL and DCOH under the model's DCOW).

CAPRI's structure, reproduced here (supply/supply_model.gms, envind/ammo_tech.gms):

* TotMit_: the manure-management options (housing, storage covers, air purification,
  acidification and their combinations) are alternatives of one target, NH3MAN; with
  'no control' their shares sum to 1. The application options form NH3APP likewise.
* Emissions cascade through the stages (HOUSN_, STORN_, application): per unit of excreted N,
  grazing g fG; housing h = (1 - g) fH (1 - rH); storage ((1 - g) - h) fS (1 - rS);
  application (what is left) fA (1 - R_A), with rH, rS the option's cuts and R_A = sum over
  application options of share x cut. Manure-management options mix linearly (alternative
  systems); application interacts with them through the N reaching the field.
* Cost per animal place (GHG_Mit_Cost_ with CAPRI's calibration): marginal cost of share s
  is thresh + slope (s - ini); thresh is the early-adopter subsidy S0 (non-zero only for
  options not used at base), so the base shares are optimal at the base value of N.

Under a nitrogen-balance price lam (EUR/kg N = kEUR/t), retained N saves mineral fertiliser
(substitution factor sub); its value per animal place for option t is
lam x sub x (N saved per unit of share) / places per unit. Shares follow from the first-order
conditions with the group limit's multiplier (bisection), alternating between the two groups
(their only link is the N reaching the field) until stable.

REGISTERED: N2, N2O and NOx are not subtracted in the cascade (CAPRI subtracts them); the
other gases' side effects are not passed to the accounts.
"""
from __future__ import annotations

import csv
from pathlib import Path

_CACHE = {}


def load(path: Path) -> dict:
    """{region: {animal: [sub, ...]}}, sub = dict(key, w, stock, mrel, g, fG, fH, fS, fA, techs=[...])."""
    key = str(path)
    if key in _CACHE:
        return _CACHE[key]
    out = {}
    if path.exists():
        with open(path) as fh:
            for r in csv.DictReader(fh):
                subs = out.setdefault(r["region"], {}).setdefault(r["animal"], {})
                s = subs.get(r["sub"])
                if s is None:
                    s = subs[r["sub"]] = dict(key=r["sub"], w=float(r["weight"]), stock=float(r["stock_factor"]),
                                              mrel=float(r["mann_rel"]), g=float(r["g"]), fG=float(r["fG"]),
                                              fH=float(r["fH"]), fS=float(r["fS"]), fA=float(r["fA"]), techs=[])
                s["techs"].append(dict(tech=r["technology"], group=r["group"], k1=float(r["kappa1"]),
                                       slope=float(r["slope"]) if r["slope"] not in ("", None) else None,
                                       th=float(r["thresh"] or 0.0), ini=float(r["ini"]), max=float(r["max"]),
                                       rH=float(r["rH"]), rS=float(r["rS"]), rA=float(r["rA"])))
        out = {reg: {a: list(d.values()) for a, d in an.items()} for reg, an in out.items()}
    _CACHE[key] = out
    return out


def _stage(sub, rH, rS):
    """Housing + storage loss and N reaching the field, per unit of excreted N (housed part)."""
    hm = 1.0 - sub["g"]
    h = hm * sub["fH"] * (1.0 - rH)
    s = (hm - h) * sub["fS"] * (1.0 - rS)
    return h + s, hm - h - s


def loss(sub, sh: dict) -> float:
    """NH3-N lost per unit of excreted N at shares sh {tech: share}."""
    RA = sum(sh.get(t["tech"], 0.0) * t["rA"] for t in sub["techs"] if t["group"] == "APP")
    man = [t for t in sub["techs"] if t["group"] == "MAN"]
    noc = 1.0 - sum(sh.get(t["tech"], 0.0) for t in man)
    L0, P0 = _stage(sub, 0.0, 0.0)
    L, P = noc * L0, noc * P0
    for t in man:
        s = sh.get(t["tech"], 0.0)
        if s:
            l_, p_ = _stage(sub, t["rH"], t["rS"])
            L += s * l_; P += s * p_
    return sub["g"] * sub["fG"] + L + P * sub["fA"] * (1.0 - RA)


def app_loss(sub, sh: dict) -> float:
    """NH3-N lost at field application per unit of excreted N at shares sh (the last term of
    loss): the base of the application side effects of manure options (NITR_INH_MAN)."""
    RA = sum(sh.get(t["tech"], 0.0) * t["rA"] for t in sub["techs"] if t["group"] == "APP")
    man = [t for t in sub["techs"] if t["group"] == "MAN"]
    noc = 1.0 - sum(sh.get(t["tech"], 0.0) for t in man)
    P = noc * _stage(sub, 0.0, 0.0)[1]
    for t in man:
        s = sh.get(t["tech"], 0.0)
        if s:
            P += s * _stage(sub, t["rH"], t["rS"])[1]
    return P * sub["fA"] * (1.0 - RA)


def stage_n(sub, sh: dict) -> tuple:
    """(housed N left after housing NH3, N left on the field after application NH3), per unit of
    excreted N at shares sh - the bases CAPRI applies its N2O loss factors to (supply_model.gms
    HOUSN_ "the N2O loss factor is applied after the losses of NH3 and NOX", APPLN_ likewise at
    application): NH3 kept by a technology flows on and raises N2O downstream."""
    RA = sum(sh.get(t["tech"], 0.0) * t["rA"] for t in sub["techs"] if t["group"] == "APP")
    man = [t for t in sub["techs"] if t["group"] == "MAN"]
    noc = 1.0 - sum(sh.get(t["tech"], 0.0) for t in man)
    hm = 1.0 - sub["g"]

    def one(rH, rS):
        h = hm * sub["fH"] * (1.0 - rH)
        p = _stage(sub, rH, rS)[1]
        return hm - h, p * (1.0 - sub["fA"] * (1.0 - RA))
    H, F = (noc * v for v in one(0.0, 0.0))
    for t in man:
        s_ = sh.get(t["tech"], 0.0)
        if s_:
            h_, f_ = one(t["rH"], t["rS"])
            H += s_ * h_; F += s_ * f_
    return H, F


def marginal(sub, sh: dict) -> dict:
    """d loss / d share for every option (negative: the option saves NH3), at shares sh."""
    RA = sum(sh.get(t["tech"], 0.0) * t["rA"] for t in sub["techs"] if t["group"] == "APP")
    man = [t for t in sub["techs"] if t["group"] == "MAN"]
    noc = 1.0 - sum(sh.get(t["tech"], 0.0) for t in man)
    L0, P0 = _stage(sub, 0.0, 0.0)
    P = noc * P0
    out = {}
    for t in man:
        l_, p_ = _stage(sub, t["rH"], t["rS"])
        P += sh.get(t["tech"], 0.0) * p_
        out[t["tech"]] = (l_ - L0) + (p_ - P0) * sub["fA"] * (1.0 - RA)
    for t in sub["techs"]:
        if t["group"] == "APP":
            out[t["tech"]] = -P * sub["fA"] * t["rA"]
    return out


def initial(sub) -> dict:
    return {t["tech"]: t["ini"] for t in sub["techs"]}


def _group_shares(techs, value: dict) -> dict:
    """FOC per option, s = ini + (value - thresh - mu) / slope in [0, max], mu >= 0 with sum <= 1."""
    def at(mu):
        o = {}
        for t in techs:
            if t["slope"] is None or t["slope"] <= 0:
                o[t["tech"]] = t["ini"]
            else:
                v = value.get(t["tech"], 0.0)
                # an option used at base has thresh 0; one not used at base starts above thresh
                o[t["tech"]] = min(max(t["ini"] + (v - t["th"] - mu) / t["slope"], 0.0), t["max"])
        return o
    o = at(0.0)
    if sum(o.values()) <= 1.0 + 1e-12:
        return o
    lo, hi = 0.0, max(value.values(), default=0.0) + max((t["slope"] or 0.0) for t in techs) + 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if sum(at(mid).values()) > 1.0:
            lo = mid
        else:
            hi = mid
    return at(hi)


def choose(sub, eur_per_n: float, n_per_unit_loss: float) -> dict:
    """Shares for one sub-activity. eur_per_n: value of one unit of N retained (lam x sub);
    n_per_unit_loss: N (t) per activity unit per unit of the loss fraction (excreted N x scale)."""
    sh = initial(sub)
    if eur_per_n <= 0 or n_per_unit_loss <= 0:
        return sh
    k = eur_per_n * n_per_unit_loss / max(sub["stock"], 1e-12)     # EUR per place per unit of loss
    for _ in range(20):
        prev = dict(sh)
        for grp in ("MAN", "APP"):
            d = marginal(sub, sh)
            techs = [t for t in sub["techs"] if t["group"] == grp]
            if techs:
                sh.update(_group_shares(techs, {t["tech"]: -k * d[t["tech"]] for t in techs}))
        if max(abs(sh[x] - prev[x]) for x in sh) < 1e-9:
            break
    return sh


def cost(sub, sh: dict) -> float:
    """Extra cost per animal place over the base shares (EUR)."""
    c = 0.0
    for t in sub["techs"]:
        if t["slope"] is None:
            continue
        d = sh.get(t["tech"], t["ini"]) - t["ini"]
        c += t["th"] * d + 0.5 * t["slope"] * d * d
    return c
