"""Biodiversity indicators of the environmental accounts.

EnvironmentalModule's methods, moved unchanged from capri_mod/environmental/environmental_module.py (refactor stage 4a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are environmental_module's, given to this
module once environmental_module is loaded (capri_mod.environmental.blocks.inject); the annotations are not evaluated.
"""
from __future__ import annotations


class BiodiversityBlock:
    def compute_biodiversity_indicators(
        self,
        activities: pd.Series,
        land: pd.Series,
    ) -> Dict[str, float]:
        """
        Shannon crop diversity index.

        (Until 29 October 2026 also an HNV farmland proxy: permanent grassland plus 0.5 x the area of pulses, soya and
        grass, a hand-set weight with grass counted twice; removed, no CAPRI source: KNOWN_ISSUES K96.)

        Shannon H' = -Σ p_i × ln(p_i)
        where p_i = share of crop i in total arable area.

        """
        # Shannon diversity
        crop_areas = activities.reindex(CROPS).fillna(0.0)
        total_crop = crop_areas.sum()
        if total_crop > 0:
            shares = crop_areas / total_crop
            shares = shares[shares > 0]
            shannon = -float((shares * np.log(shares)).sum())
        else:
            shannon = 0.0

        return {
            "shannon_crop_diversity": shannon,
        }
