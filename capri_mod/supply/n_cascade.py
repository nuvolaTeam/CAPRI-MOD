"""The data of CAPRI's nitrogen loss cascade (tools/build/build_n_cascade.py: p_Nemidat, the options' effects) and its
use for one CAPRI region and animal activity (activity_losses) and for the accounts (mineral_n2o_n). CAPRI's equations
of the cascade (GRAZN_, HOUSN_, STORN_, RUNHOUSN_, RUNSURFN_, APPLN_, RUNTOTN_, GASRUNTOTN_, GASTOTNETF_, RUNTOTNETF_,
GASRUNTOTNETF_) are in capri_mod/supply/equations/supply_model/n_flow.py (until 19 November 2026 here);
docs/dev/N_CASCADE_SPEC.md has the factors with their sources.
"""
from __future__ import annotations

from capri_mod.params import param
from capri_mod.supply.equations.supply_model.n_flow import losses, netf


def mineral_n2o_n(fr, ef4):
    """CAPRI's soil N2O of mineral fertiliser per unit of mineral N, as N2O-N (envind/gases.gms (7) N2OSYN and the
    mineral part of (9) N2OAMM): direct emiLoss(NETF, N2O, GasTot) and indirect (emiLoss(NETF, NH3) + emiLoss(NETF,
    NOx)) x EF4, from the region's MITERRA fractions (netf; before the fertiliser options' side effects, which the
    accounts apply as factors). Returns (direct, indirect); None without the region's fractions."""
    if not fr or "netf_N2O" not in fr:
        return None
    L = netf(fr, 0.0)
    return float(L["N2O"]), float(L["NH3"] + L["NOX"]) * float(ef4)


_DATA = {}


def load(data_dir=None):
    """The cascade's data (tools/build/build_n_cascade.py): (factors {(region, act): {factor: v}}, regional
    {region: {factor: v}}, effects {(region, act): {(tech, item): v}}), CAPRI regions (8 characters)."""
    from capri_mod.supply.inputs import SupplyInputs, current
    inp = SupplyInputs(data_dir, current().base_year) if data_dir else current()
    key = str(inp.path("", "abatement/ammonia"))
    if key not in _DATA:
        F, G, E = {}, {}, {}
        for r in inp.rows("n_cascade_factors.csv", "abatement/ammonia"):
            F.setdefault((r["region"], r["activity"]), {})[r["factor"]] = float(r["value"])
        for r in inp.rows("n_cascade_region.csv", "abatement/ammonia"):
            G.setdefault(r["region"], {})[r["factor"]] = float(r["value"])
        for r in inp.rows("n_cascade_effects.csv", "abatement/ammonia"):
            E.setdefault((r["region"], r["activity"]), {})[(r["technology"], r["item"])] = float(r["value"])
        _DATA[key] = (F, G, E)
    return _DATA[key]


# winter cover's effect on runoff and leaching (envind/cover_crops.gms l. 400-402, endoLeach on): the parameter
# WINTERCOV_NO3_REDUCTION


def activity_losses(region, act, shares, winter_cover=0.0, data_dir=None):
    """losses() for a CAPRI region (8 characters) and animal activity with its option shares and the region's winter
    cover share (CAPRI's other crop options' runoff effects are 0 or not modelled: tillage's no3mrun is commented out
    in envind/tillage.gms l. 561-566; buffer strips, biodiversity options and fertiliser techniques are not in
    capri-mod)."""
    F, G, E = load(data_dir)
    f = F[(region, act)]
    wc = 1.0 - param("WINTERCOV_NO3_REDUCTION") * winter_cover
    return losses(f, G.get(region, {}).get("run_surf", 0.0), shares, E.get((region, act), {}),
                  m_runsurf=(wc, 1.0), m_appl_run=wc)
