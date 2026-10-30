"""Ammonia of the environmental accounts (CAPRI's NH3 factors and the ammonia technologies).

EnvironmentalModule's methods, moved unchanged from capri_mod/environmental/environmental_module.py (refactor stage 4a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are environmental_module's, given to this
module once environmental_module is loaded (capri_mod.environmental.blocks.inject); the annotations are not evaluated.
"""
from __future__ import annotations


class AmmoniaBlock:
    def _nh3_factors(self) -> dict:
        d = self.__dict__.get("_nh3_fac_cache")
        if d is None:
            d = _inputs.current().json("nh3_factors_capri.json", "environment")["regions"]
            self._nh3_fac_cache = d
        return d

    def compute_ammonia(
        self,
        activities: pd.Series,
        region: Optional[str] = None,
        mineral_n_kt: Optional[float] = None,
    ) -> Dict[str, float]:
        """Ammonia emissions (kt NH3) from livestock manure and mineral fertiliser.

        ``region`` selects the regional N excretion. It used to be missing from
        the signature while the body referenced it, so every call raised a
        NameError; run_all_regions swallowed the error per region and returned
        an EMPTY environmental table from every model run, silently.
        """
        # CAPRI's AMMONIA ACCOUNTING (replaces the housing-only factors and the
        # "soils = 10% of livestock" proxy): per region, CAPRI's share of each
        # animal's excreted N lost as NH3-N (housing + storage + application +
        # grazing, GNH3/MANN) and the share of mineral N lost (NH3MIN/MINFER),
        # from its 2030 reference run (tools/build/build_nh3_factors.py). Responds to
        # herds AND to mineral fertiliser - which the proxy could not see.
        fac = self._nh3_factors().get(region) if region else None
        if fac:
            man_n = sum(float(fac["manure_share"].get(a, 0.0))
                        * self._n_excretion(region, a) * activities.get(a, 0.0) * 1000 / 1e6
                        for a in ANIMALS)                                   # kt NH3-N
            min_n = float(fac.get("mineral_share") or 0.0) * float(mineral_n_kt or 0.0)
            return {"nh3_livestock": man_n * 17 / 14, "nh3_soils": min_n * 17 / 14,
                    "nh3_total": (man_n + min_n) * 17 / 14}
        # no CAPRI factors: only where there is no farming (Brussels); anything else fails loudly
        if any(activities.get(a, 0.0) > 0 for a in ANIMALS) or float(mineral_n_kt or 0.0) > 0:
            raise RuntimeError(f"no CAPRI ammonia factors for {region} (tools/build/build_nh3_factors.py)")
        return {"nh3_livestock": 0.0, "nh3_soils": 0.0, "nh3_total": 0.0}
