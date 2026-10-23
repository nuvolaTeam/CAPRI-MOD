"""CAPRI's crop nutrient balance for N, P and K, the data of the fertilisation block of the regional supply model in
CAPRI's form (supply/supply_model.gms NUTNED_, fertDistMine_, fertDistExcr_, fertDistCres_ and the inner fertiliser
distribution model; capri_mod/supply/capri_regional_nlp.py).

Data (tools/build/build_npk_balance_2030.py, from CAPRI's 2030 reference results):
  npk_crop_coefs_2030.csv        per CAPRI region, model crop and nutrient: need, contribution to the arable residue
                                 pool, permanent crops' own residues, CAPRI's mineral flow (kg/ha)
  npk_region_2030.csv            per CAPRI region and nutrient: mineral efficiency, manure and residue availability,
                                 CAPRI's unit value (EUR/t)
  fert_dist_priors_npk_2030.csv  the inner model's priors per crop group, source and nutrient (posterior mode per ha)
  livestock_manure_p_coef.csv, livestock_manure_k_coef.csv   manure P2O5 / K2O per model head (kg)
Crop groups of the model crops: fert_dist_crop_groups_2030.csv (CAPRI's 2030 areas).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

NUTRIENTS = ("N", "P", "K")
SOURCES = ("MINE", "EXCR", "CRES")
PERM_NGRP = frozenset({"GRAS", "PERM"})

#: CAPRI's slope of manure N availability on manure N applied per ha of land (fert/endoManAvail.gms), 0 for P and K
ENDO_MAN_AV_SLOPE = {"N": -0.0015, "P": 0.0, "K": 0.0}


def endo_slope(g0: float, m0: float, nut: str) -> float:
    """CAPRI's slope of the endogenous availability (fert/endoManAvail.gms) with its two corrections: availability at
    most max(0.999, g0) at zero application, at least min(0.2, g0) at max(300, m0) kg/ha."""
    b = ENDO_MAN_AV_SLOPE.get(nut, 0.0)
    if b == 0.0 or not (m0 > 0):
        return 0.0
    if g0 - m0 * b > max(0.999, g0):
        b = (g0 - max(0.999, g0)) / m0
    top = max(300.0, m0) - m0
    if top > 0 and g0 + top * b < min(0.2, g0):
        b = (min(0.2, g0) - g0) / top
    return b


class NPKData:
    _inst = None

    def __init__(self, data_dir: Optional[str] = None):
        root = Path(data_dir) if data_dir else Path(__file__).resolve().parents[2] / "capri_data"
        env = root / "2017" / "environment"
        c = pd.read_csv(env / "npk_crop_coefs_2030.csv")
        self.crop = {(r, n): d.set_index("model_crop") for (r, n), d in c.groupby(["capri_region", "nutrient"])}
        g = pd.read_csv(env / "npk_region_2030.csv")
        self.reg = {(t.capri_region, t.nutrient): t for t in g.itertuples(index=False)}
        p = pd.read_csv(env / "fert_dist_priors_npk_2030.csv")
        self.pri = {(r, n): d.set_index("ngrp") for (r, n), d in p.groupby(["capri_region", "nutrient"])}
        self.man = {}
        for nut, f in (("P", "livestock_manure_p_coef.csv"), ("K", "livestock_manure_k_coef.csv")):
            if (env / f).exists():
                self.man[nut] = pd.read_csv(env / f, index_col=0)
        gr = pd.read_csv(env / "fert_dist_crop_groups_2030.csv")
        self.groups = {r: d for r, d in gr.groupby("capri_region")}
        w = gr.groupby(["model_crop", "ngrp"]).share.sum()
        tot = w.groupby(level=0).transform("sum")
        self.eu_shares = {}
        for (mc, ng), v in (w / tot).items():
            self.eu_shares.setdefault(mc, {})[ng] = float(v)

    @classmethod
    def get(cls) -> "NPKData":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def crop_shares(self, capri_region: str) -> Dict[str, Dict[str, float]]:
        out = {mc: dict(v) for mc, v in self.eu_shares.items()}
        d = self.groups.get(capri_region)
        if d is not None:
            own = {}
            for t in d.itertuples(index=False):
                own.setdefault(t.model_crop, {})[t.ngrp] = float(t.share)
            out.update(own)
        return out

    def crop_coef(self, capri_region: str, nut: str, crop: str, col: str) -> float:
        """A model crop's coefficient (kg/ha); a crop CAPRI does not grow in the region takes the country's, else 0."""
        for r in (capri_region, capri_region[:2] + "000000"):
            d = self.crop.get((r, nut))
            if d is not None and crop in d.index:
                v = float(d.at[crop, col])
                if v == v:
                    return v
        return 0.0

    def region(self, capri_region: str, nut: str):
        t = self.reg.get((capri_region, nut))
        if t is None:
            t = self.reg.get((capri_region[:2] + "000000", nut))
        return t

    def priors(self, capri_region: str, nut: str):
        d = self.pri.get((capri_region, nut))
        if d is None:
            d = self.pri.get((capri_region[:2] + "000000", nut))
        return d

    def manure_per_head(self, region: str, nut: str, animal: str) -> float:
        t = self.man.get(nut)
        if t is None or region not in t.index or animal not in t.columns:
            return 0.0
        v = t.at[region, animal]
        return float(v) if pd.notna(v) and v > 0 else 0.0
