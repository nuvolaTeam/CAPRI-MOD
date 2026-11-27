r"""The regional model's constraint rows (moved from capri_mod/supply/supply_module.py as they were, 26 November 2026).
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


from capri_mod.supply.regional_supply.tables import FIXED_ACTIVITIES, _n_techn  # noqa: E402


class ConstraintsBlock:
    """RegionalSupplyModel's constraints (_build_constraints) and the class settings beside them."""


    # CAPRI's cattle genomics (envind/breeding.gms): higher milk yield (dairy cows) and lower energy need
    # (non-dairy ruminants), adopted inside the supply model (docs/MITIGATION_IN_SUPPLY.md)
    # the animal options' PMP slope net of CAPRI's cost-saving drop between its ini and max calibration runs
    # (breeding.gms l. 447-458; K67 F2)


    #: the model's two classes of CAPRI's histosol options and the land row each acts on: the histosol data's column
    #: suffix (pmp_sqr_crop, share_grass, ...) and the model's own constraint row label, both internal names of the
    #: model, so kept in the code
    HISTOSOL_CLASSES = (("crop", "arable_land"), ("grass", "grassland"))
    #: the land types of each class's histosol area (CAPRI's luClassAgr: CROP = ARAB = ARAC + FRUN; GRSLND x
    #: v_landshare(GRAS) = the productive grassland GRAS), for the bound on the current land (K158)
    HISTOSOL_LAND = {"crop": ("ARAC", "FRUN"), "grass": ("GRAS",)}


    def _build_constraints(
        self,
        set_aside_requirement: float = 0.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns (A_ub, b_ub, A_eq, b_eq) for scipy.optimize.

        Constraints:
          1. Total arable land ≤ UAA_arable × (1 − set_aside_requirement)
          2. Total permanent crops ≤ UAA_permanent
          3. Total grassland = used grass area (accounting identity, soft)
          4. For each nutrient N: Σ_i coef_{Ni} × x_i ≤ N_max (nitrates dir.)

        ``set_aside_requirement`` is the share of UAA that must be held as
        high-diversity landscape features (the Biodiversity Strategy 10% target,
        CAP GAEC 8). It is implemented the way CAPRI implements it in
        ``pol_input/greendeal/landscape.gms``:

            data(ru,"FALL","FLOOR") = target * UAAR + SETF

        i.e. a FLOOR on the non-productive activity, sized on UAA — *not* a
        reduction of the arable area available to crops, which is what this
        previously did. The two are different instruments and behave
        differently: a floor forces land INTO fallow/set-aside (so SETA rises),
        whereas shrinking arable land squeezes every crop proportionally and
        leaves SETA untouched. That mismatch showed up directly against CAPRI's
        Green Deal run, where CAPRI moves SETA -5.7% and this model moved it
        +0.3%.

        The floor enters as -x_SETA <= -target*UAA (a lower bound in the
        upper-bound form the solver uses), and the arable constraint is left at
        its true availability so the crops compete for what remains.
        """
        acts_idx = {a: i for i, a in enumerate(self.acts)}
        n = self.n
        A_rows, b_rows = [], []
        self.ev.fall_floor = 0.0          # CAPRI data(ru,"FALL","FLOOR"), set by the landscape rule below
        # one label per row, appended with it, so a shadow price is always
        # reported under the constraint it belongs to
        self.ev.row_labels = []

        # 1. Arable land constraint
        #
        # Every activity that occupies ARABLE land must be in this row, including
        # fodder on arable land (MAIF, OFAR, ROOF) and fallow / set-aside (VSET, FALL). All
        # three used to be left out, with two consequences:
        #   - the right-hand side (arable land) counted the fodder area while the
        #     sum did not, so the row carried ~14 Mha of built-in slack and could
        #     never bind: the arable shadow price was zero in every region;
        #   - a landscape-feature floor on SETA grew set-aside out of nothing,
        #     without displacing a single crop. In CAPRI fallow competes for
        #     arable land, which is where its -9% cereal-area effect under
        #     Farm-to-Fork comes from; here cereals kept their land and fell only
        #     9.8% against CAPRI's 15%, with the cereal price already matching.
        # CAPRI's land balances (supply_model.gms LandBalNoSlak_; equations/supply_model/land.py)
        from capri_mod.supply.equations.supply_model.land import LandBalNoSlak_, LandBal_rhs
        # One classification for both rows, the same one the land data is built
        # with (tools/build/build_capri_base.py PERMANENT_CROPS): tobacco, cotton and
        # other fibre are ANNUAL crops on arable land. They used to sit in the
        # permanent row while the land data counted them as arable, so each row
        # was measured against land built on a different definition.
        arable_crops = [a for a in CROPS
                        if a not in CROPS_ON_LAND["GRAS"] + self.PERMANENT_LAND_CROPS]
        row_arable = LandBalNoSlak_(n, acts_idx, arable_crops)          # ARAC
        A_rows.append(row_arable)
        self.ev.row_labels.append("arable_land")
        # The ARABLE land figure and the crop areas come from different
        # aggregations and disagree in 54 of 248 regions, by 9,960 kha in total,
        # with ratios up to 12.7x (LT02, PL81, PL84, PL91, BG31, BG33). Taking
        # the land figure literally makes the BASE YEAR infeasible, so the solver
        # must cut: those regions lost most or all of their cereals in a plain
        # base solve, and the 9,976 kha the solve shed matched the 9,960 kha of
        # excess almost exactly. EU wheat came out 19,857 kha against a base of
        # 22,095 and a real EU figure of ~22,000.
        #
        # Same treatment as the PERMANENT bound below: the bound is the larger of
        # the land figure and what the region actually grows, so the constraint
        # stays slack where the two sources agree and stops rewriting the base
        # year where they do not.
        arable_base = sum(float(self._base_levels().get(a, 0.0))
                          for a in arable_crops if a in acts_idx)
        # arable land INCLUDING fallow, now that SETA is in the row
        _land_arable = (float(self._land_of("ARABLE"))
                        + self._land_of("FALLOW"))
        b_rows.append(LandBal_rhs(_land_arable, arable_base))

        # 1b. Landscape-elements floor: at least `set_aside_requirement` of UAA
        # held as the non-productive activity. Expressed as -x_SETA <= -target
        # so it fits the upper-bound form. A negative requirement (a scenario
        # REMOVING an existing obligation) is skipped rather than inverted into
        # a nonsensical ceiling.
        # the set-aside activities of CAPRI's e_setaLandscape (setaFallow: VSET and FALL; ISET, GSET, TSET have no
        # area in CAPRI's 2017 and 2030 data); one activity, SETA = VSET + FALL, until 7 November 2026
        _seta_acts = [a for a in ("VSET", "FALL") if a in acts_idx]
        _fall_up = None                   # FALL's upper bound under the floor (CAPRI's 0.5 x UAAR per technology)
        if set_aside_requirement and set_aside_requirement > 0 and _seta_acts:
            uaa_total = (self._land_of("ARABLE")
                         + self._land_of("PERMANENT")
                         + self._land_of("GRASSLAND")
                         + self._land_of("FALLOW"))
            _pp = getattr(self.data, "landscape_target_pp", None)
            if _pp is not None:
                # CAPRI's own rule (pol_input/greendeal/landscape.gms):
                #   FALL.FLOOR = lndscpTarg/10 * p_setAsideTarget * UAAR + SETF
                # p_setAsideTarget is the member state's MISSING share - points
                # of UAA still needed to reach 10%, net of fallow and of the
                # landscape elements LUCAS already records - and the existing
                # set-aside is added on top. A member state with no entry is
                # already at the target; one CAPRI maps no code to (Portugal)
                # has none (_capri_ms_targets). The requested share scales the
                # ambition exactly as CAPRI's lndscpTarg does (10% = full).
                _seta0 = sum(float(self._base_levels().get(a, 0.0)) for a in _seta_acts)   # CAPRI's SETF
                floor = DATA_FALL_FLOOR(set_aside_requirement, _pp, uaa_total, _seta0)   # pol_input/greendeal/landscape.gms
            else:
                floor = set_aside_requirement * uaa_total
            self.ev.fall_floor = float(floor)
            if floor > 0:
                _fall_up = v_actLevl_up_FALL(self.FALL_FLOOR_UP_SHARE, _n_techn("FALL"), uaa_total)
            # CAPRI's e_setaLandscape (equations/supply_model/set_aside.py)
            from capri_mod.supply.equations.supply_model.set_aside import e_setaLandscape
            row_seta, b_seta = e_setaLandscape(n, acts_idx, _seta_acts, floor)
            A_rows.append(row_seta)
            self.ev.row_labels.append("landscape_floor")
            b_rows.append(b_seta)

        # 2. Permanent crops land constraint
        perm_crops = list(self.PERMANENT_LAND_CROPS)
        row_perm = LandBalNoSlak_(n, acts_idx, perm_crops)              # FRUN
        A_rows.append(row_perm)
        self.ev.row_labels.append("permanent_land")
        # The PERMANENT land figure and the crop areas come from different
        # aggregations and disagree in 56 of 248 regions, by 4640 kha in total —
        # and the disagreement is concentrated in exactly the Mediterranean
        # permanent-crop regions (ES61 3.2x, ITF4 2.6x, PT18 2.7x; ES63/ES64
        # carry real olive area against a PERMANENT figure of zero). Taking the
        # land figure literally makes the BASE YEAR infeasible, so the solver
        # must cut, and the largest crop absorbs it: EL43 olives collapsed
        # 178 -> 40 kha in a plain base solve, which showed up as a 0.35x olive
        # miss against CAPRI's 2030 reference.
        #
        # The observed areas are the better-grounded quantity here (base olive
        # area totals 4808 kha against a real EU ~5000), so the bound is the
        # larger of the land figure and what the region actually grows. This
        # leaves the constraint slack where the data agrees and stops it
        # rewriting the base year where it does not.
        perm_base = sum(float(self._base_levels().get(a, 0.0))
                        for a in perm_crops if a in acts_idx)
        b_rows.append(LandBal_rhs(self._land_of("PERMANENT"), perm_base))

        # 3. Grassland constraint
        # CAPRI's land rules (LandBalNoSlak_): the row is CAPRI's grassland balance, the grassland activity (CAPRI's
        # GRAE + GRAI, the model's own activities since 7 November 2026) equals the grassland area. Maize and other fodder are ARABLE crops (CAPRI MAIF, OFAR, ROOF) and
        # are already in the arable row. (The model's earlier row - fodder on grassland plus a fifth of arable land -
        # fixed arable fodder at its base area plus a fifth of any arable change: regions under the N target could not
        # replace fertilised fodder leys.)
        grass_acts = list(CROPS_ON_LAND["GRAS"])
        row_grass = LandBalNoSlak_(n, acts_idx, grass_acts)             # GRAS
        A_rows.append(row_grass)
        self.ev.row_labels.append("grassland")
        # RHS must admit the calibrated base fodder area. The land-availability
        # GRASSLAND figure and the sum of fodder-activity base areas come from
        # different CAPRI symbols and do not always reconcile (at DE21 the base
        # fodder area is 454 against a grassland figure of 167), so a RHS built
        # only from the land figure is violated at base and forces livestock
        # down. Take the larger of the land-based limit and the actual base
        # fodder area plus expansion headroom.
        # (23 October 2026, no proxies: the former limit took a fifth of arable land on top with the land rules off and
        # 15% headroom above the base fodder area, neither CAPRI's; CAPRI's grassland balance is the grassland area,
        # LandBalNoSlak_. The larger of the land figure and the base area stays, as for the other land rows)
        grass_land_limit = self._land_of("GRASSLAND")
        base_fodder = sum(self._base_levels().get(a, 0.0) for a in grass_acts)
        b_rows.append(LandBal_rhs(grass_land_limit, base_fodder))

        # (4. the legacy nitrate-limit row on total applied N, not CAPRI's, was retired on 27 October 2026, K33: nitrogen
        # limits are CAPRI's N-balance target)

        # 5. Feed constraint: animal roughage demand ≤ on-farm supply + buy-in.
        #    Full CAPRI has a separate feed market; here we allow a buy-in
        #    headroom rather than forcing complete on-farm self-sufficiency.
        #    With a hard demand ≤ on-farm-supply (RHS 0), the newly-populated
        #    livestock herds demand more roughage than regional fodder area can
        #    supply, so the solver zeroed every feeding animal -- the corner
        #    solution that made livestock scenarios meaningless. Permitting
        #    buy-in (roughage can be purchased, as it is in reality and in CAPRI)
        #    lets herds sit at their base level. The headroom is generous because
        #    this simplified module is not the place to model the feed market.
        # REPLACED where CAPRI-consistent data exist: the hard fodder balance
        # (docs/FODDER_BALANCE.md) - fodder is non-tradable in CAPRI. The loose
        # 'buy-in' version below remains only as a fallback; it needed generous
        # headroom because its old per-unit coefficients were inconsistent.
        fodder_rows = self._fodder_rows()
        for row, _lam, rhs, lab in fodder_rows:
            A_rows.append(row)
            self.ev.row_labels.append(lab)
            b_rows.append(rhs)
            # CAPRI's SUPBAL_ for non-tradable fodder is an EQUALITY (production net of losses = use): the NLP form
            # builds it with the feed columns (capri_regional_nlp). The conic form's other side, a "_band" row with the
            # previous solve's fodder per head, was dropped from the NLP form on 26 October 2026 (K75) and is no longer
            # built (27 October 2026: the same solution to the last digit in six regions, baseline and Farm-to-Fork)
        # (The roughage "buy-in" rows that stood in where the fodder balance had no data - headroom 1.5 x the base
        # shortfall plus 0.1 x on-farm supply - were removed 23 October 2026: every region with herds has CAPRI's fodder
        # balance; one without it stops the run.)
        if not fodder_rows and any(float(self._base_levels().get(a_, 0.0)) > 1e-8 for a_ in ANIMALS
                                   if a_ in acts_idx and a_ not in FIXED_ACTIVITIES):
            raise ValueError(f"{self.data.region_id}: herds without CAPRI's fodder balance (fodder_balance_<base year>.csv)")

        # Gross nitrogen balance (JRC121368's binding GNB restriction): surplus per
        # ha of farmland <= the tiered target, i.e.
        #   sum_a (s_a - target * [a is a crop]) * x_a <= 0
        # with s_a each activity's own contribution to the balance.
        srow = getattr(self.ev, "surplus_row", None)
        if srow is not None:
            coefs, target = srow[0], srow[1]
            nmin = srow[2] if len(srow) > 2 else {}
            upt = srow[3] if len(srow) > 3 else {}
            ybase = srow[4] if len(srow) > 4 else None
            mint = getattr(self.ev, "n_intensity", {}) or {}
            ycur = self.data.yields
            row_B = np.zeros(n)
            self.ev.mineral_row = {}
            _env_now = getattr(self.seen, "env_for_surplus", None)
            for i, a in enumerate(self.acts):
                sa = float(coefs.get(a, 0.0))
                if not self._techs_inside():
                    sa -= float((getattr(self.ev, "animal_n_relief", None) or {}).get(a, 0.0))   # manure technologies
                sa -= float((getattr(self.ev, "manure_ni_relief", None) or {}).get(a, 0.0))      # inhibitors on manure
                sa += self._nitrate_row_term(a)                                             # nitrate N excretion
                _exact = None
                _fcr = float(mint.get("__credit__", 1.0))
                if _env_now is not None and (a in CROPS or _fcr != 1.0):
                    try:
                        _mi = {"__credit__": _fcr}
                        if a in mint:
                            _mi[a] = float(mint[a])
                        _exact = float(_env_now.unit_nitrogen_balance(
                            a, ycur, self.data.region_id, _mi, yields_scen=self._yields_scen_now())["n_surplus"])
                    except Exception:
                        _exact = None
                if _exact is not None and a not in CROPS:
                    sa += _exact - float(coefs.get(a, 0.0))     # manure credit at the technology factor
                    _exact = None
                if _exact is not None:
                    # THE CROP'S OWN BALANCE AT THIS SOLVE'S YIELDS AND FERTILISER INTENSITY,
                    # from the same function as the reported accounts (it is linear in
                    # activity levels): removal, residues, fixation, need-scaled mineral N
                    # and the residue and manure credits all move with yield exactly as
                    # reported. The term-by-term adjustments below covered removal and
                    # mineral need only; with CAPRI's balance (residues, fixation per
                    # tonne) the constraint and the accounts drifted apart and the EU
                    # surplus fell 28% against a 36% target.
                    row_B[i] = sa - float(coefs.get(a, 0.0)) + _exact
                    if float(nmin.get(a, 0.0)) > 0:
                        _y0 = float(ybase.get(a, 0.0)) if (ybase is not None and hasattr(ybase, "get")) else 0.0
                        _yc = float(ycur.get(a, _y0)) if hasattr(ycur, "get") else _y0
                        _r = self._need_yf(a, _y0, _yc) if (_y0 > 0 and _yc > 0) else 1.0
                        self.ev.mineral_row[a] = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r
                    continue
                if a in mint:                       # less fertiliser applied
                    sa -= float(nmin.get(a, 0.0)) * (1.0 - mint[a])
                # Uptake at THIS solve's yields - after fertiliser intensity,
                # pesticide and organic yield effects - as CAPRI's balance does.
                # With base-year uptake the constraint believed the target was
                # met while the true balance fell only half as far (Farm-to-Fork
                # EU surplus -16% against a target cut of about a third).
                if a in CROPS and ybase is not None:
                    y0 = float(ybase.get(a, 0.0)) if hasattr(ybase, "get") else 0.0
                    if y0 > 0:
                        yc = float(ycur.get(a, y0)) if hasattr(ycur, "get") else y0
                        sa += float(upt.get(a, 0.0)) * (1.0 - yc / y0)
                        # crop NEED follows yield (CAPRI fertned.gms, _need_yf),
                        # and so does the mineral N it calls for - exactly as the
                        # environmental accounts compute it. Without this term the
                        # constraint saw more fertiliser than the accounts after
                        # yield losses, demanded extra cuts, and the surplus fell
                        # past its target (Farm-to-Fork -45% vs CAPRI's -34%).
                        if yc > 0:
                            sa += (float(nmin.get(a, 0.0)) * float(mint.get(a, 1.0))
                                   * (self._need_yf(a, y0, yc) - 1.0))
                if a in CROPS and float(nmin.get(a, 0.0)) > 0:
                    # mineral part of the coefficient (for CAPRI's fertiliser technologies
                    # inside the regional model): nmin x intensity x need factor of the yield (_need_yf)
                    _y0 = float(ybase.get(a, 0.0)) if (ybase is not None and hasattr(ybase, "get")) else 0.0
                    _yc = float(ycur.get(a, _y0)) if hasattr(ycur, "get") else _y0
                    _r = self._need_yf(a, _y0, _yc) if (_y0 > 0 and _yc > 0) else 1.0
                    self.ev.mineral_row[a] = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r
                row_B[i] = sa
            # A REGIONAL CAP: the tiered per-ha target times BASE farmland. With
            # current farmland as the denominator, land expansion diluted the
            # surplus: in North Brabant the target made land worth ~28,000 EUR/ha,
            # the land market expanded farmland to its 15% cap, the target went
            # slack, and the nitrogen and land loops pulled against each other
            # without settling. The required cut in kg N is unchanged; buying
            # land no longer meets it.
            # (With the land market, land.py rewrites this row to CAPRI's form, the target per ha x the current land
            # ARAC + GRAS + FRUN: e_SURTOTHa / SURTOT_REST_, "SURPLUS PER HECTARE OF CURRENT LAND"; identical at base.)
            base_area = float(sum(v for a, v in self._base_levels().items() if a in CROPS))
            # the balance's part no activity carries (supply.manure_base_trade "capri": the region's base manure trade,
            # CAPRI's v_manureExports / v_manureImports at the calibration point, with the mineral N it displaces):
            # on the right-hand side; the NLP form takes the mineral part back (nlp.py, K167)
            _cst = {}
            if _env_now is not None:
                _cst = _env_now.nitrogen_balance_constants(self.data.region_id, ycur,
                                                           {"__credit__": float(mint.get("__credit__", 1.0))},
                                                           yields_scen=self._yields_scen_now())
            self.ev.nb_const = (float(_cst.get("n_surplus", 0.0) or 0.0), float(_cst.get("n_mineral_input", 0.0) or 0.0))
            A_rows.append(row_B)
            b_rows.append(float(target) * base_area - self.ev.nb_const[0])
            self.ev.row_labels.append("N_balance")
            # (a row "manure_application", manure N <= 170 kg N/ha x crop land, stood here until 29 October 2026:
            # capri-mod's, not CAPRI's - CAPRI's default runs tie manure to land through the crop nutrient balance
            # NUTNED_, fertDistExcr_ and ManureNPK_ with manure trade, which the NLP form ports, and apply the Nitrates
            # Directive's cap only in NDman, off in its Green Deal runs; KNOWN_ISSUES K105)

        # CAPRI's mineral fertiliser reduction (Green Deal mineRedu; pol_input/greendeal/minfert_redu_*.gms):
        #   "20"    e_synNMax: mineral N per ha of current land <= baseline mineral N per ha x (1 - r)
        #   "NNcrp" nMax_ with the "f2f" regulation of the inner fertiliser model: mineral N to each crop group per
        #           ha <= cap_g (baseline x (1 - r), CAPRI's exemptions). The inner model can move manure and crop
        #           residues between groups, so the binding condition on the regional model is the sum over the groups:
        #           mineral N to the capped groups <= sum_g cap_g x area_g.
        # As a row: sum_a (capped share_a x m_a - kappa_a) x_a + m_animals x_animals <= catch-crop N, m_a the
        # activity's mineral N from the environmental module's own balance (linear in activity levels, at this
        # solve's yields and fertiliser factors, as the N_balance row), kappa_a = sum_g share_ag x cap_g (kg/ha).
        mcap = getattr(self.ev, "mineral_cap", None)
        _env_m = getattr(self.seen, "env_for_surplus", None)
        if mcap is not None and _env_m is not None:
            mint = getattr(self.ev, "n_intensity", {}) or {}
            ycur = self.data.yields
            _fcr = float(mint.get("__credit__", 1.0))
            nmin_m = mcap.get("nmin") or {}
            ybase_m = mcap.get("ybase")
            row_m = np.zeros(n)
            mrow_parts = {}
            for i, a in enumerate(self.acts):
                _mi = {"__credit__": _fcr}
                if a in mint:
                    _mi[a] = float(mint[a])
                try:
                    m_a = float(_env_m.unit_nitrogen_balance(a, ycur, self.data.region_id, _mi,
                                                             yields_scen=self._yields_scen_now())["n_mineral_input"])
                except Exception:
                    m_a = 0.0
                if a in CROPS:
                    row_m[i] = float(mcap["capped_share"].get(a, 0.0)) * m_a - float(mcap["kappa"].get(a, 0.0))
                    if float(nmin_m.get(a, 0.0)) > 0:
                        _y0 = float(ybase_m.get(a, 0.0)) if (ybase_m is not None and hasattr(ybase_m, "get")) else 0.0
                        _yc = float(ycur.get(a, _y0)) if hasattr(ycur, "get") else _y0
                        _r = self._need_yf(a, _y0, _yc) if (_y0 > 0 and _yc > 0) else 1.0
                        mrow_parts[a] = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r \
                            * float(mcap["capped_share"].get(a, 0.0))
                else:
                    row_m[i] = m_a
            # the mineral N the base manure trade displaces, a constant of the region (supply.manure_base_trade
            # "capri", K167; the NLP form replaces this row by the inner model's regulations)
            _cm = float(_env_m.nitrogen_balance_constants(self.data.region_id, ycur, {"__credit__": _fcr},
                                                          yields_scen=self._yields_scen_now())
                        .get("n_mineral_input", 0.0) or 0.0)
            A_rows.append(row_m)
            b_rows.append(float(self._cover_n_increment()) - _cm)
            self.ev.row_labels.append("mineral_N")

        # CAPRI winterCover_: the catch crops need land not already under winter cover,
        #   sum_c crop_c x winter cover share_c <= UAAR - CATC + FALL.FLOOR  (UAAR: the region's data, fixed)
        # CAPRI adds the landscape rule's fallow floor (supply_model.gms l. 1987: "in case fallow land is
        # expanded only to meet the set aside target, take out from the calculation, otherwise we can
        # easily end up with negative values and infeasibilities"). Without it, where the floor fills
        # most of the arable land (Tyrol, Bolzano: floor 22 kha on 14 kha of arable land) the floor and
        # the catch-crop minimum could not both hold: the land-market solve failed and the fallback
        # emptied the region's grassland and herds.
        _cv = getattr(self.ev, "cover", None)
        wcs_ = getattr(self.data, "winter_cover_share", None)
        if _cv and _cv.get("delta", 0.0) > 0 and wcs_ is not None:
            row_W = np.array([float(wcs_.at[a, "share"]) if a in wcs_.index else 0.0 for a in self.acts])
            if row_W.any():
                A_rows.append(row_W)
                b_rows.append(_cv["uaa"] - _cv["req"] + float(getattr(self.ev, "fall_floor", 0.0) or 0.0)
                              + 1e-9 * max(1.0, _cv["uaa"]))
                self.ev.row_labels.append("winter_cover")

        # CAPRI's FIXED activities (sets.gms FACT = MFCACT + OANI: other oilseeds, other industrial crops, other
        # animals): not endogenous, v_actLevl.FX at the data level (supply/prep_sim.gms l. 250); CAPRI has no
        # market for their products either (arm_sets.gms nonXX_CROPS)
        _x0f = self._base_levels()
        _unc = getattr(self.data, "uncalibrated", None) or frozenset()
        for i, a in enumerate(self.acts):
            if a in FIXED_ACTIVITIES or (a in _unc and float(_x0f.get(a, 0.0)) > 1e-8):
                v = max(float(_x0f.get(a, 0.0)), 0.0)
                tol = 1e-7 * max(v, 1e-3)
                for sg in (1.0, -1.0):
                    row_f = np.zeros(n)
                    row_f[i] = sg
                    A_rows.append(row_f)
                    b_rows.append(sg * v + tol)
                    self.ev.row_labels.append(f"fixed_{a}_{'up' if sg > 0 else 'lo'}")

        # CAPRI's bounds on the endogenous activities (supply/set_supply_bounds.gms, applied in every simulation by
        # prep_sim.gms): LO = max(0.1 x level, 1e-8), UP = max(10 x level, level + 100), level = the data level of the
        # simulation (here the region's base), per technology: the model's activity is the sum of CAPRI's technologies
        # (T1 and T2 at half the level each, T alone; model_activity_classes.csv technologies), so its bounds are the
        # sums, LO = max(0.1 x level, k x 1e-8), UP = max(10 x level, level + k x 100) with k technologies (until 13
        # November 2026 the bounds of one technology: a crop below 22 kha could grow by 100 kha, not 200). Without them an activity could leave its calibration range entirely
        # (K27: Dutch fattening sheep 10 -> 2,923 thousand head, dairy cows to 0 under Farm-to-Fork). CAPRI's own
        # exemption: voluntary set-aside (VSET 1e-6 .. 1e5, set_supply_bounds.gms l. 42-43; FALL takes the rule, as in
        # CAPRI; until 7 November 2026, the model's SETA = VSET + FALL was exempt). The additive 100 is in CAPRI's units: 1000 ha
        # (crops, as the model) or 1000 head of CAPRI's activity (LEVL), converted to the model's herd units by
        # CAPRI's LEVL per model head in 2017 (capri_level_ratio.csv: poultry in thousand head against CAPRI's million,
        # fattening sheep, bulls and heifers counted as census stock against CAPRI's activity level).
        _lr = getattr(self.data, "capri_level_ratio", None)
        for i, a in enumerate(self.acts):
            if (a in FIXED_ACTIVITIES or (a in _unc and float(_x0f.get(a, 0.0)) > 1e-8)
                    or (a not in CROPS and a not in ANIMALS)):
                continue
            if a == "VSET" and float(_x0f.get(a, 0.0)) > self.VSET_DATA_MIN:
                # CAPRI's exemption only where the data have a set-aside level (set_supply_bounds.gms l. 42-43:
                # $ (p_technFact x DATA LEVL GT 1e-6)); without one VSET has no variable in CAPRI and takes the absent
                # rule below (found 13 November 2026: VSET from nothing in PL, CZ, RO, SK, CY and MT, 1.2 Mha in the
                # Green Deal 2030 run, where CAPRI's data have FALL only)
                for sg, bd in ((1.0, _n_techn(a) * self.VSET_UP), (-1.0, -_n_techn(a) * self.VSET_LO)):
                    row_v = np.zeros(n); row_v[i] = sg
                    A_rows.append(row_v); b_rows.append(bd)
                    self.ev.row_labels.append(f"bound_{a}_{'up' if sg > 0 else 'lo'}")
                continue
            v = float(_x0f.get(a, 0.0))
            if not v > float(_settings().get("supply.absent_level")):
                # CAPRI has no variable for an activity without a level at the calibration point (v_actLevl exists
                # only where p_technFact(..,"LEVL",..) is set, i.e. where the data have a level): held at zero
                # (K64: Norway's regions produced 6e-6 kt of tobacco from the solver's interior, which no trade
                # flow could take, and the market's residual stalled at 3e-6)
                if getattr(type(self), "absent_activities_fixed", False):
                    row_u = np.zeros(n); row_u[i] = 1.0
                    A_rows.append(row_u); b_rows.append(0.0); self.ev.row_labels.append(f"bound_{a}_absent")
                continue
            k_ = (float(_lr[a]) if a in ANIMALS and _lr is not None and a in _lr.index and pd.notna(_lr[a])
                  and float(_lr[a]) > 0 else 1.0)
            nt = _n_techn(a)
            add = 100.0 * k_ * nt
            hi, lo = max(10.0 * v, v + add), max(0.1 * v, nt * 1e-8)
            if a == "FALL" and _fall_up is not None:
                # CAPRI's "generous upper bound for FALL in case this is driven by scenario assumptions"
                # (set_supply_bounds.gms l. 159-160, after the rule above): with the landscape floor the fallow may
                # take half the UAA per technology (found 13 November 2026: RO010000, 12 kha of fallow and no
                # set-aside in the data, could not reach its 122 kha floor under 10 x its level)
                hi = _fall_up
            row_u = np.zeros(n); row_u[i] = 1.0
            A_rows.append(row_u); b_rows.append(hi); self.ev.row_labels.append(f"bound_{a}_up")
            row_l = np.zeros(n); row_l[i] = -1.0
            A_rows.append(row_l); b_rows.append(-lo); self.ev.row_labels.append(f"bound_{a}_lo")

        A_ub = np.array(A_rows)
        b_ub = np.array(b_rows)

        return A_ub, b_ub, np.zeros((0, n)), np.zeros(0)
