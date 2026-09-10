"""Technological GHG abatement layer — EcAMPA measures as explicit inputs.

This layer is deliberately distinct from the model-derived *economic* MAC curve
in ``abatement_module.py``. Here, EcAMPA 2 (JRC, 2016) measure data — each
mitigation technology's emission-reduction potential and cost — is used as
**explicit, cited input**. That is the legitimate use of the report's numbers:
as parameters of a technology-adoption module, clearly labelled, not as a
validation of the economic model.

The two layers answer different questions and are additive:
  - economic MACC (abatement_module):  abatement from changing the production mix
  - technological layer (this file):   abatement from adopting measures at fixed
                                        production (nitrification inhibitors, feed
                                        additives, anaerobic digestion, ...)

EcAMPA found that a ~20% EU-28 agricultural mitigation target is met by a
combination of the two. Modelling both lets CAPRI-mod approach EcAMPA's total,
with each component transparent and separately sourced.

Provenance: every measure's potential and cost is page-cited to EcAMPA 2 in
``capri_data/<base_year>/abatement/ecampa_measures.csv``. Nothing here is
invented; where EcAMPA gives a range or an entangled effect, the CSV notes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class MeasureResult:
    """Abatement and cost from one technological measure."""

    measure: str
    gas: str
    abatement: float          # t CO2-eq abated
    cost: float               # EUR total (potential x cost x uptake)
    cost_per_tonne: float     # EUR / t CO2-eq
    source_page: int


@dataclass
class TechnicalAbatementResult:
    """Result of applying the technological measure set."""

    measures: List[MeasureResult]
    total_abatement: float
    baseline_emissions: float
    abatement_pct: float
    notes: Dict = field(default_factory=dict)

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [(m.measure, m.gas, m.abatement, m.cost, m.cost_per_tonne,
              m.source_page) for m in self.measures],
            columns=["measure", "gas", "abatement_tCO2e", "cost_eur",
                     "cost_per_tonne", "ecampa_page"],
        )


class TechnologicalAbatement:
    """Apply EcAMPA technological measures to computed emissions.

    Parameters
    ----------
    measures : DataFrame
        The EcAMPA measure table (ecampa_measures.csv).
    """

    def __init__(self, measures: pd.DataFrame):
        self.measures = measures

    @classmethod
    def from_data_dir(cls, data_dir, base_year: str = "2017"):
        path = (Path(data_dir) / base_year / "abatement" /
                "ecampa_measures.csv")
        if not path.exists():
            raise FileNotFoundError(
                f"EcAMPA measure file not found at {path}. This layer requires "
                f"the cited EcAMPA data; it does not fabricate measure values."
            )
        return cls(pd.read_csv(path))

    def apply(self,
              emissions_by_source: Dict[str, float],
              uptake_scale: float = 1.0,
              measures_enabled: Optional[List[str]] = None,
              enteric_by_animal: Optional[Dict[str, float]] = None
              ) -> TechnicalAbatementResult:
        """Apply the measures to a *source-resolved* emissions inventory.

        Parameters
        ----------
        emissions_by_source : dict
            Emissions in CO2-eq by source, using the environmental module's own
            source keys: ``CH4_ENT`` (enteric fermentation), ``CH4_MAN`` (manure
            CH4), ``N2O_MAN`` (manure N2O), ``N2O_SOIL`` (soil N2O), ``CO2_LIME``,
            ``CO2_UREA``.
        uptake_scale : float
            Fraction of each measure's maximum uptake actually adopted (0..1).
        measures_enabled : list of str, optional
            Restrict to a subset of measures by name; default is all.
        enteric_by_animal : dict, optional
            Enteric CH4 (CO2-eq) per animal, from
            :meth:`EnvironmentalModule.enteric_ch4_by_animal`. When supplied,
            feed measures are applied *per animal* to only the animals each
            targets (its ``applies_to_animals`` set) — e.g. a nitrate additive
            hits dairy + fattening cattle only, not sheep or the whole enteric
            pool. When absent, feed measures fall back to the whole ``CH4_ENT``
            pool (coarser, a slight overestimate for mixed-livestock regions).

        Reductions on the *same source* (or *same animal*, for enteric) are
        applied multiplicatively, so stacked measures never abate more than 100%
        of that pool.
        """
        baseline = sum(emissions_by_source.values())
        remaining = dict(emissions_by_source)
        # per-animal enteric pool, when provided, lets feed measures target
        # specific animals; its total replaces the CH4_ENT scalar for accounting.
        animal_pool = dict(enteric_by_animal) if enteric_by_animal else None
        if animal_pool is not None:
            # keep the source total consistent with the per-animal detail
            remaining["CH4_ENT"] = sum(animal_pool.values())
            baseline = sum(remaining.values())
        results = []

        rows = self.measures
        if measures_enabled is not None:
            rows = rows[rows["measure"].isin(measures_enabled)]

        _FERT_N_MEASURES = {"precision_farming_low", "precision_farming_mid",
                            "precision_farming_high", "variable_rate_technology"}
        fert = rows[rows["measure"].isin(_FERT_N_MEASURES)]
        if len(fert) > 1:
            keep = fert.loc[fert["reduction_pct"].astype(float).idxmax(), "measure"]
            drop = _FERT_N_MEASURES - {keep}
            rows = rows[~rows["measure"].isin(drop)]
            self._exclusive_note = (
                f"kept {keep} as the representative fertiliser-N measure; "
                f"excluded {sorted(drop)} as non-additive alternatives")
        else:
            self._exclusive_note = None

        for _, m in rows.iterrows():
            source = m.get("emission_source")
            if not isinstance(source, str) or source not in remaining:
                continue
            red_raw = m.get("reduction_pct", np.nan)
            if pd.isna(red_raw):
                continue
            red_pct = float(red_raw)
            if red_pct <= 0:
                continue
            max_uptake = float(m.get("max_uptake_pct", 100) or 100) / 100.0
            effective = (red_pct / 100.0) * max_uptake * uptake_scale
            effective = min(effective, 1.0)

            # Activity-resolved enteric abatement: a feed measure with an
            # applies_to_animals set, and a per-animal pool available, abates
            # only its target animals — never the whole enteric pool.
            targets = self._animal_targets(m)
            if (source == "CH4_ENT" and animal_pool is not None
                    and targets is not None):
                abated = 0.0
                for animal in targets:
                    if animal in animal_pool:
                        cut = animal_pool[animal] * effective
                        animal_pool[animal] -= cut
                        abated += cut
                remaining["CH4_ENT"] = sum(animal_pool.values())
            else:
                pool_before = remaining[source]
                abated = pool_before * effective
                remaining[source] = pool_before - abated

            raw_cost = m.get("cost_eur", np.nan)
            cost_per_tonne = (float(raw_cost) if pd.notna(raw_cost) and
                              str(m.get("cost_unit", "")).startswith("per_tonne")
                              else np.nan)
            results.append(MeasureResult(
                measure=m["measure"], gas=m["gas"],
                abatement=float(abated),
                cost=float(raw_cost) if pd.notna(raw_cost) else np.nan,
                cost_per_tonne=cost_per_tonne,
                source_page=int(m.get("source_page", 0) or 0),
            ))

        total_ab = baseline - sum(remaining.values())
        return TechnicalAbatementResult(
            measures=results,
            total_abatement=float(total_ab),
            baseline_emissions=float(baseline),
            abatement_pct=float(100.0 * total_ab / baseline) if baseline else 0.0,
            notes={
                "uptake_scale": uptake_scale,
                "n_measures_applied": len(results),
                "resolution": (
                    "per emission source; enteric CH4 further resolved per animal"
                    if animal_pool is not None else
                    "per emission source (enteric CH4 at pool level — pass "
                    "enteric_by_animal for per-animal resolution)"),
                "provenance": "EcAMPA 2 (JRC 2016), page-cited in "
                              "ecampa_measures.csv",
                "scope": "technological measures at fixed production; combine "
                         "with the economic MACC for a total comparable to "
                         "EcAMPA's headline mitigation.",
            },
        )

    @staticmethod
    def _animal_targets(measure_row) -> Optional[set]:
        """Parse the animals a measure applies to from ``applies_to_animals``.

        Returns a set of animal codes, or None if the measure is not
        animal-targeted (so it falls back to source-pool application).
        """
        raw = measure_row.get("applies_to_animals")
        if not isinstance(raw, str) or not raw.strip():
            return None
        return {a.strip() for a in raw.split("|") if a.strip()}
