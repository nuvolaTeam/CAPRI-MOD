"""CAPRI's endogenous-technology settings: scenario configuration parameters shared by the reference and the
policy run.

In CAPRI a scenario file (pol_input/greendeal/greendeal_scenarios.gms) loads the reference technology file
(refScenMain = pol_input/greendeal/refpol_endotech_all_sup), which sets the technology parameters with
"$if not SETGLOBAL <name> $SETGLOBAL <name> <default>": a value given when the run is launched wins, otherwise
the file's default applies. Because the scenario file loads the reference file, the same values hold in the
reference run and in the policy run; a policy effect is always measured with one set of technologies.

The model follows that: a PolicyScenario carries ``endotech`` overrides, CapriModel.run applies the effective
settings to the scenario AND to the baseline it compares against (the baseline cache is keyed by them).

Settings (refpol_endotech_all_sup.gms):
  ghgTechMYld  accelerated catching up of milk yields (envind/breeding.gms genet_yld); star 3.0 default 0
               (option off). CAPRI's older ecampa reference files (refpol_endotech_set14_ini.gms) set 0.2, the
               value behind JRC121368 Table 17 (genomics on 15% of dairy cows).
  ghgTechFEff  lower energy need of beef cattle and sheep (genet_eff); default 0.1.
  ghgTechLowNFeed  low-nitrogen feeding (envind/low_n_feed.gms lowNFeed): rations cut toward the protein
               requirement; default 1 (option on), as in the JRC121368-era references (Sprint 9g).
  ghgTechLineNitr  the feed supplements linseed and nitrate (envind/line_nitr.gms LINE_Tot, Nitr_Tot): a switch
               (capmod.gms includes line_nitr.gms unless it is 0); default 1, also in the JRC121368-era references
               (pol_input/ecampa/refpol_endotech_set14_ini.gms) (Sprint 9g).
"""
from __future__ import annotations
from typing import Dict, Mapping, Optional

import pandas as pd

#: CAPRI star 3.0 defaults (pol_input/greendeal/refpol_endotech_all_sup.gms)
STAR3_DEFAULTS: Dict[str, float] = {"ghgTechMYld": 0.0, "ghgTechFEff": 0.1, "ghgTechLowNFeed": 1.0,
                                    "ghgTechLineNitr": 1.0}
#: the setting of CAPRI's JRC121368-era endotech references (pol_input/ecampa/refpol_endotech_set14_ini.gms)
JRC121368_ENDOTECH: Dict[str, float] = {"ghgTechMYld": 0.2, "ghgTechFEff": 0.1, "ghgTechLowNFeed": 1.0,
                                        "ghgTechLineNitr": 1.0}

_SCALED = ("d_milk_rel", "d_ener_rel", "d_crpr_rel", "d_drmn_rel", "d_drmx_rel", "d_mann_rel")


def effective(*overrides: Optional[Mapping[str, float]]) -> Dict[str, float]:
    """Defaults, then each override in turn (launch-time settings win, as $if not SETGLOBAL)."""
    out = dict(STAR3_DEFAULTS)
    for o in overrides:
        for k, v in (o or {}).items():
            if k not in STAR3_DEFAULTS:
                raise KeyError(f"unknown endogenous-technology setting {k!r}; known: {sorted(STAR3_DEFAULTS)}")
            out[k] = float(v)
    return out


def key(settings: Mapping[str, float]) -> tuple:
    return tuple(sorted((k, float(v)) for k, v in settings.items()))


def scale_genetics(unit: Optional[dict], settings: Mapping[str, float]) -> Optional[dict]:
    """{region: {(animal, option): Series per unit of tech_param}} -> effects at the settings: the d_* columns
    times the parameter, cost_eur_head = max(cost_floor, cost_per_unit x parameter). An option whose parameter
    is 0 is dropped (breeding.gms defines genet_yld only $ p_ghgTechMYld and genet_eff only $ p_ghgTechFEff); a
    parameter that is a switch (param_switch 1: ghgTechLineNitr) leaves the effects at their values."""
    if unit is None:
        return None
    out = {}
    for r, opts in unit.items():
        d = {}
        for k, e in opts.items():
            p = float(settings.get(str(e.get("tech_param", "")), 0.0) or 0.0) if "tech_param" in e else None
            if p is None:              # an old-format table: already at fixed settings
                d[k] = e
                continue
            if p <= 0:
                continue
            if float(e.get("param_switch", 0.0) or 0.0) > 0:     # an on/off setting (ghgTechLineNitr)
                p = 1.0
            s = e.copy()
            for c in _SCALED:
                if c in s.index:
                    s[c] = float(s[c]) * p
            s["cost_eur_head"] = max(float(s["cost_floor"]), float(s["cost_per_unit"]) * p)
            d[k] = s
        if d:
            out[r] = d
    return out
