"""
CAPRI Policy Module
===================
Handles Common Agricultural Policy instruments and other trade policies.

CAP pillars implemented:
  Pillar I (direct payments):
    - Basic Income Support for Sustainability (BISS / former BPS)
    - Complementary Redistributive Income Support (CRIS)
    - Coupled support (for specific sectors)
    - Eco-schemes
    - Young farmers supplement

  Pillar II (rural development):
    - Agri-Environment-Climate Schemes (AECS)
    - Areas of Natural Constraint (ANC) payments
    - Organic farming support
    - Investment support

  Market measures:
    - Tariff Rate Quotas (TRQs)
    - Export subsidies (now mostly eliminated under WTO)
    - Intervention buying / public storage
    - Private storage aid

Reference: EU Regulation 2021/2115 (CAP Strategic Plans)
           CAPRI Policy Module documentation (Britz & Witzke 2012, Ch. 3)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


# ---------------------------------------------------------------------------
# ENUMS AND CONSTANTS
# ---------------------------------------------------------------------------




# (PaymentType, DirectPaymentScheme and EcoScheme - containers that no run used - were removed on 23 October 2026.)


@dataclass
class PolicyScenario:
    """
    Complete CAP / trade policy scenario specification.

    Used to parameterize the supply and market modules for
    counterfactual analysis.
    """
    name: str
    description: str = ""

    # Pillar I changes (relative to baseline)
    biss_rate_change: float = 0.0          # EUR/ha change in BISS rate
    coupled_support: Dict[str, float] = field(default_factory=dict)
    #: premium factors by model region and activity, {region: {activity: new/old}}: a CAPRI
    #: premium experiment applied as CAPRI's relative change of PRME (tools/run/run_vcs_2030.py)
    premium_factor_regional: Dict[str, Dict[str, float]] = field(default_factory=dict)
    #: share of Pillar I reported as eco-schemes (CAP 2023-2027: at least 25% of direct payments). Reporting only: the
    #: eco-schemes are inside Pillar I's budget (CAPRI's DPPIL1), so the share moves nothing in the supply models.
    eco_scheme_budget_pct: float = 0.25

    # Pillar II: relative changes of CAPRI's rural-development budgets (as CAPRI's RD scenarios change p_rdBudget,
    # policy/rd_logic.gms), e.g. -0.2 for a 20% cut. Each activity's premium changes by the change times the part
    # of its premium paid under the scheme (CAPRI's 2030 PRME by scheme, premium_scheme_shares_2030.csv). Until
    # 23 October 2026 these were EUR/ha rate changes (aecs_/anc_/organic_rate_change) scaled by participation
    # shares of 20%, 30% and 8% that had no source; CAPRI has no separate organic-farming scheme (its organic support
    # is inside the agri-environment groups), so the organic rate change was removed (PROXY_AUDIT S289, S292).
    lfa_budget_change: float = 0.0         # DPRD_LFA: areas of natural constraint (less favoured areas)
    ae_budget_change: float = 0.0          # DPAE: agri-environment (DPRD_AE1..8 and national AE schemes)
    n2k_budget_change: float = 0.0         # DPRD_N2K: Natura 2000

    # Trade measures
    tariff_changes: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # {region: {commodity: delta_pct}}
    trq_volume_changes: Dict[str, float] = field(default_factory=dict)
    # {commodity: change of the EU's tariff-rate quota volume, 1000 t}: spread over the commodity's quotas in CAPRI's
    # bilateral data (one per exporter) in proportion to their base volumes (MarketModule._apply_trq_volumes)

    # Environmental constraints
    set_aside_requirement: float = 0.0    # share of UAA as landscape elements
    #: Farm-to-Fork organic AREA target (share of UAA, e.g. 0.25 for 25%).
    #: An area target, not a payment. CAPRI models
    #: organic farming by adjusting the average input-output coefficients in
    #: proportion to the organic share (pol_input/greendeal/organic_io.gms:
    #: DATA(RU, organicCrops, "Yild", "percentageChange") = -yildReduction *
    #: p_organicAreaTarget), rather than tracking organic and conventional
    #: activities separately. This model does the same.
    organic_area_target: float = 0.0
    #: Farm-to-Fork nutrient-surplus target, applied as CAPRI applies it
    #: (JRC121368): a TIERED reduction of the gross nitrogen balance - 25% on
    #: the first 50 kg N/ha of surplus, 50% for 50-100, 75% for 100-150, 100%
    #: above 150. Set True to activate. This acts on SURPLUS, not on applied
    #: nitrogen; the two differ by roughly a factor of four in this model
    #: (median surplus 54 kg N/ha against applied intensity 241), so the tiered
    #: rule must never be applied to the applied-N basis directly.
    nutrient_surplus_target: bool = False
    #: how the surplus target is set per region (a scenario-configuration setting; default star 3.0's):
    #: "jrc121368" - the tiered rule and the nine-region 36% cap of JRC121368 (the 2020 CAPRI run);
    #: "star3" - CAPRI star 3.0's pol_input/greendeal/surptot.gms: every EU NUTS2 region's baseline
    #: surplus per hectare cut by surplus_cut (surpRedu/100), no tiers, no caps
    surplus_rule: str = "star3"
    surplus_cut: float = 0.5
    #: CAPRI's manure trade (GUI "New Manure Trade Module", manureTradeNew) for this scenario and its baseline;
    #: None = capri-mod's default (CAPRIModel.use_manure_market: on, as star 3.0's GUI)
    manure_trade: Optional[bool] = None
    #: CAPRI's endogenous biofuel markets (GUI "Endogenous bio-fuel markets", BIOF_M) for this scenario and its
    #: baseline; None = capri-mod's default (CAPRIModel.biofuel_markets: on, as star 3.0's GUI)
    biofuel_markets: Optional[bool] = None
    #: CAPRI's biofuel mandate scenario (scen/bio_fuels/change_biof_mandate.gms): the EU member states' and the
    #: UK's blending mandates (QUTS) times this factor; a policy shock of the scenario (None = unchanged). Acts
    #: with endogenous biofuel markets.
    biofuel_mandate: Optional[float] = None
    #: CAPRI's negProdPriceAllowed(rms, "MILK") / negProdPriceAllowedFromStart(rmssup, "MILK") (set by the Green Deal
    #: scenario file, pol_input/greendeal/greendeal_scenarios.gms l. 66-67): a member state's raw milk price may fall
    #: below zero. Without it CAPRI's lower bound on the price is widened toward zero but stays positive
    #: (arm/set_start_val.gms, widen_bounds.gms), and capri-mod holds the price just above zero, recording the member
    #: state whose milk market then does not clear (MarketModule.dairy_block)
    negative_milk_price: bool = False
    #: CAPRI's Green Deal mineral fertiliser reduction (greendeal_scenarios.gms, mineRedu; a policy shock of the
    #: scenario, EU27 only): "00" off; "20" minfert_redu_uaa.gms - mineral N per ha of UAA <= baseline x (1 - 20%)
    #: (e_synNMax); "10crp"/"13crp"/"17crp"/"20crp" minfert_redu_by_crop.gms - mineral N per ha of each crop group
    #: <= its baseline x (1 - r), groups below 30 kg/ha and CAPRI's listed exceptions held at baseline (nMax_ and the
    #: "f2f"/"limCres" regulations of the inner fertiliser model). docs/FERTILISER_ALLOCATION.md
    mineral_redu: str = "00"
    #: CAPRI's emission tax (ghgTax: p_carbonTax(ru, "GGWP"), pol_input/ecampa/carbtax50_endotech_*.gms), EUR per t
    #: CO2-eq on the EU regions' agricultural emissions inside the supply models; a policy shock of the scenario
    #: (0 = no tax). capri_mod/supply/ghg_tax.py
    carbon_tax: float = 0.0
    #: Farm-to-Fork pesticide-reduction target, as a share (0.50 for -50%): plant-protection expenditure cut by the
    #: remaining target on the conventional area, other inputs (INPO) raised by the same percentage, a minimum
    #: cover-crop area of half the target (pol_input/greendeal/pesticides.gms, conventional_io.gms;
    #: SupplyModel.apply_pesticide_reduction), and a yield loss depending on pesticide_rule.
    pesticide_reduction: float = 0.0
    #: Yield effect of the pesticide target. "jrc121368": the 2020 Farm-to-Fork study's assumption, an average
    #: yield loss of 10% at a 50% cut (scaled linearly), on conventional land; the organic yield gap applies in
    #: full to converted land (CAPRI scales it by 0.45 only with pest_disagg on, organic_area.gms). "star3": CAPRI star 3.0's Green Deal group as its code runs by default
    #: (pesticides.gms calls conventional_io.gms with the yield shock 'off'; pestDisaggStage none, so no
    #: endogenous pesticide yield response either): no pesticide yield loss, the full organic yield gap.
    pesticide_rule: str = "jrc121368"

    #: CAPRI's endogenous-technology settings for this run (capri_mod/policy/endotech.py), e.g.
    #: {"ghgTechMYld": 0.2}: scenario configuration parameters that, as in CAPRI (the scenario file loads
    #: refpol_endotech_all_sup), hold for the scenario AND the baseline it is compared with. Empty = CAPRI
    #: star 3.0 defaults (ghgTechMYld 0, ghgTechFEff 0.1).
    endotech: Dict[str, float] = field(default_factory=dict)

    # Production quotas (dairy, sugar — historically important)
    milk_quota: Optional[float] = None    # 1000 t (None = no quota)
    sugar_quota: Optional[float] = None


# ---------------------------------------------------------------------------
# DIRECT PAYMENTS ENGINE
# ---------------------------------------------------------------------------

class DirectPaymentsEngine:
    """CAP payments by region and their split over CAPRI's premium schemes (reporting and scenario premiums).

    The regional total is CAPRI's premium per hectare of UAA (cap_payments.csv BPS: CAPRI's PRME over all schemes,
    tools/build/build_crop_economics_2017.py) times the region's UAA. It is split over Pillar I (DPPIL1, coupled support
    included), the rural-development schemes (DPRD_LFA, DPRD_N2K, DPAE) and national payments (DPNAT) as the region's
    premiums are: each activity's base-year premium (crops: cap_premium x area; animals: livestock_premium_coef x
    heads) split by the shares of its premium paid under each scheme in CAPRI's 2030 reference (PRME by scheme,
    premium_scheme_shares_2030.csv). CAPRI's regional budgets (CEILVAL) are not used for the split: in the six
    member states with the single area payment CAPRI books Pillar I only at national level. National envelopes are
    CAPRI's 2030 total budgets (DPTOTAL) per CAPRI member state.
    """

    #: report column -> CAPRI scheme
    COMPONENTS = {"pillar1": "DPPIL1", "LFA": "DPRD_LFA", "N2K": "DPRD_N2K", "AE": "DPAE", "national": "DPNAT"}

    def __init__(self, scenario: Optional[PolicyScenario] = None, data: Optional[dict] = None):
        self.scenario = scenario or PolicyScenario(name="baseline")
        self.data = data or {}
        self.ceilings = self.data.get("cap_ceilings_2030")
        self._shares = None

    def _scheme_shares(self) -> pd.DataFrame:
        """region x scheme: the part of the region's base-year premiums paid under each CAPRI scheme."""
        if self._shares is None:
            sh = self.data.get("premium_scheme_shares_2030")
            if sh is None:
                raise ValueError("no CAPRI premium split by scheme (premium_scheme_shares_2030.csv, "
                                 "tools/build/build_cap_ceilings_2030.py)")
            prem, areas = self.data.get("cap_premium"), self.data.get("areas")
            lpc, herds = self.data.get("livestock_premium_coef"), self.data.get("animal_numbers")

            def w(r, a):
                for p_, l_ in ((prem, areas), (lpc, herds)):
                    if p_ is not None and l_ is not None and r in p_.index and a in p_.columns \
                            and r in l_.index and a in l_.columns:
                        v = float(p_.at[r, a]) * float(l_.at[r, a])
                        return v if v == v and v > 0 else 0.0
                return 0.0
            schemes = list(self.COMPONENTS.values())
            ww = pd.Series([w(r, a) for r, a in zip(sh["region"], sh["activity"])], index=sh.index)
            num = sh[schemes].mul(ww, axis=0).groupby(sh["region"]).sum()
            den = ww.groupby(sh["region"]).sum()
            self._shares = num.div(den.where(den > 0), axis=0)
        return self._shares

    def compute_payments_by_region(self, cap_data: pd.DataFrame, land_data: pd.DataFrame) -> pd.DataFrame:
        """CAP payments per region (EUR 1000) by CAPRI premium scheme, under the scenario's changes."""
        from capri_mod.data.definitions import REGION_TO_COUNTRY
        sc = self.scenario
        chg = {"LFA": sc.lfa_budget_change, "AE": sc.ae_budget_change, "N2K": sc.n2k_budget_change}
        if "BPS" not in cap_data.columns:              # no stand-in (removed 23 October 2026: 200 EUR/ha)
            raise ValueError("cap_payments.csv has no BPS column")
        rows = []
        for region in cap_data.index:
            if region not in land_data.index:              # no stand-in (removed 23 October 2026: 100 kha)
                raise ValueError(f"{region}: no land in land_availability.csv")
            # BPS is CAPRI's premiums per ha of UAAR, and CAPRI's UAAR holds fallow (SETA, FALL): the same area here
            # (KNOWN_ISSUES K104; until 29 October 2026 fallow was left out)
            uaa = float(land_data.loc[region, [c for c in ("ARABLE", "PERMANENT", "GRASSLAND", "FALLOW")
                                               if c in land_data.columns]].sum())
            total0 = float(cap_data.at[region, "BPS"]) * uaa          # EUR/ha x 1000 ha = EUR 1000
            shr = self._scheme_shares()
            ceil = shr.loc[region] if region in shr.index and shr.loc[region].notna().all() else None
            if ceil is None and total0 == 0.0:
                ceil = pd.Series(0.0, index=list(self.COMPONENTS.values()))      # no farmland, no premiums
            row = {"region": region, "country": REGION_TO_COUNTRY.get(region, "XX"), "UAA_1000ha": uaa,
                   "premium_EUR_ha_UAA": float(cap_data.at[region, "BPS"])}
            for col, scheme in self.COMPONENTS.items():
                part = total0 * float(ceil[scheme]) if ceil is not None else float("nan")
                row[col] = part * (1.0 + float(chg.get(col, 0.0) or 0.0))
            if ceil is not None:
                row["pillar1"] += float(sc.biss_rate_change or 0.0) * uaa
            row["eco_scheme"] = row["pillar1"] * float(sc.eco_scheme_budget_pct or 0.0)   # inside Pillar I
            row["pillar2"] = row["LFA"] + row["N2K"] + row["AE"]
            row["total_payments"] = (row["pillar1"] + row["pillar2"] + row["national"]) if ceil is not None \
                else total0 + float(sc.biss_rate_change or 0.0) * uaa
            rows.append(row)
        return pd.DataFrame(rows).set_index("region")

    def compute_national_budgets(self, regional_payments: pd.DataFrame) -> pd.DataFrame:
        """Payments by CAPRI member state against CAPRI's 2030 budgets (DPTOTAL, EUR million). The simulated
        payments are CAPRI's 2017 premiums on the model's land, so the comparison is between years."""
        from capri_mod.data.definitions import capri_ms
        if self.ceilings is None:
            raise ValueError("no CAPRI CAP budgets (cap_ceilings_2030.csv, tools/build/build_cap_ceilings_2030.py)")
        sim = regional_payments["total_payments"].groupby([capri_ms(r) for r in regional_payments.index]).sum() / 1000.0
        env = self.ceilings["DPTOTAL"].reindex(sim.index)
        budget = pd.DataFrame({"simulated_EUR_million": sim, "envelope_EUR_million": env})
        budget["utilisation_pct"] = budget["simulated_EUR_million"] / budget["envelope_EUR_million"] * 100.0
        return budget


# (InterventionSystem, a stub with invented trigger factors that nothing called, was removed 23 October 2026; CAPRI's
# intervention-stock system - arm/market_model.gms buyingToIntervStock_, releaseFromIntervStock_ - is to be ported
# into the market module.)


# ---------------------------------------------------------------------------
# POLICY MODULE COORDINATOR
# ---------------------------------------------------------------------------

class PolicyModule:
    """
    Coordinates all CAP and trade policy instruments.

    Called at the start of each scenario run to:
      1. Compute payment rates → feed to supply module (net revenues)
      2. Compute tariffs / TRQ status → feed to market module
      3. Track compliance costs and environmental conditionality
    """

    def __init__(
        self,
        data: dict,
        scenario: Optional[PolicyScenario] = None,
    ):
        self.data     = data
        self.scenario = scenario or PolicyScenario(name="baseline")

        self.payments   = self._engine(self.scenario)

    def apply_scenario(self, scenario: PolicyScenario):
        """Switch to a new policy scenario.

        Quota instruments are declared on PolicyScenario but are NOT implemented
        anywhere in the supply solve. Rather than accept them and silently return
        baseline results — the failure mode that left every CAP scenario inert
        until it was caught by validating against CAPRI — they are refused
        explicitly. Milk quotas ended in 2015 and sugar quotas in 2017, so for a
        2017-based model they are historical instruments; if needed they must
        first be implemented as constraints in SupplyModel._build_constraints.
        """
        for field_name in ("milk_quota", "sugar_quota"):
            if getattr(scenario, field_name, None) is not None:
                raise NotImplementedError(
                    f"PolicyScenario.{field_name} is declared but not implemented "
                    "in the supply solve, so setting it would silently produce "
                    "baseline results. Implement it as a constraint in "
                    "SupplyModel._build_constraints before using this instrument."
                )
        self.scenario = scenario
        self.payments = self._engine(scenario)

    def _engine(self, scenario: PolicyScenario) -> DirectPaymentsEngine:
        return DirectPaymentsEngine(scenario, data=self.data)


    def get_payment_rates_by_region(self) -> pd.DataFrame:
        """Compute and return regional payment rates for supply module."""
        return self.payments.compute_payments_by_region(
            cap_data=self.data["cap_payments"],
            land_data=self.data["land"],
        )

    def get_effective_tariffs(self) -> pd.DataFrame:
        """
        Return the tariff matrix [region × commodity] with the scenario's tariff changes. The EU's tariff-rate
        quotas act in the bilateral market (market/bilateral.py, CAPRI's TRQ regime; trq_volume_changes).
        """
        base_tariffs = self.data["tariffs"].copy()

        # Apply scenario tariff changes
        for region, changes in self.scenario.tariff_changes.items():
            for comm, delta in changes.items():
                if region in base_tariffs.index and comm in base_tariffs.columns:
                    base_tariffs.at[region, comm] = max(
                        0, base_tariffs.at[region, comm] + delta
                    )

        return base_tariffs

    def get_supply_policy_adders(self) -> pd.Series:
        """Per-activity premium changes added to net revenues (EUR/ha or EUR/head): the BISS rate change on every
        crop but set-aside, and coupled support. The model differences them against the baseline's, so only the
        scenario's change enters. Eco-schemes are inside Pillar I (eco_scheme_budget_pct is a reporting split), and
        the Pillar II budget changes act per region and activity (get_premium_factors_regional)."""
        from capri_mod.data.definitions import CROPS, ALL_ACTIVITIES
        adders = pd.Series(0.0, index=ALL_ACTIVITIES)
        d = float(self.scenario.biss_rate_change or 0.0)
        if d:
            for crop in CROPS:
                if crop != "SETA":
                    adders[crop] += d
        for comm, rate in self.scenario.coupled_support.items():
            if comm in adders.index:
                adders[comm] += rate
        return adders

    def get_premium_factors_regional(self) -> Dict[str, Dict[str, float]]:
        """Premium factors {region: {activity: new/old}}: the scenario's own (premium_factor_regional) times the
        Pillar II budget changes, 1 + sum_s change_s x share_s(region, activity), with share_s the part of the
        activity's premium paid under scheme s in CAPRI's 2030 reference (premium_scheme_shares_2030.csv)."""
        sc = self.scenario
        out = {r: dict(v) for r, v in (getattr(sc, "premium_factor_regional", None) or {}).items()}
        chg = {"DPRD_LFA": float(sc.lfa_budget_change or 0.0), "DPAE": float(sc.ae_budget_change or 0.0),
               "DPRD_N2K": float(sc.n2k_budget_change or 0.0)}
        if not any(chg.values()):
            return out
        sh = self.data.get("premium_scheme_shares_2030")
        if sh is None:
            raise ValueError("Pillar II budget changes need CAPRI's premium split by scheme "
                             "(premium_scheme_shares_2030.csv, tools/build/build_cap_ceilings_2030.py)")
        f = 1.0 + sum(c * sh[k] for k, c in chg.items() if c)
        for r, a, v in zip(sh["region"], sh["activity"], f):
            if v != 1.0:
                out.setdefault(r, {})
                out[r][a] = out[r].get(a, 1.0) * float(v)
        return out

    def summarise_policy(self) -> Dict:
        """Policy scenario summary: payments by region and scheme, member-state budgets against CAPRI's 2030 ones."""
        regional = self.get_payment_rates_by_region()
        national = self.payments.compute_national_budgets(regional)
        eu = [r for r in regional.index if not str(r).startswith("NO")]
        uaa = float(regional.loc[eu, "UAA_1000ha"].sum())
        return {
            "scenario_name": self.scenario.name,
            "total_EU_budget_EUR_billion": regional.loc[eu, "total_payments"].sum() / 1e6,
            "pillar1_EUR_billion": regional.loc[eu, "pillar1"].sum() / 1e6,
            "pillar2_EUR_billion": regional.loc[eu, "pillar2"].sum() / 1e6,
            "premium_EUR_ha_UAA": regional.loc[eu, "total_payments"].sum() / uaa if uaa > 0 else float("nan"),
            "national_budgets": national,
        }
