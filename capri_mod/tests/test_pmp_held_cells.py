"""Register DEP-23, closed 23 November 2026: the activities held at their level for lack of a positive CAPRI own PMP
term (capri_mod/supply/supply_module.py SupplyModule._uncalibrated) are held at 0 at the 2030 market year, as CAPRI's.

In CAPRI's 2030 data these cells have no level and no main-output yield at "Y" (sim_ini_21730 DATA: NL34's pulses, for
example, LEVL and PULS at BAS only), so supply/prep_sim.gms l. 91-93 starts them at 0, supply/set_supply_bounds.gms
l. 27-37 bounds only levels above 1e-8, and without a yield they produce nothing: in CAPRI's 2030 reference and in its
Green Deal step every one of them is 0 (dataOut, 23 November 2026). So the model's cell is CAPRI's where its 2030 level
is 0: every cell with a base-year level and no positive own term must have a 2030 trajectory factor of 0
(capri_ref_2030/regional.csv, CAPRI's 2030 reference over its 2017 levels), and CAPRI's 2030 level and yield 0."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D17 = ROOT / "capri_data" / "2017" / "supply"
D30 = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply"
TRAJ = ROOT / "capri_data" / "scenarios" / "capri_ref_2030" / "regional.csv"
REF = (ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "res_2_1730greendeal_refdefaulta"
       / "capri_ref_levl_yild_2030_2017.parquet")


def test_the_cells_without_a_capri_term_are_zero_at_2030():
    from capri_mod.data.definitions import CAPRI_MEMBERS
    from capri_mod.data.loaders import HERD_ALIASES
    from capri_mod.supply.supply_module import RegionalSupplyModel
    p = pd.read_csv(D30 / "pmp_capri_2030.csv", float_precision="round_trip")
    pa = pd.read_csv(D30 / "pmp_capri_2030_animals.csv", float_precision="round_trip")
    own = {(r, a) for r, a, b, g in zip(p.region, p.act_i, p.act_j, p.g) if a == b and g > 0}
    own |= {(r, a) for r, a, g in zip(pa.region, pa.animal, pa.g) if g > 0}
    t = pd.read_csv(TRAJ, float_precision="round_trip")
    fac = t[(t.block == "herds") & (t.year == 2030)].set_index(["region", "item"]).factor
    ref = pd.read_parquet(REF)
    l30 = ref[(ref["item"] == "LEVL") & (ref.year == 2030)].set_index(["capri_region", "activity"]).value
    y30 = ref[(ref["item"] == "YILD") & (ref.year == 2030)].set_index(["capri_region", "activity"]).value
    areas = pd.read_csv(D17 / "base_areas.csv", index_col=0)
    herds = pd.read_csv(D17 / "animal_numbers.csv", index_col=0).drop(columns=["COWS"], errors="ignore")
    held = []
    for tab in (areas, herds):
        for r in tab.index:
            for c in tab.columns:
                v = tab.at[r, c]
                if not (v == v and float(v) > 0):
                    continue
                a = HERD_ALIASES.get(c, c)
                # CAPRI's other animals, a fixed activity (FACT, held at its data level, supply/prep_sim.gms l. 250):
                # no PMP terms, its 2030 level CAPRI's (K207); the fixed crops' cells here are 0 at 2030 in CAPRI
                if (r, a) in own or a in RegionalSupplyModel.OTHER_ANIMALS:
                    continue
                f = fac.get((r, c), fac.get((r, a)))
                mem = CAPRI_MEMBERS.get(a, (a,))
                held.append((r, a, f, sum(float(l30.get((r, m), 0.0)) + float(y30.get((r, m), 0.0)) for m in mem)))
    assert len(held) > 300                                 # 391 at 23 November 2026
    assert all(f is not None and float(f) == 0.0 for _r, _a, f, _l in held), [h for h in held if not h[2] == 0.0][:10]
    # CAPRI's own 2030 level and yield of the crops among them are 0 too
    assert all(l_ == 0.0 for r, a, f, l_ in held if a in areas.columns)
