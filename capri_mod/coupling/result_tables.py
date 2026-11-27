r"""The run's result tables built from the regional results: land-use change, NPK, set-aside, labour, and the premium
outlays, member-state accounts and welfare by product (moved from capri_mod/model.py as they were, 26 November 2026).
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
import warnings
import time

from capri_mod.data.loaders import load_all_data
from capri_mod.supply.supply_module import SupplyModule
from capri_mod.supply import state as _sst   # the supply's state objects
from capri_mod.data.inputs import market_year as _mkt_year   # the market year, else the base year (K52f)
from capri_mod.market.market_module import MarketModule
from capri_mod.policy.policy_module import PolicyModule, PolicyScenario
from capri_mod.environmental.environmental_module import EnvironmentalModule
from capri_mod.utils.utils import (
    calibrate_supply_elasticities, ConvergenceTracker, ResultsReporter
)
from capri_mod.scenarios.scenarios import get_scenario, list_scenarios
from capri_mod.params import param, param_table
from capri_mod.settings import setting, tri_state, current as _settings
from capri_mod.data.definitions import MS_CODE, capri_ms, REGION_TO_COUNTRY, EU_MS_BLOCK, sup_noneu, is_eu as _is_eu
from capri_mod.data.definitions import PRICE_FOLLOWS_EU, PRICE_FOLLOWS_ALL, PRICE_FOLLOWS_SHARE, CAPRI_FEED_TRD
from capri_mod.market.equations.set_prices import DATA_UVAG_DWHE
from capri_mod.tableio import read_input
from capri_mod.policy.premium_response import merge as _merge_premium_factors   # the iterations' premium cut
from capri_mod import runlog as _runlog


def _luc_table(supply_results):
    """Region x transition (1000 ha per year for changes, remaining in full) from the regional results, or None."""
    import pandas as pd
    rows = {r: (getattr(res, "luc", None) or {}).get("transitions") for r, res in (supply_results or {}).items()}
    rows = {r: v for r, v in rows.items() if v}
    return pd.DataFrame.from_dict(rows, orient="index") if rows else None


def _npk_table(supply_results):
    """Long table of the NLP form's fertilisation block per region: nutrient, crop group, source, t; purchases as
    group "TOTAL", source "PURCHASE". None without the NLP form."""
    import pandas as pd
    rows = []
    for r, res in (supply_results or {}).items():
        for nut, o in (getattr(res, "fert_npk", None) or {}).items():
            rows.append(dict(region=r, nutrient=nut, ngrp="TOTAL", source="PURCHASE", t=float(o["purchase"])))
            for (g, s_), v in o.get("flows", {}).items():
                rows.append(dict(region=r, nutrient=nut, ngrp=g, source=s_, t=float(v)))
    return pd.DataFrame(rows) if rows else None


def _set_aside_table(supply_results, data):
    """CAPRI's two set-aside activities, VSET and FALL, and its obligatory set-aside ISET (SETA_, scenarios with
    set-aside rates only), per region (1000 ha; premiums million EUR), VSET and FALL the model's own
    activities since 7 November 2026 (before, the model's SETA split by CAPRI's VSET share and PMP terms, K111):
    their levels and premiums per ha (tools/build/build_labour_setaside.py, set_aside_split.csv prem_vset, prem_fall,
    the 2030 values at the 2030 market year). None without the data."""
    import pandas as pd
    sa = data.get("set_aside_split")
    if sa is None:
        return None
    yr = _mkt_year(data)
    vt = "_2030" if yr == 2030 else ""
    rows = {}
    for r, res in (supply_results or {}).items():
        x = getattr(res, "activities", None)
        if x is None or r not in sa.index or not ("VSET" in x.index or "FALL" in x.index):
            continue
        row = sa.loc[r]
        v, f_ = (float(x.get(a, 0.0)) for a in ("VSET", "FALL"))
        pv, pf = (float(row.get(k + vt, row.get(k, 0.0)) or 0.0) for k in ("prem_vset", "prem_fall"))
        rows[r] = {"SETA": v + f_, "VSET": v, "FALL": f_, "prem_VSET": v * pv / 1000.0, "prem_FALL": f_ * pf / 1000.0,
                   # CAPRI's obligatory set-aside (SETA_, 0 without a scenario's rates; not in SETA = VSET + FALL)
                   "ISET": float(getattr(res, "iset", 0.0) or 0.0)}
    return pd.DataFrame.from_dict(rows, orient="index") if rows else None


def _labour_table(supply_results, data):
    """CAPRI's labour accounts per region (million hours): total LABT, family LABF, paid LABP, as CAPRI's GROF =
    sum over activities of the level x labour per unit / 1000 (tools/build/build_labour_setaside.py; the 2030 coefficients
    at the 2030 market year; VSET and FALL their own activities since 7 November 2026). None without the data."""
    import pandas as pd
    lc = data.get("labour_coef")
    if lc is None:
        return None
    yr = _mkt_year(data)
    vt = "_2030" if yr == 2030 else ""
    if not isinstance(lc.index, pd.MultiIndex):
        lc = lc.reset_index().set_index(["region", "activity"]) if "activity" in lc.columns else lc
    rows = {}
    for r, res in (supply_results or {}).items():
        x = getattr(res, "activities", None)
        if x is None:
            continue
        tot = {"LABT": 0.0, "LABF": 0.0, "LABP": 0.0}
        for a, lev in x.items():
            if (r, a) not in lc.index or not (lev == lev):
                continue
            row = lc.loc[(r, a)]
            for it in tot:
                c = row.get(it.lower() + vt)
                c = row.get(it.lower()) if c is None or c != c else c
                if c is not None and c == c:
                    tot[it] += float(lev) * float(c) / 1000.0
        rows[r] = tot
    return pd.DataFrame.from_dict(rows, orient="index") if rows else None




class ResultTablesBlock:
    """CAPRIModel's premium outlays, member-state accounts and welfare by product (_feoga, _eaa_ms,
    _welfare_products)."""

    def _feoga(self, supply_results):
        """The premium outlays per member state and product at the solution and their budgets (income I4,
        capri_mod/income/feoga.py feop_by_product; EUR million), or None where they could not be computed (warned)."""
        try:
            from capri_mod.income.feoga import feop_by_product
            t = feop_by_product(supply_results, self.supply_module, self.data)
            return t if len(t) else None
        except Exception as exc:
            warnings.warn(f"feoga: the premium outlays per product could not be computed ({exc!r})")
            return None

    def _eaa_ms(self, supply_results):
        """The member states' and the regional aggregates' accounts at producer and basic prices at the solution, with
        their product aggregates (capri_mod/income/eaa_ms.py, eaa_aggregates.py; EUR million), or None where there is
        no complete member state or they could not be computed (warned)."""
        try:
            from capri_mod.income.eaa_aggregates import accounts
            return accounts(supply_results) or None
        except Exception as exc:
            warnings.warn(f"eaa_ms: the member states' accounts at producer prices could not be computed ({exc!r})")
            return None

    def _welfare_products(self, supply_results, feop, welfare_supply):
        """The farms' profit and the domestic support per member state and market product at the solution, with the
        product aggregates and the market and world regions' rows (capri_mod/income/welfare_products.py,
        eaa_aggregates.py welfare_aggregates; EUR million), or None where they could not be computed (warned)."""
        try:
            from capri_mod.income.welfare_products import welfare_by_product
            rents = (welfare_supply["RENT"].to_dict() if welfare_supply is not None and "RENT" in welfare_supply
                     else None)
            from capri_mod.income.eaa_aggregates import welfare_aggregates
            t = welfare_by_product(supply_results, feop, rents)
            return welfare_aggregates(t) if len(t) else None
        except Exception as exc:
            warnings.warn(f"welfare_products: the profit and support per product could not be computed ({exc!r})")
            return None
