r"""The regional model's net revenues per activity at the solve's prices (moved from capri_mod/supply/supply_module.py
as they were, 26 November 2026).
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
import multiprocessing
import os
import warnings
from pathlib import Path

from capri_mod.supply.capri_pmp import (
    share_term, ARABLE_ACTIVITIES,
)
from capri_mod.params import param, param_table
from capri_mod.units import M_N2O, M_N2O_N
from capri_mod.settings import setting, tri_state, current as _settings
from capri_mod.data.definitions import (
    CROPS, ANIMALS, ALL_ACTIVITIES, FEED_ITEMS, NUTRIENTS, ACTIVITY_CLASSES, CROPS_ON_LAND, LAND_MARKET_TYPES, CATTLE_SPLITS,
)
from capri_mod.data.definitions import MS_CODE, capri_ms, IdentityMap, is_eu
from capri_mod.tableio import read_input
from capri_mod.supply import inputs as _inputs
from capri_mod.market.equations.set_prices import DATA_UVAG_Y
from capri_mod.supply.equations.greendeal.landscape import DATA_FALL_FLOOR
from capri_mod.supply.equations.greendeal.surptot import data_SURTOT_MAXS
from capri_mod.supply.equations.set_supply_bounds import v_actLevl_up_FALL
from capri_mod.supply.equations.ghgmiti import (
    p_ghgMiti_othImpact_EmiCalmin, p_ghgMiti_pmpParsqr, p_ghgMiti_pmpParsqr_saving, p_ghgMiti_relSubs)

#: the class, set by capri_mod/supply/supply_module.py where it is defined (an import here would be circular)
SupplyModule = None


from capri_mod.supply.regional_supply.tables import _InputColumn  # noqa: E402


class NetRevenuesBlock:
    """RegionalSupplyModel's net revenues (_compute_net_revenues) and the class settings beside them."""

    def _compute_net_revenues(self, price_shock: Optional[pd.Series] = None):
        """
        Compute per-unit net revenues r_i:
          r_i = price_i × yield_i - variable_cost_i + cap_payment_i  (crops)
          r_i = price_i × yield_i - variable_cost_i                   (animals)
        """
        # the crops' unit values move by the market price's absolute change, as CAPRI's (K169): the scaled shock is the
        # solve's price shock for the crops' revenue, their yield response and the technology mix; the feed costs below
        # keep the market's own change
        _ps_c = self._transmit_crops(price_shock)
        self.ev.price_shock_now = _ps_c
        prices = self.data.producer_prices.copy()
        if _ps_c is not None:
            prices = prices * (1 + _ps_c.reindex(prices.index).fillna(0))

        # GRAS is already on a dry-matter tonnage basis: the conversion from
        # CAPRI's fresh-matter kg/ha happens once at load time, in
        # loaders._reconcile_grass_yield_units.
        yields  = self.data.yields
        costs   = self.data.variable_costs
        cap     = self.data.cap_payments

        # (The livestock yield-unit factors that turned price x YILD into EUR per head - 1e-3 for most animals, a
        # mass proxy for eggs - were removed 23 October 2026: animals take CAPRI's output value per head, TOOU / MREV,
        # below; one without it stops the run.)
        # CAPRI's own market revenue per head (MREV), where available, replaces
        # price x yield for livestock. For crops the two are identical (wheat in
        # DE11: 135.6 EUR/t x 6.15 t/ha = 833.7 = MREV), but for breeding and
        # suckler activities YILD is not a marketed product - suckler cows carry
        # a YILD of 422.6 against 21.8 of beef - so a revenue built from it
        # values the wrong quantity. That is why gross_margin was dominated by
        # pigs and barely moved under policy.
        rev_coef = getattr(self.data, "livestock_revenue_coef", None)
        from capri_mod.supply.equations.supply_model.objective import LINEAR_netRevenue   # CAPRI's LINEAR_ per unit

        r = {}
        prem = {}
        rev = {}
        out_items = {}
        for act in self.acts:
            price   = prices.get(act, 0.0)
            yld     = yields.get(act, 0.0)
            cost    = costs.get(act, 0.0)
            # LIVESTOCK COSTS on the same basis as livestock revenue: CAPRI's
            # regional total inputs (LEVL x TOIN) / the model's head count
            # (livestock_cost_coef.csv). The per-head TOIN in variable_costs is
            # on CAPRI's activity-level basis, which differs from the model's
            # heads several-fold for bulls and heifers.
            _cc = getattr(self.data, "livestock_cost_coef", None)
            if act in ANIMALS and _cc is not None and act in _cc.index \
                    and pd.notna(_cc[act]) and float(_cc[act]) > 0:
                cost = float(_cc[act])
            if not np.isfinite(float(cost)):
                # no CAPRI input cost for an activity the region does not have (its level is fixed at 0, as CAPRI keeps
                # an activity without base level out of its model): none. Until 27 October 2026 the per-head animal
                # columns of variable_costs.csv held values of unknown origin here (written by no builder)
                if float(self._base_levels().get(act, 0.0)) > 1e-8:
                    raise ValueError(f"{self.data.region_id} {act}: no CAPRI input cost")
                cost = 0.0
            # CAPRI's PRME is the premium actually attached to each activity.
            # The instrument-level fallback (BPS applied to every crop and
            # nothing to livestock) both overstates crops -- 676.7 EUR/ha at
            # DE11 against CAPRI's 360.8 -- and zeroes livestock, where CAPRI
            # has 108.2 for dairy cows and 8.2 for bulls.
            premium = getattr(self.data, "cap_premium", None)
            revenue = price * yld
            _ov = getattr(self.data, "livestock_output_value_coef", None)
            _tou = (float(_ov[act]) if act in ANIMALS and _ov is not None and act in _ov.index
                    and pd.notna(_ov[act]) and float(_ov[act]) > 0 else None)
            _mrev = (float(rev_coef[act]) if act in ANIMALS and rev_coef is not None and act in rev_coef.index
                     and pd.notna(rev_coef[act]) else None)
            # CAPRI books no market revenue (MREV) for some activities in some regions (milk sheep and goats in the
            # Netherlands, Denmark and Sweden: no milk, output TOOU only): GAMS reads the absent item as 0
            if _mrev is None and _tou is not None:
                _mrev = 0.0
            if act in ANIMALS and act not in self.OTHER_ANIMALS and not (_mrev is not None and (_mrev > 0 or _tou is not None)):
                if float(self._base_levels().get(act, 0.0)) > 1e-8:
                    raise ValueError(f"{self.data.region_id} {act}: no CAPRI output value per head (TOOU / MREV)")
                revenue = 0.0
            if _mrev is not None and (_mrev > 0 or _tou is not None):
                revenue = _mrev
                # with CAPRI's margin basis (switch below): total output TOOU
                if _tou is not None:
                    revenue = _tou
                    # a commodity price moves the market part (MREV) only; young animals
                    # (the rest of TOOU) move with their own prices (young-animal markets)
                    if price_shock is not None and _mrev > 0:
                        revenue += self._market_revenue_change(act, _mrev, price_shock)
                elif price_shock is not None:
                    revenue *= 1.0 + self._pt(act, SupplyModule.ACTIVITY_PRICE_SOURCE.get(act)) * float(price_shock.get(act, 0.0))

            _pc = getattr(self.data, "livestock_premium_coef", None)
            if act in ANIMALS and _pc is not None \
                    and act in _pc.index and pd.notna(_pc[act]):
                # CAPRI's premiums on the model's head basis, like revenue and costs
                # (livestock_premium_coef.csv: LEVL x PRME of CAPRI's activities / model
                # heads). Looking PRME up by the model's names left suckler cows, heifers,
                # calves, sheep, pigs and poultry without premiums.
                payment = float(_pc[act])
            elif premium is not None and act in premium.index and pd.notna(premium[act]):
                payment = float(premium[act])
            else:
                # no CAPRI premium (PRME) for the activity: none. The fallback was cap_payments.csv's BPS,
                # the loader's random generator written to disk (docs/dev/SYNTHETIC_DATA_AUDIT.md)
                payment = 0.0

            # FEED COSTS follow feed prices. Animal margins were revenue minus a
            # FIXED variable cost, so dearer cereals never reached livestock:
            # under Farm-to-Fork (cereals +14%) poultry changed by exactly 0.0%
            # against CAPRI's -16%. The change in cost per head is the animal's
            # purchased cereal ration (t/head, livestock_feed_coef.csv) times the
            # change in each cereal's price. Base costs already include feed, so
            # at base nothing changes. Protein feed (oilseed cakes, CAPRI's SOYC,
            # RAPC, SUNC) is priced through the FPRO bulk or, without it, the
            # cake price changes (_protein_feed_cost_change).
            if act in ANIMALS and price_shock is not None and act not in (getattr(self.seen, "feed_rations", None) or {}):
                # With feeding inside the regional model (a ration for the animal) the feed is
                # bought in the model at its current prices (QUADRF_ in capri_regional_nlp.py, the base
                # ration's cost taken out of the linear term), as CAPRI costs feed once (supply_model.gms QUADRF_); the
                # change below would count it twice (the supply audit's finding S1, ARCHITECTURE_REFACTOR.md section 5.2, fixed 24 October 2026). It applies where the animal's
                # feeding is not in the model.
                # FEED COSTS follow feed prices. Feed per head is CAPRI's 2017
                # regional total for the activity divided by this model's herd
                # (livestock_feed_coef.csv), so units and vintage match the
                # herds; the old feed table used CAPRI per-UNIT values on
                # census-stock herds (bulls 0.47 t of cereals per head against
                # 1.89, pigs 0.91 against 0.45).
                #  - cereals and protein-rich feed: the member state's CAPRI bulk
                #    price index (feedBlkPrice_, CES over the bulk's products) on
                #    the bulk's base price level (cereal mix at CAPRI's 2030 EU
                #    feed weights, cake index); before the first bulk prices,
                #    the mix and cake price changes themselves;
                #  - energy-rich feed: no market here, price unchanged.
                fc = getattr(self.data, "livestock_feed_coef", None)
                qc = float(fc.get(f"{act}_cereals", float("nan"))) if fc is not None else float("nan")
                qp = float(fc.get(f"{act}_protein", float("nan"))) if fc is not None else float("nan")
                if qc == qc:
                    wsum = sum(self.FEED_CEREAL_MIX.values())
                    _fbr = getattr(self.seen, "feed_bulk_ratio", None) or {}
                    if "FCER" in _fbr:
                        lvl = sum((w / wsum) * float(self.data.producer_prices.get(feed, 0.0))
                                  for feed, w in self.FEED_CEREAL_MIX.items())
                        cost += qc * lvl * (float(_fbr["FCER"]) - 1.0)
                    else:
                        for feed, w in self.FEED_CEREAL_MIX.items():
                            p0 = float(self.data.producer_prices.get(feed, 0.0))
                            cost += qc * (w / wsum) * p0 * float(price_shock.get(feed, 0.0))
                    if qp == qp and qp > 0:
                        if "FPRO" in _fbr:
                            w_, p_ = self._cake_index()
                            ws_ = sum(w_.values()) or 1.0
                            cost += qp * sum((w_[c] / ws_) * p_[c] for c in w_) * (float(_fbr["FPRO"]) - 1.0)
                        else:
                            cost += self._protein_feed_cost_change(qp, price_shock)
                # (no feed coefficient: CAPRI has no herd of the animal in the region at base, so no feed and no
                # feed cost change; the national feed table that stood here as a fallback, feed_requirements.csv, had
                # no builder and was removed on 29 October 2026, KNOWN_ISSUES K99)
            # Crop gross margin (EUR/ha); animal gross margin (EUR/head)
            r[act] = LINEAR_netRevenue(revenue, cost, payment)
            prem[act] = payment
            rev[act] = revenue
            out_items[act] = self._output_items(act, revenue, price, yld, _tou, _mrev, price_shock)

        self.net_revenues = pd.Series(r)
        #: the premium part of each net revenue (CAPRI's PRME per ha or head), for income reports (capri_mod/income)
        self.premiums = pd.Series(prem, dtype=float)
        #: the revenue part of each net revenue (EUR per ha or head), for income reports (the fodder crops' output,
        #: which CAPRI's LINEAR_ does not hold: income I3)
        self.revenues = pd.Series(rev, dtype=float)
        #: the revenue by output item (_output_items), for the economic accounts by item (income I2, capri_mod/income/eaa.py)
        self.output_items = out_items

    # ------------------------------------------------------------------
    # Constraint matrix
    # ------------------------------------------------------------------


    #: CAPRI's organic crops (organicCrops, pol_input/greendeal/load_organic_targets.gms l. 201-233) and the target of
    #: each (p_organicAreaTargetCrops: its NGRP group's, arable_pp, permanent_pp or uaa_pp; l. 148-165, 187, 240-258,
    #: 269-271): the crops whose own organic target tops up other inputs (organic_io.gms) and, where grouped, lowers
    #: yields (organic_area.gms); grassland, fodder, other oilseeds and the minor crops are not organic crops. The
    #: organic crops whose yield takes the organic yield gap (in an NGRP group and in pact2yieldGap,
    #: inputs/load_organic_yieldgap.gms l. 93-140). Both from capri_data/codes/model_activity_classes.csv (the
    #: organic module's sets are not among the sim_ini sets, so the rows cite the GAMS lines)
    ORGANIC_CROP_TARGET = {a: r["organic_target"] for a, r in ACTIVITY_CLASSES.items() if r["organic_target"]}
    ORGANIC_YIELD_GAP_CROPS = tuple(a for a in CROPS if ACTIVITY_CLASSES[a]["organic_yield_gap"] == "1")
    #: CAPRI-ERROR-FIX (setting supply.greendeal_inputs_keep_tech_change): define_inputs.gms l. 66-73 applies a
    #: scenario's regional input change as (1 + change) x the input-saving progress TF_I only when the global
    #: scenAugmentsTechChange is on. organic_io.gms l. 94 and conventional_io.gms l. 171 set it on, but
    #: conventional_io.gms l. 361 sets it off at compile time in its other branch, which comes later in the file, so
    #: the Green Deal runs replace the progress instead of multiplying it (CAPRI's own notes, l. 176 and
    #: greendeal_scenarios.gms l. 137-138, call the off setting an oversight). false: CAPRI's code as written.
    greendeal_inputs_keep_tech_change = setting("supply.greendeal_inputs_keep_tech_change")
    #: CAPRI-ERROR-FIX (setting supply.organic_topup_at_fuel_cost): organic_io.gms l. 107-115 tops up other inputs
    #: of each organic crop by its EFUL coefficient x 2 x its organic target, "assuming that costs for EFUL+SERI would
    #: double", but adds the fuel coefficient to the INPO coefficient, so it is valued at INPO's unit value instead of
    #: fuel's. true: valued at the fuel cost; false: CAPRI's code as written.
    organic_topup_at_fuel_cost = setting("supply.organic_topup_at_fuel_cost")
    #: Comparison switch (setting supply.greendeal_plap_crop_level_capri_step; DEP-51, its crop-level part): CAPRI's
    #: 2030 reference values each crop's plant protection at its pesticide module's aggregates (Plantp_cost, which its
    #: PMP calibration absorbed), its Green Deal step at PLAP x UVAG(PLAP). true: the Green Deal step moves each crop's
    #: mean plant-protection cost to CAPRI's step (policy._apply_greendeal_input_changes); false: the model's one
    #: representation in base and scenario (DEP-51).
    greendeal_plap_crop_level_capri_step = setting("supply.greendeal_plap_crop_level_capri_step")
    #: Comparison switch (setting supply.greendeal_plap_mix_capri_step; DEP-51, its T1 - T2 part): CAPRI's 2030
    #: reference and calibration had no T1 - T2 plant-protection cost, its Green Deal step has one (p_technFact PLAP
    #: +-0.4). true: in the Green Deal group's solves each technology mix column carries the difference
    #: (policy._plap_mix_capri_step, techn_mix._mix_linear); false: the model's one representation (DEP-51).
    greendeal_plap_mix_capri_step = setting("supply.greendeal_plap_mix_capri_step")

    #: EU organic area already in place, subtracted from the target to give the
    #: share that actually CONVERTS. CAPRI sets this explicitly:
    #: p_organicAreaTarget("EU27yr19") = 0.25 - 0.10 in
    #: gams/pol_input/greendeal/load_organic_targets.gms, i.e. a 15 percentage
    #: point shock, not 25. This model applied the full target as if every
    #: hectare converted, nearly double CAPRI's shock, which is why oilseeds
    #: (1.43x) and permanent crops (1.57x) overshot CAPRI's published results.
    #: CAPRI breaks the 15 points down by member state and crop group from Eurostat
    #: organic areas (organic_targets.gdx, organic_targets_UAA.gdx); that breakdown is
    #: loaded (organic_targets_ms.csv) and used for every EU region. This EU figure
    #: is only the fallback for a region without it (the parameter ORGANIC_BASELINE_SHARE, read where used).

    #: Crops occupying PERMANENT land - the same set the land data is built
    #: with in tools/build/build_capri_base.py. Everything else except grass is arable.
    PERMANENT_LAND_CROPS = CROPS_ON_LAND["FRUN"]         # capri_data/codes/model_activity_classes.csv


    #: CAPRI's assumed average yield loss for a 50% pesticide reduction
    #: (JRC121368, from Sanchez et al. 2019: 18.6% of EU production potentially
    #: affected by 20 pests, worst case 50% loss on that share). CAPRI has NO
    #: dose-response function for plant protection -- unlike fertiliser -- so
    #: this is an explicit assumption in CAPRI too, not a derived quantity (the parameter
    #: PESTICIDE_YIELD_LOSS_AT_50PCT, read where used).

    #: The crops the pesticide yield loss reaches (the jrc121368 rule only; CAPRI star 3.0 calls conventional_io.gms
    #: with the yield shock off): CAPRI's pesticideCrops, every crop activity MCACT but the idled histosols
    #: (pol_input/greendeal/conventional_io.gms l. 51-53). K74 (the supply audit's finding S11, ARCHITECTURE_REFACTOR.md section 5.2), 29 October 2026: a list of 23 crops without
    #: source before (rice, tobacco, textiles, nurseries, flowers, other crops and industrial crops left out). The loss
    #: acts through the yield of a crop with a producer price; the fodder crops (grass, fodder maize, other fodder,
    #: CAPRI's shift of their output coefficients) and set-aside are not reached (REGISTERED: their yields enter the
    #: fodder balances from CAPRI's data, not from the yields this rule moves)
    PESTICIDE_AFFECTED = tuple(c for c in CROPS if ACTIVITY_CLASSES[c]["pesticide"] == "1")   # classes table

    #: Share of total input cost that is fertiliser (CAPRI FERT, EU-wide, all 27 member states' 2017 data;
    #: tools/build/build_crop_cost_shares.py): FALLBACK for the fertiliser cost per ha of a crop CAPRI does not grow
    #: in the region (the regional rows of plant_protection_cost.csv serve the others).
    FERT_COST_SHARE = _InputColumn("crop_cost_shares.csv", "supply", "fert_cost_share")


    # kg N excreted per kg nitrate fed (CAPRI line_nitr.gms: +0.42% of DM intake at 1.5%): the parameter NITR_N_EXCR,
    # read where used


    #: free land types of CAPRI's land market (artificial land held fixed)
    LAND_TYPES = tuple(LAND_MARKET_TYPES)                # capri_data/codes/model_land_types.csv

    #: CAPRI's fertiliser allocation (manure replaces mineral N). OFF by default:
    #: on its own it makes herd cuts LESS effective per head (each head cut
    #: relieves only the unavailable share of its manure), so the N target needs
    #: more heads, as CAPRI's substitution implies; CAPRI's relief comes from
    #: the manure market that substitution enables. To be switched on together
    #: with the national manure pool (not ported yet).
    use_fert_allocation = False
    #: national manure market through the allocation (not ported yet); requires
    #: use_fert_allocation
    use_manure_pool = False


    #: activities without a level at the calibration point held at zero by a bound row, as CAPRI (no v_actLevl without
    #: p_technFact). OFF: tried 22 October 2026, it made the NLP form fail or relax mineral caps in Greek and Bulgarian
    #: regions under Farm-to-Fork (fixed columns at zero degenerate the fertiliser block); absent_output_cleared instead
    absent_activities_fixed = setting("supply.absent_activities_fixed")
    #: CAPRI's bounds of the voluntary set-aside where its data have a level above 1e-6 (set_supply_bounds.gms
    #: l. 42-43; 1000 ha): 1e-6 .. 1e5
    VSET_DATA_MIN = 1.0e-6
    VSET_LO, VSET_UP = 1.0e-6, 1.0e5
    #: CAPRI's fallow bound under a landscape floor (set_supply_bounds.gms l. 159-160: v_actLevl.up(FALL,A) = 0.5 x
    #: UAAR per technology where DATA FALL FLOOR is set), summed over FALL's technologies (model_activity_classes.csv)
    FALL_FLOOR_UP_SHARE = 0.5
    # K64: the solver's residue on activities without a base level (|level| <= 1e-4, 0.1 ha or head) is reported as
    # zero, so no output arises where CAPRI has no variable (Norway's 6e-6 kt of tobacco had kept the market from
    # converging); CAPRI's bounds on endogenous activity levels, 0.1 to 10 x the simulation's data level
    # (set_supply_bounds.gms), always apply


    # CAPRI's low/high-intensity fattening bulls and heifers (the port of CAPRI's bull and heifer splits, tools/build/build_cattle_intensity.py)

    #: CAPRI's cattle activities inside the model's animals (tools/build/build_cattle_intensity.py SPLITS): key -> (the CAPRI
    #: activity that gains the stalls z, the one that gives them up); splits of one animal giving up the same activity
    #: share its curvature (cross term) and its bound
    CATTLE_SPLIT_MEMBERS = dict(CATTLE_SPLITS)          # capri_data/codes/model_cattle_splits.csv
    #: the splits that give CAPRI's replacement heifers and calves their own levels, with the young-animal markets per
    #: sex (22 October 2026). OFF by default: with them the Farm-to-Fork 2030 run's young-animal markets did not converge
    #: (KNOWN_ISSUES K65; runs r89-r92). False keeps only the intensity pairs (the port of CAPRI's bull and heifer splits), the pooled young-animal
    #: markets and the animals' herd terms of that grouping - the validated state of runs r86 / r87
    use_cattle_member_splits = setting("supply.use_cattle_member_splits")
