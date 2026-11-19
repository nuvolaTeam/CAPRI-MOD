"""CAPRI's leaching of the soil N surplus and the indirect N2O of leached and run-off N, in CAPRI's form
(supply/supply_model.gms LEACHN_, AMMOAGG_, GWPN2OLEA_; envind/gases.gms l. 696-745 for the accounts).
Data: tools/build/build_n_leaching.py (n_leaching_region.csv), fertiliser options' NO3 effects in fert_side_effects.csv
(tools/build/build_fert_side_effects.py), the application options' no3mlea in n_cascade_effects.csv (tools/build/build_n_cascade.py).

CAPRI's LEACHN_ (with its first factor LEACHN_B1) and AMMOAGG_ are in
capri_mod/supply/equations/supply_model/n_flow.py (until 19 November 2026 here and in the accounts), with their
departures: B2 held at CAPRI's Green Deal 'ini' reference (REGISTERED) and the sign of the application options'
leaching effect (CAPRI-ERROR-FIX FIX-2, the setting environment.ammapp_sign). This module keeps the data (load,
capri_region), the share for a CAPRI region (share), the fertiliser options' effect (fert_effect, ghgMiti.gms) and
the accounts' allocation to the crops (crop_n, gases.gms).

Indirect N2O of leached and run-off N allocated to crops (gases.gms l. 696-745), t N:
  mineral runoff        MINFER x RunTot_NETF
  manure surface runoff sum_a N_a x RunSurf_a
  mineral leaching      MINFER x (1 - GasRunTot_NETF - e) x L
  manure leaching       [sum_a N_a (1 - GasRunTot_a - e) - MTRADE (1 - e)] x L
  deposition, residues  (ATMOSD + CRESID) x (1 - N2O GasTot_NETF - e) x L
  fixation              BIOFIX x (1 - e) x L
with e = EXPPRD / IMPORT of CAPRI's 2030 reference; N2O = that x EF5 x 44/28, EF5 = 0.0075 (GHGEFS, envind/
create_rawdat_gascoeff_gdx.gms l. 713). The housing runoff (MANN x RunHous x EF5) is allocated to the animals and is
part of the manure N2O factors (f_lea).
"""
from __future__ import annotations

from capri_mod.data.definitions import capri_ms  # noqa: E402  (TUR for Turkey's units)
from capri_mod.supply.equations.supply_model.n_flow import LEACHN_, LEACHN_B1

# EF5 and winter cover's reduction of the leaching factor (envind/cover_crops.gms l. 402) are the parameters
# EF5_LEACHING_N2O and WINTERCOV_NO3_REDUCTION (one parameter with n_cascade's runoff effect)
# the sign of the application losses: the setting environment.ammapp_sign, "consistent" (- agg, as RUNSURFN_; default)
# or "capri" (CAPRI's code: + agg)
APPL = ("AmmAppLE", "AmmAppHE")   # APPLN_'s terms, as n_flow.APPL_TECHS (checked against MitiTechAmm)

_REG = {}
b1 = LEACHN_B1        # the accounts' and the tests' name until 19 November 2026


def load(data_dir=None):
    """{CAPRI region: {leach_base, leach_ini, exp_imp}} (n_leaching_region.csv)."""
    from capri_mod.supply.inputs import SupplyInputs, current
    inp = SupplyInputs(data_dir, current().base_year) if data_dir else current()
    key = str(inp.path("", "abatement/ammonia"))
    if key not in _REG:
        out = {}
        for r in inp.rows("n_leaching_region.csv", "abatement/ammonia"):
            out[r["region"]] = {k: (float(v) if v not in ("", None) else None) for k, v in r.items() if k != "region"}
        _REG[key] = out
    return _REG[key]


def capri_region(region, data_dir=None):
    """The model region's CAPRI region: the region itself (the model's regions are CAPRI's units), else its member
    state's row where CAPRI's table has no row for the region."""
    rs = str(region)
    if rs not in load(data_dir):
        ms = capri_ms(rs)
        rs = ms if ms in load(data_dir) else rs
    return rs


def share(rs, b1_now, b1_ini, data_dir=None):
    """The leaching share of the soil surplus for CAPRI region rs (LEACHN_, n_flow.py), or None without data."""
    x = load(data_dir).get(rs) or {}
    return LEACHN_(x.get("leach_ini"), x.get("leach_base"), b1_now, b1_ini)


def fert_effect(lit, nmin):
    """ghgMiti.gms l. 552-563: the option's change of the factor per kg of N, 1 - (1 - lit) (1 + NMIN)."""
    return 1.0 - (1.0 - float(lit)) * (1.0 + float(nmin or 0.0))


def crop_n(mineral, run_tot_netf, grt_netf, n2o_netf, manure_terms, mtrade, dep_res, fixation, L, e):
    """t N leached or run off allocated to crops (gases.gms l. 696-745). manure_terms: [(N_a, RunSurf_a,
    GasRunTot_a)], N_a t N excreted; mtrade: net manure exports (t N, + = export); dep_res: deposition + residues (t N);
    fixation (t N). Returns {component: t N}."""
    out = {"min_run": mineral * run_tot_netf,
           "man_run": sum(n * rs_ for n, rs_, _ in manure_terms),
           "min_lea": mineral * (1.0 - grt_netf - e) * L,
           "man_lea": (sum(n * (1.0 - g - e) for n, _, g in manure_terms) - mtrade * (1.0 - e)) * L,
           "dep_lea": dep_res * (1.0 - n2o_netf - e) * L,
           "fix_lea": fixation * (1.0 - e) * L}
    return out
