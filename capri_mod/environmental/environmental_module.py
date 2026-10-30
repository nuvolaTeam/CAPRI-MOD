"""
CAPRI Environmental Module
==========================
Computes environmental indicators from supply module outputs.

Indicators implemented:
  1. GHG emissions (CH4, N2O, CO2) following IPCC Tier 1/2 methodology
  2. Nitrogen balance (inputs - outputs = surplus, a pollution proxy)
  3. Phosphate balance (CAPRI's gross balance in P2O5, calc_nbalance.gms)
  4. Land use indicators (UAA, crop diversity)
  5. Pesticide use index (simplified)
  6. Ammonia emissions (NH3)
  7. Water use / irrigation demand

References:
  - IPCC (2019) Refinement to the 2006 GL for National GHG Inventories
  - EEA (2020) European Environment Agency nitrogen indicators
  - CAPRI Environmental Module documentation (Pérez-Domínguez et al. 2016)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Optional

from capri_mod.params import param, param_table
from capri_mod.settings import setting
from capri_mod.fert.npk import need_yield_factor
from capri_mod.data.definitions import (
    CROPS, ANIMALS, ALL_ACTIVITIES, NUTRIENTS, GHG_TYPES,
)
from capri_mod.data.definitions import MS_CODE, capri_ms, IdentityMap
from capri_mod.tableio import read_input


# ---------------------------------------------------------------------------
# IPCC FACTORS AS CAPRI USES THEM (envind/gases.gms; GHGInv/tables2006ipcc.gms)
# ---------------------------------------------------------------------------
# N2O from mineral and residue N: EF1 direct 1%, volatilised share 10% x EF4 1% (gases.gms N2OSYN, N2OCRO)
EF_SOIL_N2O_DIRECT   = param("EF_SOIL_N2O_DIRECT")
EF_SOIL_N2O_INDIRECT = param("EF_SOIL_N2O_INDIRECT")
# global warming potentials, AR4 (UNFCCC reporting, CAPRI p_globWarmPot)
GWP_CH4 = param("GWP_CH4")
GWP_N2O = param("GWP_N2O")
# Every other coefficient of the accounts is CAPRI's own regional data (manure N, manure N2O shares, ammonia
# shares, manure and enteric CH4 per head, liming and urea CO2, crop N, deposition). The IPCC Tier 1 and
# literature tables that stood here as fallbacks were removed (Sprint 9s, docs/SYNTHETIC_DATA_AUDIT.md): a
# region without CAPRI's data now fails loudly instead of taking a generic value.


@dataclass
class EnvironmentalIndicators:
    """Environmental indicators for a region or aggregate.

    The @dataclass decorator had gone missing, so constructing it with its
    fields raised a TypeError - the second of two errors that left every
    model run's environmental table empty.
    """
    region: str

    # GHG (kt CO2-equivalent)
    ghg_enteric: float = 0.0
    ghg_manure_ch4: float = 0.0
    ghg_manure_n2o: float = 0.0
    ghg_soil_n2o: float = 0.0
    ghg_histosol_n2o: float = 0.0
    #: of ghg_manure_n2o: the ammonia technologies' effect against their base shares (direct and
    #: through the loss cascade), kt CO2eq - JRC121368 Table 18 reports the same split
    ghg_manure_n2o_tech: float = 0.0
    ghg_residue_n2o: float = 0.0
    ghg_indirect_n2o: float = 0.0
    #: indirect N2O of the N leached and run off from the fields (CAPRI gases.gms N2OLEA allocated to crops;
    #: capri_mod/supply/n_leaching.py); the housing runoff's is in ghg_manure_n2o
    ghg_leaching_n2o: float = 0.0
    #: CAPRI's leaching share of the soil surplus (v_nitrBalance(Leach)) and the N leached and run off from the
    #: fields that carries the indirect N2O (t N)
    leach_share: float = 0.0
    n_runoff_leached: float = 0.0
    ghg_liming: float = 0.0
    ghg_urea: float = 0.0
    #: all items; non-CO2 (CH4 + N2O, JRC121368's "non-CO2 GHG"); CAPRI's GGWP, the emission tax's base
    #: (supply_model.gms GWPTOT_: CH4 + N2O + GCO2, GCO2 = liming only)
    ghg_total: float = 0.0
    ghg_non_co2: float = 0.0
    ghg_ggwp: float = 0.0

    # Nitrogen (t N: area in 1000 ha x kg N/ha)
    n_mineral_input: float = 0.0
    n_organic_input: float = 0.0
    n_fixation: float = 0.0
    n_deposition: float = 0.0
    n_crop_uptake: float = 0.0
    n_animal_products: float = 0.0
    n_surplus: float = 0.0        # Gross N surplus (potential pollution)
    n_use_efficiency: float = 0.0  # NUE = outputs / inputs

    # Phosphate: CAPRI's gross P balance, in P2O5 as CAPRI reports phosphate (reports/calc_nbalance.gms, FNUT = PHOF;
    # compute_phosphorus_balance). t P2O5 (1000 ha x kg/ha, as the N items; CAPRI's tables are in 1000 t P2O5;
    # P = 0.4364 x P2O5)
    p_input: float = 0.0               # IMPORT = EXCRET - MTRADE + MINFER + CRESID
    p_uptake: float = 0.0              # EXPPRD: removal with crop products (retention)
    p_surplus: float = 0.0             # SURTOT = IMPORT - EXPPRD, the gross balance
    p_mineral_input: float = 0.0       # MINFER: mineral P2O5 bought
    p_manure_excretion: float = 0.0    # EXCRET
    p_manure_net_export: float = 0.0   # MTRADE: manure P2O5 exported less imported
    p_crop_residues: float = 0.0       # CRESID
    p_runoff: float = 0.0              # RUNANI: manure P2O5 run off (CAPRI's N runoff share)
    p_surplus_soil: float = 0.0        # SURSOI = SURTOT - RUNANI

    # Ammonia (kt NH3)
    nh3_livestock: float = 0.0
    nh3_soils: float = 0.0
    nh3_total: float = 0.0

    # Land use (1000 ha)
    uaa_total: float = 0.0
    arable_land: float = 0.0
    permanent_crops: float = 0.0
    grassland: float = 0.0
    #: area under organic farming added by the scenario's organic area target (1000 ha): each crop's area x its
    #: converted share (SupplyModel._organic_conv, organic_area.gms). CAPRI's targets are percentage points above the
    #: baseline's organic area, which neither CAPRI's data nor capri-mod's hold, so it is 0 without a target
    organic_area: float = 0.0

    # Biodiversity proxy
    shannon_crop_diversity: float = 0.0

    def to_series(self) -> pd.Series:
        return pd.Series(self.__dict__)


# ---------------------------------------------------------------------------
# ENVIRONMENTAL MODULE
# ---------------------------------------------------------------------------

from capri_mod.environmental.blocks import (  # noqa: E402  (refactor stage 4a: the blocks)
    GHGBlock, NitrogenBlock, AmmoniaBlock, PhosphorusBlock, BiodiversityBlock,
)


class EnvironmentalModule(GHGBlock, NitrogenBlock, AmmoniaBlock, PhosphorusBlock, BiodiversityBlock):
    """
    Computes environmental indicators from supply module outputs.

    Takes SupplyResult objects and nutrient data, returns
    EnvironmentalIndicators for each region.
    """

    def __init__(self, data: dict):
        self.data = data
        # Mineral N per ha: CAPRI's regional NMIN (data["mineral_n_regional"], _base_mineral_rate). A national
        # table without builder (data["nutrients"], nutrient_coefs.csv) stood under it until 29 October 2026 and gave
        # fallow and set-aside 4.8 kg N/ha where CAPRI applies none (KNOWN_ISSUES K100). A removal x yield x efficiency
        # derivation (FertilizerModule) was removed on 23 October 2026 (PROXY_AUDIT S213, S214).


    #: CAPRI's slope of manure availability on manure applied per ha (fert/endoManAvail.gms)
    ENDO_MAN_AV_SLOPE = -0.0015


    #: CAPRI crop -> model crop (several CAPRI crops pooled by level)
    _CAPRI_CROP = {"CORN": ("MAIZ",), "WINE": ("TWIN",), "GRAS": ("GRAE", "GRAI"),
                   "OFOD": ("OFAR", "ROOF"), "SETA": ("SETA", "FALL", "VSET")}
    _CROP_N = None


    #: CAPRI (eq. 5.10, fertiliser distribution): "crop residues can be re-distributed among crop
    #: groups for annual arable crops but not for grassland and permanent crops, where it stays
    #: with the crop that produced it"
    #: crops whose own residues cover their own need, CAPRI's permanent crop groups (supply/define_ngrp_sets.gms
    #: PERM_NGRP: GRAS, and PERM = OLIV, TABO, TAGR, TWIN, CITR, APPL); every other crop draws on the arable residue
    #: pool (fertDistCres_). Other fruit (VEGE in CAPRI) and nurseries (OAFC) were here until Sprint 9e.
    OWN_RESIDUE_CROPS = frozenset({"GRAS", "APPL", "CITR", "TAGR", "WINE", "OLIV", "TABO"})


    _ENT_CACHE = None


    _FERT_SIDE = None


    #: anaerobic digestion on dairy cows' manure CH4: "fix" applies CAPRI's CH4 factor to DCOL/DCOH as to the other
    #: animals (the user's decision, 20 October 2026); "capri" reproduces CAPRI as coded, where ad_data_and_cali.gms
    #: l. 588 zeroes the NOC CH4MAN_3k factor the dairy macro needs, so dairy AD has no CH4 effect (docs/AD_SPEC.md)
    ad_dairy_ch4 = setting("environment.ad_dairy_ch4")


    # ------------------------------------------------------------------------------------------------------------------
    # PHOSPHATE (P2O5) BALANCE: CAPRI's reports/calc_nbalance.gms with FNUT = PHOF (capri_mod/environmental/p_balance.py)
    # ------------------------------------------------------------------------------------------------------------------


    def compute_indicators(
        self,
        supply_result,  # SupplyResult
        land: Optional[pd.Series] = None,
    ) -> EnvironmentalIndicators:
        """
        Compute full set of environmental indicators for one region.

        Parameters
        ----------
        supply_result : SupplyResult from supply module
        land          : land availability series for the region
        """
        acts   = supply_result.activities
        region = supply_result.region_id
        # nitrate shares of this region's rations, BEFORE the GHG calculation uses them
        self._nitrate_share_now = dict(getattr(supply_result, "nitrate_share", None) or {})
        # CAPRI's feed supplements (envind/line_nitr.gms; Sprint 9g): enteric CH4 per head of the adopting share
        # x (1 + ch4ent_rel) - linseed -25%, nitrate -15%; both on the same animals (AComLN) multiply, the
        # overlap taken as large as the shares allow (CAPRI's maximum run puts all its linseed on nitrate
        # cows; without an emission price the split is not determined: REGISTERED)
        _supp = {}
        _lvs = getattr(supply_result, "activities", None)
        _gtab_s = (self.data.get("genetics_effects") or {}).get(region) if hasattr(self, "data") else None
        if _gtab_s and _lvs is not None:
            _sh = {}
            for (_ga, _go), _gz in (getattr(supply_result, "genetics_shift", None) or {}).items():
                _e = _gtab_s.get((_ga, _go))
                _h = float(_lvs.get(_ga, 0.0) or 0.0)
                if _e is None or _h <= 0 or not _gz or "ch4ent_rel" not in _e.index or not pd.notna(_e["ch4ent_rel"]):
                    continue
                _sh.setdefault(_ga, {})[_go] = (min(1.0, max(0.0, float(_gz) / _h)), float(_e["ch4ent_rel"]))
            for _ga, _l in _sh.items():
                _f = 1.0 + sum(s_ * r_ for s_, r_ in _l.values())
                # linseed and nitrate on the same animals (CAPRI's AComLN): their effects multiply; 3-NOP adds
                # (line_nitr.gms l. 107-121, 124-134; ghgMiti.gms sums the options' QEmitt changes)
                if "LINE_Tot" in _l and "Nitr_Tot" in _l:
                    (sL, rL), (sN, rN) = _l["LINE_Tot"], _l["Nitr_Tot"]
                    _f += rL * rN * min(sL, sN)
                _supp[_ga] = max(0.0, _f)
        if not hasattr(self, "_supp_ch4"):
            self._supp_ch4 = {}
        self._supp_ch4[region] = _supp
        # feed dry matter per animal (feeding inside the supply model), and the region
        self._feed_dm_now = dict(getattr(supply_result, "feed_dm", None) or {})
        self._region_now = region

        yields = self.data["yields"].loc[region] if region in self.data["yields"].index \
                 else pd.Series(dtype=float)
        # Crop uptake must use the yields of THIS solution, not the base year's:
        # under a scenario, lower fertiliser, pesticide and organic yields lower
        # uptake too. With base yields the accounts counted the fertiliser cut
        # but not the lost uptake, so the reported nitrogen surplus fell far more
        # than it did (Farm-to-Fork: -47.5% against the constraint's own cut).
        # Realised yield = gross output / area, wherever both are positive.
        try:
            go = getattr(supply_result, "gross_output", None)
            ac = getattr(supply_result, "activities", None)
            if go is not None and ac is not None:
                realised = {c: float(go[c]) / float(ac[c]) for c in CROPS
                            if c in go.index and c in ac.index
                            and float(ac[c]) > 1e-9 and float(go[c]) > 0}
                if realised:
                    yields = yields.copy()
                    for c, v in realised.items():
                        yields[c] = v
        except Exception:
            pass

        if land is None:
            land = self.data["land"].loc[region] if region in self.data["land"].index \
                   else pd.Series(dtype=float)

        # GHG
        mint = dict(getattr(supply_result, "n_intensity", {}) or {})
        _gz = float(getattr(supply_result, "grass_ext_shift", 0.0) or 0.0)
        ghg = self.compute_ghg(acts, region, mint, grass_shift=_gz)
        ghg_total = sum(ghg.values())

        # Nitrogen (the straw part of crop need follows the yields before the price response: need_yield_factor)
        _pf = (getattr(supply_result, "yield_price_factor", None) or {}) if supply_result is not None else {}
        _ysc = {c: float(yields.get(c)) / f for c, f in _pf.items()
                if f > 0 and hasattr(yields, "get") and yields.get(c) is not None} or None
        nb = self.compute_nitrogen_balance(acts, yields, region, mint, yields_scen=_ysc)
        _nb_raw = dict(nb)
        # MANURE MARKET (when on): the region's endogenous manure trade and its
        # allocated mineral N (fertiliser allocation) replace the fixed-rule
        # values, so the reported balance is the one the regional model met.
        _mt = getattr(supply_result, "manure_trade", None)
        _ma = getattr(supply_result, "mineral_n_alloc", None)
        if _mt and (abs(_mt[0]) > 0 or abs(_mt[1]) > 0):
            # traded manure, with the balance's own linear substitution:
            # organic +-1, mineral -+a, surplus +-(1 - a) per t (net imports)
            _d = float(_mt[1]) - float(_mt[0])
            _a = float(getattr(supply_result, "manure_availability", 0.0) or 0.0)   # substitution factor used (0 at the floor)
            nb["n_organic_input"] = float(nb["n_organic_input"]) + _d
            nb["n_mineral_input"] = float(nb["n_mineral_input"]) - _a * _d
            nb["n_surplus"] = float(nb["n_surplus"]) + (1.0 - _a) * _d
        # CAPRI's grassland split (Sprint 7a): the area moved from GRAI to GRAE changes the
        # balance by the same per-ha difference the supply model's N row used
        if _gz:
            _dl = self.grass_intensity_delta(region) or {}
            for _k, _v in _dl.items():
                if _k in nb and isinstance(nb[_k], (int, float)) and _k != "n_use_efficiency":
                    nb[_k] = float(nb[_k]) + _gz * float(_v)
        # CAPRI's dairy split (Sprint 7b): z cows at DCOL instead of DCOH excrete
        # (MANN_DCOL - MANN_DCOH) / MANN_DCOW of a cow's manure N more each - the supply model's
        # manure rows use the same factor. Accounted as k = z x that factor manure-equivalent cows:
        # the balance and manure N2O with and without them (enteric CH4 already follows the cows'
        # feed; manure CH4 per head is left unchanged: REGISTERED)
        _dz = float(getattr(supply_result, "dairy_low_shift", 0.0) or 0.0)
        _dk = 0.0
        _dtab = self.data.get("dairy_intensity") if hasattr(self, "data") else None
        if _dz and _dtab is not None and region in _dtab.index:
            _dk = _dz * float(_dtab.at[region, "dmann_rel"])
        # the bull and heifer splits (Sprint 7c) the same way: z stalls at the low-intensity activity
        # carry (MANN per stall, low - high) / average of the animal's manure N
        _kk = {"DCOW": _dk} if _dk else {}
        _ctab = (self.data.get("cattle_intensity") or {}).get(region) if hasattr(self, "data") else None
        for _k, _z in (getattr(supply_result, "cattle_shift", None) or {}).items():
            # every split of the animal (key "HFRS", "HFRS:rep", "CALV:male", ...)
            _a = _k.split(":")[0]
            if _z and _ctab and _k in _ctab:
                _kk[_a] = float(_kk.get(_a, 0.0)) + float(_z) * float(_ctab[_k]["dmann_rel"])
        # cattle genomics (breeding.gms): g animals adopting excrete d_mann_rel more (genet_yld) or less
        # (genet_eff) manure N each; enteric CH4 follows the animals' feed as for the splits
        _gtab = (self.data.get("genetics_effects") or {}).get(region) if hasattr(self, "data") else None
        for (_ga, _go), _gz in (getattr(supply_result, "genetics_shift", None) or {}).items():
            if _gz and _gtab and (_ga, _go) in _gtab:
                _kk[_ga] = float(_kk.get(_ga, 0.0)) + float(_gz) * float(_gtab[(_ga, _go)]["d_mann_rel"])
        _acts_k = None
        if _kk:
            _acts_k = dict(acts) if isinstance(acts, dict) else acts.copy()
            for _a, _v in _kk.items():
                _acts_k[_a] = float(_acts_k.get(_a, 0.0)) + _v
            _nb_k = self.compute_nitrogen_balance(_acts_k, yields, region, mint, yields_scen=_ysc)
            _nb_0 = self.compute_nitrogen_balance(acts, yields, region, mint, yields_scen=_ysc)
            for _k in ("n_organic_input", "n_mineral_input", "n_mineral_plain", "n_surplus"):
                if _k in nb and _k in _nb_k:
                    nb[_k] = float(nb[_k]) + float(_nb_k[_k]) - float(_nb_0[_k])
            _g_k = self.compute_ghg(_acts_k, region, mint, grass_shift=_gz)
            if "N2O_MAN" in ghg:
                ghg["N2O_MAN"] += float(_g_k.get("N2O_MAN", 0.0)) - float(ghg["N2O_MAN"])
        _rel = getattr(supply_result, "animal_n_relief", None) or {}
        self._nh3_saved_last = 0.0                  # per region: never carried over
        self._n_kept_last = 0.0
        self._nitrate_share_now = dict(getattr(supply_result, "nitrate_share", None) or {})
        self._nitrate_nh3_extra = 0.0
        _nx = getattr(supply_result, "nitrate_n_extra", None) or {}
        if _nx:
            # nitrate N excreted: manure like any other (organic +, mineral - sub, surplus + (1 - sub))
            _lv2 = getattr(supply_result, "activities", None)
            if _lv2 is None:
                _lv2 = {}
            _sb = float(getattr(supply_result, "n_substitution", 0.0) or 0.0)
            _dx = sum(float(v) * float(_lv2.get(a, 0.0)) for a, v in _nx.items())
            nb["n_organic_input"] = float(nb["n_organic_input"]) + _dx
            nb["n_mineral_input"] = float(nb["n_mineral_input"]) - _sb * _dx
            nb["n_surplus"] = float(nb["n_surplus"]) + (1.0 - _sb) * _dx
            _fs = (self._nh3_factors().get(region) or {}).get("manure_share", {}) if region else {}
            self._nitrate_nh3_extra = sum(float(v) * float(_lv2.get(a, 0.0)) * float(_fs.get(a, 0.0)) for a, v in _nx.items())
        if _rel:
            _lv = getattr(supply_result, "activities", None)
            if _lv is None:
                _lv = {}
            _d = sum(float(v) * float(_lv.get(a, 0.0)) for a, v in _rel.items())
            nb["n_mineral_input"] = float(nb["n_mineral_input"]) - _d
            nb["n_surplus"] = float(nb["n_surplus"]) - _d
            self._nh3_saved_last = sum(float(v) * float(_lv.get(a, 0.0))
                                       for a, v in (getattr(supply_result, "animal_nh3_saved", None) or {}).items())
            # N kept in the manure: every loss CAPRI's cascade has (GasRunTot), the NH3 above being part of it
            _kp = getattr(supply_result, "animal_n_kept", None)
            self._n_kept_last = (sum(float(v) * float(_lv.get(a, 0.0)) for a, v in _kp.items()) if _kp
                                 else self._nh3_saved_last)
        if _ma is not None:
            _d = float(_ma) - float(nb["n_mineral_input"])
            nb["n_mineral_input"] = float(_ma)
            nb["n_surplus"] = float(nb["n_surplus"]) + _d
        # CAPRI's catch crops beyond the base share (the Farm-to-Fork requirement, or the share the NLP form chose:
        # supply result's cover_crops): their N (BioFix x area) is an input of the balance and supplies crop need;
        # with mineral N allocated in the supply model it is already net of it, else it replaces mineral N here
        _cv = getattr(supply_result, "cover_crops", None) or {}
        _cn = float(_cv.get("delta", 0.0) or 0.0) * float(_cv.get("biofix", 0.0) or 0.0) * 1000.0
        if _cn != 0:
            nb["n_fixation"] = float(nb["n_fixation"]) + _cn
            nb["n_surplus"] = float(nb["n_surplus"]) + _cn
            if _ma is None:
                _r = min(_cn, max(0.0, float(nb["n_mineral_input"])))
                nb["n_mineral_input"] = float(nb["n_mineral_input"]) - _r
                nb["n_surplus"] = float(nb["n_surplus"]) - _r
        # CAPRI's inner fertiliser distribution model (star 3.0 default useInnerFertDistModel): the region's
        # mineral N, manure N applied and arable residue pool distributed over CAPRI's crop groups, with the
        # mineral fertiliser reduction's regulations when the scenario has them (reporting; the regional totals
        # are the balance's own)
        try:
            _fdm = getattr(supply_result, "fert_dist_model", None)
            if _fdm:
                # the allocation the regional model solved (CAPRI reports v_fertDist of its supply model): the inner
                # model at the model's own totals, or the coupled NLP where it had no solution there
                _mc = getattr(supply_result, "mineral_cap", None) or {}
                _gc = _mc.get("group_caps") or {}
                self._fert_dist_now = [
                    dict(region=region, capri_region=_fdm.get("capri_region"), ngrp=g, area_kha=float(A),
                         mine_kg_ha=float(_fdm["flows"].get((g, "MINE"), 0.0)) / A if A > 0 else 0.0,
                         excr_kg_ha=float(_fdm["flows"].get((g, "EXCR"), 0.0)) / A if A > 0 else 0.0,
                         cres_kg_ha=float(_fdm["flows"].get((g, "CRES"), 0.0)) / A if A > 0 else 0.0,
                         mine_cap_kg_ha=float(_gc.get(g, float("nan"))) if _gc else float("nan"),
                         cap_scale=1.0, converged=True)
                    for g, A in _fdm["area"].items()]
            else:
                self._fert_dist_now = self.fert_distribution(region, acts, yields, nb, _nb_raw,
                                                             getattr(supply_result, "mineral_cap", None),
                                                             getattr(supply_result, "fert_dist_mode_crops", None),
                                                             getattr(supply_result, "fert_dist_priors", None),
                                                             yields_scen=_ysc)
        except Exception as _exc:
            import warnings as _w
            _w.warn(f"inner fertiliser distribution failed for {region}: {_exc!r}")
            self._fert_dist_now = None
        # soil N2O from MINERAL fertiliser (CAPRI N2OSYN; JRC121368's "N2O mineral fertiliser"): the
        # balance's own mineral N (after substitution, yield effects, technologies, catch crops) x
        # (direct + volatilised share x indirect factor). It used to be crops' N coefficients (16.6 Mt N
        # in the EU, mineral and organic) rescaled by the mineral ratio, so manure-borne soil N2O moved
        # with mineral N; manure N2O is N2O_MAN. Crop residues are their own source (CAPRI N2OCRO).
        # The factors are CAPRI's (gases.gms (7) N2OSYN = NMIN x emiLoss(NETF, N2O) and the mineral part of (9) N2OAMM =
        # NMIN x (emiLoss(NETF, NH3) + emiLoss(NETF, NOx)) x EF4), from the region's MITERRA loss fractions (K74 S12,
        # 27 October 2026; before, IPCC's EF1 + 10% x EF4 everywhere); IPCC's where CAPRI's fractions are missing
        _dn = self._mineral_n2o_n(region)
        if "N2O_SOIL" in ghg:
            ghg["N2O_SOIL"] = (max(0.0, float(nb.get("n_mineral_input", 0.0))) / 1000.0
                               * (_dn[0] + _dn[1]) * 44.0 / 28.0 * GWP_N2O)
        ghg["N2O_CRO"] = (max(0.0, float(nb.get("n_crop_residues", 0.0) or 0.0)) / 1000.0
                          * EF_SOIL_N2O_DIRECT * 44.0 / 28.0 * GWP_N2O)
        # CO2 from urea on the same mineral N (CAPRI gases.gms (17): NMIN x urea share x 44/28)
        ghg["CO2_UREA"] = (max(0.0, float(nb.get("n_mineral_input", 0.0))) / 1000.0
                           * self._co2_coefs(region)[1] * 44.0 / 28.0)

        # CAPRI's N2O from drained organic soils (gases.gms N2OHIS, agriculture): per ha of the land-use
        # class, its organic-soil share x the climate-weighted IPCC 2013 factor (tools/build/build_histosol.py),
        # on the area in use; the fallowed histosol area emits nothing (QEmitt = 0 in the Green Deal runs)
        _ht = self.data.get("histosol") if hasattr(self, "data") else None
        if _ht is not None and region in _ht.index:
            _h = _ht.loc[region]
            _fa = getattr(supply_result, "histosol_fallow", None) or {}
            _crop_area = sum(float(acts.get(c, 0.0) or 0.0) for c in CROPS if c != "GRAS")
            _n2o_t = (_crop_area * float(_h.get("n2o_t_ha_crop", 0.0) or 0.0)
                      + float(acts.get("GRAS", 0.0) or 0.0) * float(_h.get("n2o_t_ha_grass", 0.0) or 0.0))
            for _c in ("crop", "grass"):
                _f = float(_fa.get(_c, 0.0) or 0.0)
                if _f > 0:
                    _n2o_t -= _f * float(_h.get(f"ef_n2o_{_c}", 0.0) or 0.0) * 0.001 * 44.0 / 28.0
            ghg["N2O_HIS"] = max(0.0, _n2o_t) * GWP_N2O      # 1000 ha x t N2O/ha = kt N2O -> kt CO2-eq
        # crop-residue N2O of the added catch crops (CAPRI gases.gms N2OCRO: BioFix x area x EF1)
        if _cn != 0:
            ghg["N2O_CRO"] = ghg.get("N2O_CRO", 0.0) + _cn / 1e3 * EF_SOIL_N2O_DIRECT * 44.0 / 28.0 * GWP_N2O   # t N -> kt
        # CAPRI's technology effects on manure N2O (v_emiLoss in gases.gms; manure_n2o_tech.csv):
        # per animal, housing/storage N2O x (1 - sum_t s_t r_hou_t) / (1 - sum_t s0_t r_hou_t) and
        # application N2O likewise with r_app (low-emission spreading raises it), at the regional
        # model's option shares s against CAPRI's initial shares s0; inhibitors on manure cut
        # application N2O by their share x CAPRI's literature effect (N2OAPP; NMAN left out: REGISTERED)
        _ms = getattr(supply_result, "manure_tech_shares", None) or {}
        _n2o_tech = 0.0
        if _ms and region:
            _eff, _s0 = self._manure_n2o_tech(region)
            _sni = float((getattr(supply_result, "fert_tech_shares", None) or {}).get("NITR_INH_MAN", 0.0) or 0.0)
            _lit = 0.0
            if _sni > 0:
                from capri_mod.supply.supply_module import fert_side_value as _fsv
                _lit = float(_fsv(region, "NITR_INH_MAN", "N2OAPP") or 0.0)
            _dm = 0.0
            for a_ in ANIMALS:
                _mf = self._manure_n2o_factor(region, a_)
                x_ = float(acts.get(a_, 0.0) or 0.0)
                if _mf is None or x_ <= 0:
                    continue
                e_ = _eff.get(a_, {})
                sh = {t: v for (aa, t), v in _ms.items() if aa == a_}
                b_ = _s0.get(a_, {})
                _full = self._manure_n2o_full(region, a_, sh, b_, self._winter_cover_now(region, supply_result))
                if _full is not None:
                    # CAPRI's cascade (HOUSN_, STORN_, APPLN_ with every option's effect on every gas): the N2O
                    # at the shares s against the base shares s0, per stage
                    fh, fa = _full[0], _full[1] * (1.0 - _sni * _lit)
                    kt_n = self._n_excretion(region, a_) * x_ * 1000.0 / 1e6
                    _dm += kt_n * (_mf[0] * (fh - 1.0) + _mf[1] * (fa - 1.0))
                    continue
                h1 = sum(sh.get(t, b_.get(t, 0.0)) * rr[0] for t, rr in e_.items())
                h0 = sum(b_.get(t, 0.0) * rr[0] for t, rr in e_.items())
                p1 = sum(sh.get(t, b_.get(t, 0.0)) * rr[1] for t, rr in e_.items())
                p0 = sum(b_.get(t, 0.0) * rr[1] for t, rr in e_.items())
                fh = (1.0 - h1) / (1.0 - h0) if h0 < 1.0 else 1.0
                fa = ((1.0 - p1) / (1.0 - p0) if p0 < 1.0 else 1.0) * (1.0 - _sni * _lit)
                # CAPRI's loss cascade (HOUSN_, APPLN_): the N2O factors apply to the N LEFT after
                # NH3 losses at the same stage, so NH3 kept by covers, housing or low-emission
                # spreading flows on and raises N2O downstream - JRC121368 Table 18: housing and
                # storage technologies +0.9 Mt CO2eq, application technologies +5.2 Mt
                ch, ca_ = self._manure_n2o_cascade(region, a_, sh, b_)
                fh *= ch
                fa *= ca_
                kt_n = self._n_excretion(region, a_) * x_ * 1000.0 / 1e6
                _dm += kt_n * (_mf[0] * (fh - 1.0) + _mf[1] * (fa - 1.0))
            ghg["N2O_MAN"] = ghg.get("N2O_MAN", 0.0) + _dm * 44.0 / 28.0 * GWP_N2O
            _n2o_tech = _dm * 44.0 / 28.0 * GWP_N2O
            # CAPRI's anaerobic digestion on manure CH4 (supply_model.gms GWPCH4MAN_, MC_GHG_Miti_Factor): per sub-activity
            # 1 - v (1 - QE_AD / QE_NOC), v = s / (L (1 - G)), at the shares s against the base shares
            _dch4 = 0.0
            for a_ in ANIMALS:
                x_ = float(acts.get(a_, 0.0) or 0.0)
                f_ = self._ad_ch4_factor(region, a_, _ms, _s0.get(a_, {}))
                if f_ is None or x_ <= 0:
                    continue
                _dch4 += x_ * 1000.0 * self._ch4_per_head("man", region, a_) / 1e6 * GWP_CH4 * (f_ - 1.0)
            if _dch4:
                ghg["CH4_MAN"] = ghg.get("CH4_MAN", 0.0) + _dch4
        # CAPRI's emission side effects of nitrification inhibitors on mineral N
        # (p_litRevFertTechs, envind/ghgMiti.gms l. 552-555): per kg of N under the option the
        # emission factor is (1 - lit) x (1 + NMIN) times NOC's, NMIN being the option's N saving,
        # already in the mineral input. Weight: the option's share of mineral N (area share s,
        # N per ha lowered by 1 + NMIN). Direct soil N2O takes the N2O factor; the volatilisation
        # path of indirect N2O and mineral NH3 take the NH3 factor.
        f_side = self.fert_side_factors(region, getattr(supply_result, "fert_tech_shares", None),
                                        getattr(supply_result, "fert_nmin", None))
        if f_side and "N2O_SOIL" in ghg:
            _dir = _dn[0] / (_dn[0] + _dn[1]) if (_dn[0] + _dn[1]) > 0 else 1.0
            _old = ghg["N2O_SOIL"]
            ghg["N2O_SOIL"] = _old * (_dir * f_side["N2OSYN"] + (1.0 - _dir) * f_side["NH3SYN"])
        # CAPRI's leaching of the soil surplus (LEACHN_) and the indirect N2O of leached and run-off N allocated to
        # crops (gases.gms N2OLEA; capri_mod/supply/n_leaching.py)
        _lea = self.leaching(region, acts, nb, supply_result)
        if _lea is not None:
            ghg["N2O_LEA"] = _lea["n2o_n"] / 1000.0 * 44.0 / 28.0 * GWP_N2O       # t N2O-N -> kt CO2-eq
            self._leaching_last = _lea
        # total after every adjustment of soil N2O (it was summed before the mineral-input
        # rescaling above, so GHG total missed the substitution and yield effects on soil N2O)
        ghg_total = sum(ghg.values())

        # Biodiversity
        bio = self.compute_biodiversity_indicators(acts, land)

        # Ammonia
        nh3 = self.compute_ammonia(_acts_k if _acts_k is not None else acts, region,
                                   mineral_n_kt=float(nb.get("n_mineral_input", 0.0)) / 1000.0)
        if f_side and nh3.get("nh3_soils"):
            nh3 = dict(nh3)
            _d = float(nh3["nh3_soils"]) * (f_side["NH3SYN"] - 1.0)
            nh3["nh3_soils"] = float(nh3["nh3_soils"]) + _d
            nh3["nh3_total"] = float(nh3["nh3_total"]) + _d
        # CAPRI's inhibitors on applied manure raise application NH3 (p_litRevFertTechs NH3APP,
        # supply model's _apply_manure_inhibitor): t NH3-N per activity unit -> kt NH3
        _ni = getattr(supply_result, "manure_ni_nh3", None) or {}
        if _ni:
            _lv3 = getattr(supply_result, "activities", None)
            if _lv3 is None:
                _lv3 = {}
            _d = sum(float(v) * float(_lv3.get(a, 0.0)) for a, v in _ni.items()) / 1000.0 * 17.0 / 14.0
            if _d:
                nh3 = dict(nh3)
                nh3["nh3_livestock"] = float(nh3["nh3_livestock"]) + _d
                nh3["nh3_total"] = float(nh3["nh3_total"]) + _d
        # CAPRI's ammonia technologies: N kept from volatilising (t N) -> kt NH3
        _sv = float(getattr(self, "_nh3_saved_last", 0.0) or 0.0) - float(getattr(self, "_nitrate_nh3_extra", 0.0) or 0.0)
        if _sv != 0:
            _d = _sv / 1000.0 * 17.0 / 14.0
            nh3 = dict(nh3)
            nh3["nh3_livestock"] = max(0.0, float(nh3["nh3_livestock"]) - _d)
            nh3["nh3_total"] = max(0.0, float(nh3["nh3_total"]) - _d)
        # indirect N2O from volatilised manure NH3 (CAPRI N2OAMM: NH3-N x EF4), after every NH3
        # adjustment; the GHG total is summed again with it
        if nh3.get("nh3_livestock"):
            ghg["N2O_IND"] = float(nh3["nh3_livestock"]) * 14.0 / 17.0 * EF_SOIL_N2O_INDIRECT * 44.0 / 28.0 * GWP_N2O
            ghg_total = sum(ghg.values())

        # Land use, CAPRI's aggregates (sets.gms landUse_TO_landUseAgg): arable crops ARAC (paddy, fallow and set-aside,
        # every other arable crop including fodder on arable land, silage maize, tobacco and textile crops), permanent
        # crops FRUN (fruit, olives, nurseries, vineyards), grassland GRAS. Before October 2026 tobacco and the textile
        # crops counted as permanent crops, silage maize and other fodder as grassland, nurseries nowhere.
        # CAPRI's gross phosphate balance (P2O5); a failure leaves the P items empty, not the region
        try:
            pb = self.compute_phosphorus_balance(acts, yields, region, supply_result)
        except Exception as _exc:
            import warnings as _w
            _w.warn(f"phosphate balance failed for {region}: {_exc!r}")
            from capri_mod.environmental.p_balance import ITEMS as _PIT
            pb = {k: float("nan") for k in _PIT}
        _oc = getattr(supply_result, "organic_conv", None) or {}
        organic = sum(float(acts.get(c, 0.0) or 0.0) * (1.0 - float(v)) for c, v in _oc.items() if c in CROPS)

        PERM = ("WINE", "OLIV", "TABO", "APPL", "OFRU", "CITR", "TAGR", "NURS")
        perm   = sum(acts.get(c, 0.0) for c in PERM)
        grass  = acts.get("GRAS", 0.0)
        arable = sum(acts.get(c, 0.0) for c in CROPS if c not in PERM + ("GRAS",))

        return EnvironmentalIndicators(
            region=region,
            # GHG
            ghg_enteric=ghg["CH4_ENT"],
            ghg_manure_ch4=ghg["CH4_MAN"],
            ghg_manure_n2o=ghg["N2O_MAN"],
            ghg_soil_n2o=ghg["N2O_SOIL"],
            ghg_histosol_n2o=float(ghg.get("N2O_HIS", 0.0)),
            ghg_manure_n2o_tech=float(_n2o_tech),
            ghg_residue_n2o=float(ghg.get("N2O_CRO", 0.0)),
            ghg_indirect_n2o=float(ghg.get("N2O_IND", 0.0)),
            ghg_leaching_n2o=float(ghg.get("N2O_LEA", 0.0)),
            leach_share=float(_lea["share"]) if _lea is not None else 0.0,
            n_runoff_leached=float(_lea["n_runoff_leached"]) if _lea is not None else 0.0,
            ghg_liming=ghg["CO2_LIME"],
            ghg_urea=float(ghg.get("CO2_UREA", 0.0)),
            ghg_total=ghg_total,
            ghg_non_co2=ghg_total - float(ghg.get("CO2_LIME", 0.0)) - float(ghg.get("CO2_UREA", 0.0)),
            ghg_ggwp=ghg_total - float(ghg.get("CO2_UREA", 0.0)),
            # Nitrogen
            n_mineral_input=nb["n_mineral_input"],
            n_organic_input=nb["n_organic_input"],
            n_fixation=nb["n_fixation"],
            n_deposition=nb["n_deposition"],
            n_crop_uptake=nb["n_crop_uptake"],
            n_animal_products=nb["n_animal_products"],
            n_surplus=nb["n_surplus"],
            n_use_efficiency=nb["n_use_efficiency"],
            # Phosphate (t P2O5)
            p_input=pb["IMPORT"],
            p_uptake=pb["EXPPRD"],
            p_surplus=pb["SURTOT"],
            p_mineral_input=pb["MINFER"],
            p_manure_excretion=pb["EXCRET"],
            p_manure_net_export=pb["MTRADE"],
            p_crop_residues=pb["CRESID"],
            p_runoff=pb["RUNANI"],
            p_surplus_soil=pb["SURSOI"],
            # Ammonia
            nh3_livestock=nh3["nh3_livestock"],
            nh3_soils=nh3["nh3_soils"],
            nh3_total=nh3["nh3_total"],
            # Land
            uaa_total=arable + perm + grass,
            arable_land=arable,
            permanent_crops=perm,
            grassland=grass,
            organic_area=organic,
            # Biodiversity
            shannon_crop_diversity=bio["shannon_crop_diversity"],
        )

    def run_all_regions(
        self,
        supply_results: Dict,  # {region: SupplyResult}
        verbose: bool = False,
    ) -> pd.DataFrame:
        """
        Compute environmental indicators for all regions.
        Returns DataFrame with one row per region.
        """
        rows = []
        fd = []
        for i, (region, result) in enumerate(supply_results.items()):
            if verbose and i % 50 == 0:
                print(f"  Environmental module: region {i+1}/{len(supply_results)}")
            try:
                self._fert_dist_now = None
                ind = self.compute_indicators(result)
                rows.append(ind.to_series())
                fd.extend(self._fert_dist_now or [])
            except Exception as _e:
                import warnings as _w
                _w.warn(f"environmental indicators failed for {region}: {_e!r} - region left out of the table")
                if verbose:
                    print(f"    Warning: {region} environmental calc failed: {_e}")

        # CAPRI's inner fertiliser distribution per region and crop group (CAPRIModel.run: results["fert_dist"])
        self.last_fert_dist = pd.DataFrame(fd)
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows).set_index("region")
        return df


# refactor stage 4a: the blocks' methods see this module's names (capri_mod/environmental/blocks/__init__.py)
from capri_mod.environmental import blocks as _blocks  # noqa: E402
_blocks.inject(globals())
