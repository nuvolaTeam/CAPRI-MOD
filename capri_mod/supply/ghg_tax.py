"""CAPRI's emission tax in the supply models (ghgTax; supply/supply_model.gms objective, pol_input/ecampa/
carbtax50_endotech_set*.gms; Sprint 9i).

CAPRI prices agricultural greenhouse gases inside each regional supply model when a scenario switches the tax on
(%ghgTax% on): the objective carries - p_carbonTax(r, "GGWP") x (v_CO2EquEmis(r, "GGWP") - reference emissions),
EUR per t CO2-eq on the region's global-warming emissions, EU regions only (msNoEU excluded). Emissions are
variables of the supply model (activities, feeding, mitigation options), so the tax works on herd and crop levels,
rations and technology adoption at once; the reference emissions are a constant (a tax beyond, a subsidy below the
reference) and do not move the optimum.

The model's emissions are the environmental module's accounts (EnvironmentalModule.compute_indicators). The tax
enters the regional problem as each column's emission per unit, taken at the baseline solution:

  activities, CAPRI's intensity splits (grassland, dairy, bulls and heifers), breeding / low-N feed / supplement
      options, histosol fallowing: the change of the region's GHG total per unit of the column, by finite
      differences of the accounts at the baseline (one unit = 1000 ha or 1000 heads, so kt per unit = t per ha or
      head);
  feeding (cattle, CAPRI's feed-based CH4ENT, gases.gms GWPCH4ENT_): per t of each flexible feed fed, its dry
      matter x GE x 4.1868 x Ym / 55.65 x GWP(CH4); the fixed feeds' CH4 per head goes with the animal (the
      accounts' finite difference holds the animals' feed, so their enteric CH4 is not counted twice).

  ammonia options (Sprint 9k): manure N2O per unit of option share through the accounts' loss cascade ("mtech"),
      plus, in the supply model, the indirect N2O of the NH3 kept and the soil N2O of the mineral N it displaces;
  manure trade (Sprint 9k): the mineral N bought by the exporter, saved by the importer (sub x soil N2O per t N),
      in the supply model.

Registered: the coefficients are held at the baseline solution (the accounts are close to linear: per-head and
per-ha factors; the mineral N2O follows the balance's substitution); the fertiliser options and land-market columns
carry no emission coefficient of their own (their effects reach the GHG total through mineral N in the accounts, not
in the tax).
"""
from __future__ import annotations

import copy
from typing import Dict, Optional

import numpy as np
from capri_mod.params import param, param_table
from capri_mod.data.definitions import capri_ms

#: MJ per Mcal, MJ per kg CH4 (IPCC 2006 Eq. 10.21, as gases.gms and the accounts)
MJ_PER_MCAL = 4.1868                       # unit conversion
MJ_PER_KG_CH4 = param("MJ_PER_KG_CH4")


def _ghg_total(env, res) -> float:
    """CAPRI's GGWP, the tax base: CH4 + N2O + CO2 from liming (supply_model.gms GWPTOT_, GWPCO2_ - CO2 from urea
    is reported, not taxed)."""
    ind = env.compute_indicators(res)
    return float(ind.ghg_ggwp)


def _enteric_per_t_dm(env, region: str, animal: str) -> Optional[Dict[str, float]]:
    """t CO2-eq per t of dry matter of each feed group fed to a cattle animal (None for other animals)."""
    from capri_mod.environmental.environmental_module import GWP_CH4
    fac = env._enteric_factors().get(animal)
    if not fac:
        return None
    ctry = capri_ms(region)
    ge = fac["ge"].get(ctry) or fac["ge"].get("EU")
    if not ge:
        return None
    k = MJ_PER_MCAL * float(fac["ym"]) / MJ_PER_KG_CH4 * GWP_CH4
    return {f: float(v) * k for f, v in ge.items()}


def ghg_coefficients(env, region: str, res, rations: Optional[dict]) -> dict:
    """Emission per unit of each regional column at the baseline solution (t CO2-eq per unit).

    Returns {"act": {activity: e}, "grass": e, "dairy": e, "cattle": {animal: e}, "genet": {(animal, option): e},
    "hist": {class: e}, "feed": {(animal, feed): e per t fresh matter of a flexible feed}}."""
    out = {"act": {}, "grass": 0.0, "dairy": 0.0, "cattle": {}, "genet": {}, "hist": {}, "feed": {}}
    g0 = _ghg_total(env, res)
    acts = res.activities

    def diff(mutate, h):
        r1 = copy.copy(res)
        mutate(r1, h)
        return (_ghg_total(env, r1) - g0) / h

    for a in acts.index:
        x = float(acts.get(a, 0.0) or 0.0)
        h = max(0.01 * abs(x), 0.01)

        def m(r1, h_, a=a):
            r1.activities = acts.copy()
            r1.activities[a] = float(acts[a]) + h_
        out["act"][a] = diff(m, h)
    for fld, key in (("grass_ext_shift", "grass"), ("dairy_low_shift", "dairy")):
        def m(r1, h_, fld=fld):
            setattr(r1, fld, float(getattr(res, fld, 0.0) or 0.0) + h_)
        out[key] = diff(m, 0.01)
    for fld, key in (("cattle_shift", "cattle"), ("genetics_shift", "genet"), ("histosol_fallow", "hist")):
        base = dict(getattr(res, fld, None) or {})
        keys = set(base)
        if fld == "genetics_shift":
            keys |= set(((env.data.get("genetics_effects") or {}).get(region) or {}).keys())
        if fld == "histosol_fallow":
            keys |= {"crop", "grass"}
        if fld == "cattle_shift":
            # the cattle splits' keys; the member splits ("HFRS:rep", "CALV:male", ...) only when they are on
            from capri_mod.supply.supply_module import RegionalSupplyModel as _RSM
            _ms = bool(getattr(_RSM, "use_cattle_member_splits", False))
            keys |= {k for k in ((env.data.get("cattle_intensity") or {}).get(region) or {}) if _ms or ":" not in k}
        for k in keys:
            def m(r1, h_, fld=fld, k=k, base=base):
                d = dict(base)
                d[k] = float(d.get(k, 0.0) or 0.0) + h_
                setattr(r1, fld, d)
            out[key][k] = diff(m, 0.01)
    # CAPRI's ammonia options (Sprint 9k): manure N2O per unit of an animal's option share, through the accounts'
    # loss cascade (housing/storage and application N2O on the N left after NH3 losses), per 1000 heads - so per
    # unit of the regional model's M (share x heads). The NH3 kept and the mineral N it displaces are priced in the supply
    # model from the option's own N saving (SupplyModel._tech_list).
    out["mtech"] = {}
    try:
        eff, s0 = env._manure_n2o_tech(region)
    except Exception:
        eff, s0 = {}, {}
    base_sh = dict(getattr(res, "manure_tech_shares", None) or {})
    for a in set(eff or {}) | set(s0 or {}):
        x = float(acts.get(a, 0.0) or 0.0)
        if x <= 1e-6:
            continue
        for t in set((eff or {}).get(a) or {}) | set((s0 or {}).get(a) or {}):
            def m(r1, h_, a=a, t=t):
                d = dict(base_sh)
                d[(a, t)] = float(d.get((a, t), (s0.get(a) or {}).get(t, 0.0)) or 0.0) + h_
                r1.manure_tech_shares = d
            out["mtech"][(a, t)] = diff(m, 0.01) / x
    # cattle feeding: flexible feeds per t fresh matter on the feed columns; the fixed feeds per head on the animal
    for a, r in (rations or {}).items():
        e_dm = _enteric_per_t_dm(env, region, a)
        if not e_dm:
            continue
        fixed = 0.0
        for j, f in enumerate(r.feeds):
            e = float(e_dm.get(f, e_dm.get("_mean", 0.0))) * float(r.dm[j])        # t CO2-eq per t FM
            if r.flex[j]:
                out["feed"][(a, f)] = e
            else:
                fixed += e * float(r.x0[j]) / 1000.0                               # kg FM per head -> t
        if a in out["act"]:
            out["act"][a] += fixed
    return out
