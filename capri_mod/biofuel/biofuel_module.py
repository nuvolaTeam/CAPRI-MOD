"""
Biofuel module for CAPRI-Python.

Follows CAPRI's biofuel structure (global/biofuel_markets.gms):
  - Two biofuels: BIOE (bioethanol) and BIOD (biodiesel)
  - Bioethanol feedstocks: wheat, maize, sugar beet   -> ethanol
  - Biodiesel feedstocks:   rapeseed, sunflower, soya oil -> biodiesel (FAME)
  - Biofuel demand is driven by a blending mandate: a target share of
    transport fuel (gasoline for ethanol, diesel for biodiesel) that must be
    met from biofuel. That target creates a derived demand for feedstocks,
    which feeds back into the crop market as additional (industrial) demand.

Conversion coefficients are standard agronomic constants (tonnes of biofuel
per tonne of feedstock), consistent with CAPRI/AGLINK ranges. They are not
model-fitted; they are physical process yields.

This module computes, for a given set of feedstock crop prices and a mandate
level, the biofuel production and the induced feedstock demand (1000 t), which
the market module can add to domestic use.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional
import pandas as pd


# --- Feedstock -> biofuel conversion (tonnes biofuel per tonne feedstock) ---
# Bioethanol (ethanol yield per tonne of dry feedstock):
#   wheat  ~0.38 t ethanol / t grain, maize ~0.40, sugar beet ~0.10 (high water)
# Biodiesel (FAME yield per tonne of oil; oilseeds first crushed to oil):
#   vegetable oil -> biodiesel ~0.98 (near 1:1 by mass via transesterification)
ETHANOL_YIELD = {   # t ethanol per t feedstock
    "SWHE": 0.38,
    "CORN": 0.40,
    "BARL": 0.34,
    "SUGR": 0.62,   # per tonne of sugar (not beet)
}
BIODIESEL_OIL_YIELD = {  # t biodiesel per t vegetable oil
    "RAPO": 0.98,   # rapeseed oil
    "SUNO": 0.98,   # sunflower oil
    "SOYA_OIL": 0.98,
}
# Oil extraction from oilseed (t oil per t seed) — matches processing splits
SEED_TO_OIL = {
    "RAPE": 0.40,
    "SUNF": 0.42,
    "SOYA": 0.18,
}

# Energy content to convert fuel volumes: biofuel share is by energy.
# Ethanol ~21.1 MJ/l, gasoline ~32.2 MJ/l; biodiesel ~33 MJ/l, diesel ~35.8 MJ/l.
ETHANOL_ENERGY_RATIO = 21.1 / 32.2   # ethanol vs gasoline per unit volume
BIODIESEL_ENERGY_RATIO = 33.0 / 35.8


@dataclass
class BiofuelResult:
    bioethanol_kt: float = 0.0
    biodiesel_kt: float = 0.0
    feedstock_demand: Dict[str, float] = field(default_factory=dict)  # 1000 t
    mandate_share: float = 0.0


class BiofuelModule:
    """
    Compute biofuel production and induced feedstock demand for the EU under a
    blending mandate.
    """

    def __init__(self, data: Optional[dict] = None,
                 mandate_share: float = 0.065):
        """
        mandate_share: physical energy share of transport fuel met by biofuel.
        The EU RED target is ~10% (2020) / ~14% (RED II), but actual physical
        blend penetration in the base period was ~6-7%. The default 0.065 is
        calibrated so EU biofuel output matches observed levels (~5 Mt ethanol,
        ~13 Mt biodiesel, 2020). Raise it to simulate a stronger mandate.
        """
        self.data = data or {}
        self.mandate_share = mandate_share
        # EU transport fuel demand (1000 t oil-equivalent), order-of-magnitude
        # baseline; can be overridden from data if available.
        self.eu_gasoline_kt = self.data.get("eu_gasoline_kt", 55_000.0)
        self.eu_diesel_kt = self.data.get("eu_diesel_kt", 180_000.0)

    def run(self,
            feedstock_shares: Optional[Dict[str, float]] = None,
            mandate_share: Optional[float] = None) -> BiofuelResult:
        """
        feedstock_shares: how the ethanol / biodiesel mandate is split across
            eligible feedstocks (defaults to an even split of the ethanol
            mandate across wheat/maize/sugar and the biodiesel mandate across
            rape/sun/soya oil). Values need not sum to 1 within a group; they
            are normalised.
        """
        m = self.mandate_share if mandate_share is None else mandate_share

        # --- Ethanol required (energy share of gasoline, converted to volume/mass)
        ethanol_energy_target = self.eu_gasoline_kt * m
        ethanol_kt = ethanol_energy_target / ETHANOL_ENERGY_RATIO

        # --- Biodiesel required (energy share of diesel)
        biodiesel_energy_target = self.eu_diesel_kt * m
        biodiesel_kt = biodiesel_energy_target / BIODIESEL_ENERGY_RATIO

        # --- Split across feedstocks
        eth_feeds = feedstock_shares.get("ethanol") if feedstock_shares else None
        bd_feeds = feedstock_shares.get("biodiesel") if feedstock_shares else None
        if not eth_feeds:
            eth_feeds = {"SWHE": 0.45, "CORN": 0.40, "SUGR": 0.15}
        if not bd_feeds:
            # EU biodiesel is rapeseed-dominated; sunflower and soya are minor.
            bd_feeds = {"RAPE": 0.75, "SUNF": 0.15, "SOYA": 0.10}

        feedstock_demand: Dict[str, float] = {}

        # Ethanol feedstock demand: ethanol_kt * share / ethanol_yield
        eth_tot = sum(eth_feeds.values()) or 1.0
        for crop, sh in eth_feeds.items():
            y = ETHANOL_YIELD.get(crop, 0.38)
            eth_from_crop = ethanol_kt * (sh / eth_tot)
            feedstock_demand[crop] = feedstock_demand.get(crop, 0.0) + eth_from_crop / y

        # Biodiesel feedstock demand: needs oil, which needs seed
        bd_tot = sum(bd_feeds.values()) or 1.0
        oil_map = {"RAPE": "RAPO", "SUNF": "SUNO", "SOYA": "SOYA_OIL"}
        for seed, sh in bd_feeds.items():
            oil_key = oil_map.get(seed, "RAPO")
            oil_yield = BIODIESEL_OIL_YIELD.get(oil_key, 0.98)
            seed_oil = SEED_TO_OIL.get(seed, 0.40)
            bd_from_seed = biodiesel_kt * (sh / bd_tot)
            oil_needed = bd_from_seed / oil_yield
            seed_needed = oil_needed / seed_oil
            feedstock_demand[seed] = feedstock_demand.get(seed, 0.0) + seed_needed

        return BiofuelResult(
            bioethanol_kt=round(ethanol_kt, 1),
            biodiesel_kt=round(biodiesel_kt, 1),
            feedstock_demand={k: round(v, 1) for k, v in feedstock_demand.items()},
            mandate_share=m,
        )

    def induced_demand_series(self, commodities, **kwargs) -> pd.Series:
        """Return feedstock demand as a Series aligned to `commodities` (1000 t)."""
        res = self.run(**kwargs)
        s = pd.Series(0.0, index=commodities)
        for k, v in res.feedstock_demand.items():
            if k in s.index:
                s[k] = v
        return s
