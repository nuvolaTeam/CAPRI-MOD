"""CAPRI's leaching of the soil N surplus and the indirect N2O of leached and run-off N, in CAPRI's form
(supply/supply_model.gms LEACHN_, AMMOAGG_, GWPN2OLEA_; envind/gases.gms l. 696-745 for the accounts).
Data: tools/build/build_n_leaching.py (n_leaching_region.csv), fertiliser options' NO3 effects in fert_side_effects.csv
(tools/build/build_fert_side_effects.py), the application options' no3mlea in n_cascade_effects.csv (tools/build/build_n_cascade.py).

Leaching share of the soil surplus (LEACHN_):

  L = leach_base x B1 x B2
  B1 = 1 - 0.35 wc - nminSh x sum_fert s x e_SLEA - nmanSh x sum_fert s x e_MLEA + agg      (options capri-mod has)
  B2 = 1 - tillage, buffer strips, biodiversity, biochar terms                               (options it has not)
  agg = v_ammoAppLeaAgg = sum_a N_a (1 - GasRunTot_a) x sum_{AmmAppLE, AmmAppHE} no3mlea x s / sum_a N_a (1 - GasRunTot_a)
  e_SLEA = 1 - (1 - lit) (1 + NMIN) (ghgMiti.gms l. 552-563; NMAN for manure)

B2 is held at CAPRI's Green Deal 'ini' reference: L = leach_ini x B1 / B1_ini (B1_ini at CAPRI's initial shares and
the base winter cover). REGISTERED.

CAPRI-ERROR-FIX (the project lead's decision, 20 October 2026; docs/CAPRI_DEPARTURES_REGISTER.md FIX-2): CAPRI adds agg in LEACHN_ ("+ v_ammoAppLeaAgg",
supply_model.gms l. 3413) while it subtracts the same options' runoff effect in RUNSURFN_ and the fertiliser options'
leaching effects in LEACHN_. Its literature table gives reductions (prep_data_LitRev.gms p_reducGains: positive = less
loss; LNA_low liquid: NH3 0.51, RunSurf -0.24, Leach -0.24), copied without change of sign to no3mlea (ammo_tech.gms
l. 2293), so with the '+' low-emission application lowers the leaching share where the data say it raises it.
capri-mod subtracts it (AMMAPP_SIGN = "consistent", default); "capri" reproduces CAPRI's code. The base is calibrated to
CAPRI's realised share either way (leach_ini), so the sign acts only through changes in the options' adoption.

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

EF5 = 0.0075
WINTERCOV_NO3LEA = 0.35          # envind/cover_crops.gms l. 402
# the sign of the application losses: the setting environment.ammapp_sign, "consistent" (- agg, as RUNSURFN_; default)
# or "capri" (CAPRI's code: + agg)
APPL = ("AmmAppLE", "AmmAppHE")

_REG = {}


def load(data_dir=None):
    """{CAPRI region: {leach_base, leach_ini, exp_imp}} (n_leaching_region.csv)."""
    import csv
    from pathlib import Path
    d = Path(data_dir) if data_dir else Path(__file__).resolve().parents[2] / "capri_data"
    key = str(d)
    if key not in _REG:
        out = {}
        f = d / "2017" / "abatement" / "ammonia" / "n_leaching_region.csv"
        if f.exists():
            for r in csv.DictReader(open(f)):
                out[r["region"]] = {k: (float(v) if v not in ("", None) else None) for k, v in r.items() if k != "region"}
        _REG[key] = out
    return _REG[key]


def capri_region(region, data_dir=None):
    """The model region's CAPRI region: the region itself (the model's regions are CAPRI's units), else its member
    state's row where CAPRI's table has no row for the region."""
    rs = str(region)
    if rs not in load(data_dir):
        ms = rs[:2] + "000000"
        rs = ms if ms in load(data_dir) else rs
    return rs


def b1(wc=0.0, agg=0.0, nmin_sh=0.0, nman_sh=0.0, fert_min=0.0, fert_man=0.0):
    """LEACHN_'s first factor. fert_min / fert_man: sum over the fertiliser options of share x effect (mineral N /
    manure); agg: v_ammoAppLeaAgg."""
    from capri_mod.settings import current as _settings
    sign = 1.0 if _settings().get("environment.ammapp_sign") == "capri" else -1.0
    return 1.0 - WINTERCOV_NO3LEA * wc - nmin_sh * fert_min - nman_sh * fert_man + sign * agg


def share(rs, b1_now, b1_ini, data_dir=None):
    """The leaching share of the soil surplus: leach_ini x B1 / B1_ini (B2 at CAPRI's ini run), or None without data."""
    x = load(data_dir).get(rs) or {}
    li = x.get("leach_ini")
    if li is None:
        lb = x.get("leach_base")
        return None if lb is None else max(0.0, lb * b1_now)
    if not b1_ini > 0:
        return li
    return max(0.0, li * b1_now / b1_ini)


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
