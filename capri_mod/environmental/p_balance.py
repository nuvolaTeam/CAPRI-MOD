"""CAPRI's gross phosphate balance (reports/calc_nbalance.gms with FNUT = PHOF), in P2O5 as CAPRI reports it.

Items (CAPRI's names; calc_nbalance.gms line numbers):
  EXCRET  manure P2O5 excreted, sum over animals of level x MANP                                   (l. 144-146)
  MTRADE  manure P2O5 net exports (exports - imports)                                               (l. 175, ManureTradeNEW)
  MINFER  mineral P2O5 bought, NETF = -v_netPutQuant(PHOF)                                          (l. 115)
  CRESID  P2O5 in crop residues, sum over crops of level x the crop's residue output (MANP of a crop)  (l. 197-207)
  EXPPRD  P2O5 removed with crop products, sum over crops of level x retention (PRET)          (l. 45-59)
  RUNANI  manure P2O5 run off, sum over animals of level x MANP x the N runoff share RunTot      (l. 71, 103-106)
  IMPORT  = EXCRET - MTRADE + MINFER + CRESID                                                       (l. 237-243)
  SURTOT  = IMPORT - EXPPRD          (the gross balance; CAPRI's surplus to soil or water)          (l. 305-313)
  SURSOI  = SURTOT - RUNANI          (P has no gaseous losses)                                      (l. 247-262)
CAPRI reports them in 1000 t P2O5 and per ha of UAAR; the environmental accounts keep t P2O5 (1000 ha x kg/ha, as the
N items). P2O5 is CAPRI's unit for phosphate throughout (PHOF, MANP, PRET, PCRD); P = P2O5 x 0.4364.

Data: capri_data/2017/environment/p_balance_crop_coefs_2030.csv (retention and residue output per ha of the model's
crops, tools/build/build_p_balance.py); manure P2O5 per head and CAPRI's crop nutrient balance for P (NPKData,
capri_mod/fert/npk.py, the data of the regional model's fertilisation block).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pandas as pd

ITEMS = ("EXCRET", "MTRADE", "MINFER", "CRESID", "EXPPRD", "RUNANI", "IMPORT", "SURTOT", "SURSOI")


def balance(excret: float, mtrade: float, minfer: float, cresid: float, expprd: float, runani: float) -> Dict[str, float]:
    """CAPRI's P balance from its items (calc_nbalance.gms with FNUT = PHOF; units as given)."""
    imp = excret - mtrade + minfer + cresid
    surtot = imp - expprd
    return {"EXCRET": excret, "MTRADE": mtrade, "MINFER": minfer, "CRESID": cresid, "EXPPRD": expprd,
            "RUNANI": runani, "IMPORT": imp, "SURTOT": surtot, "SURSOI": surtot - runani}


class PCropCoefs:
    """CAPRI's P2O5 retention (pret) and residue output (pcrd) per ha of the model's crops, per CAPRI region."""
    _inst = None

    def __init__(self, data_dir: Optional[str] = None):
        root = Path(data_dir) if data_dir else Path(__file__).resolve().parents[2] / "capri_data"
        t = pd.read_csv(root / "2017" / "environment" / "p_balance_crop_coefs_2030.csv")
        self.c = {(r.capri_region, r.model_crop): (float(r.pret_kg_ha), float(r.pcrd_kg_ha))
                  for r in t.itertuples(index=False)}

    @classmethod
    def get(cls) -> "PCropCoefs":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def coef(self, capri_region: str, crop: str):
        """(retention, residue output) kg P2O5/ha; a crop CAPRI does not grow in the region takes the country's
        (as NPKData.crop_coef), else (0, 0)."""
        for r in (capri_region, capri_region[:2] + "000000"):
            v = self.c.get((r, crop))
            if v is not None:
                return v
        return 0.0, 0.0


def nutned_mineral(D, capri_region: str, need, own, own_perm, pool, mine0, xb, x, sq, E0: float, E: float,
                   grass=None) -> Optional[float]:
    """Mineral P2O5 bought (t) from CAPRI's NUTNED_ for P summed over the crop groups, the equation of the regional
    model's fertilisation block (capri_regional_nlp._fert_block, data SupplyModel._npk_spec):

        kappa x (sum_c need_c sq_c x_c - gc x sum_c own_perm_c x_c) = eff x MINE + g0 x E + gc x C

    with the arable residue pool C = sum_c pool_c x_c, the permanent groups' own residues own_perm_c (own_c x the crop's
    share in a permanent group), manure applied E, sq_c = CAPRI's need factor of the yield
    (capri_mod.fert.npk.need_yield_factor), and kappa the need factor that closes the equation at the base levels xb with CAPRI's mineral flows mine0, as the block computes it:
    kappa x (need0 - gc x own0) = eff x M0 + g0 x E0 + gc x C0 (CAPRI's v_cropNutNeedMultFact, calibrated at the
    base and fixed in simulation).
    Arguments are dicts by model crop (kg/ha, 1000 ha) and t; grass = (z, dn, sq) adds the grassland split column
    (z x need difference GRAE - GRAI). Used where the regional model has no fertilisation block (conic form); at the
    NLP form's solution the sum of its NUTNED_ rows is this equation exactly. None without CAPRI's data."""
    R = D.region(capri_region, "P")
    if R is None:
        return None
    eff = float(R.mine_eff) if R.mine_eff == R.mine_eff else 1.0
    g0 = float(R.excr_avail) if R.excr_avail == R.excr_avail else 0.0
    gc = float(R.cres_avail) if R.cres_avail == R.cres_avail else 0.0
    dot = lambda c, lv: sum(float(c.get(k, 0.0)) * float(v) for k, v in lv.items())
    need0 = dot(need, xb)
    net0 = need0 - gc * dot(own, xb)
    # as the block (SupplyModel._npk_spec): kappa 1 where the base has no need net of own residues (Berlin)
    kappa = (eff * dot(mine0, xb) + g0 * E0 + gc * dot(pool, xb)) / net0 if net0 > 0 else 1.0
    N = sum(float(need.get(k, 0.0)) * float(sq.get(k, 1.0)) * float(v) for k, v in x.items())
    if grass is not None:
        N += float(grass[0]) * float(grass[1]) * float(grass[2])
    M = (kappa * (N - gc * dot(own_perm, x)) - g0 * E - gc * dot(pool, x)) / eff
    return M                          # kg/ha x 1000 ha = t, as E
