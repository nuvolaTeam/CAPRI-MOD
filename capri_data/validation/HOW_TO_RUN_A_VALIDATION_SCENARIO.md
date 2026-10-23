# How to run a CAPRI scenario for comparison with capri-mod

Status: revised 20 October 2026 against the code. The CAPRI-side steps were written in October 2026 from CAPRI's GUI
and folder conventions and have not been re-checked in a CAPRI installation since.

A comparison of response magnitudes needs a CAPRI run pair (reference and scenario) with a clear policy contrast,
from the same CAPRI version capri-mod is built from (star 3.0, base 2017, 2030). One such pair is in hand: CAPRI's
2030 run without voluntary coupled support against its reference (`coupled_support_2030/capri_vcs_effect.csv.xz`,
`tools/build/extract_capri_vcs_pair.py`, compared by `tools/run/run_vcs_2030.py`). Wanted next (README 11.4, 13; KNOWN_ISSUES
K13):

- **CAPRI's Green Deal 2030 step** (lnds 8, org 18, pest 20, mine 13crp, surp 30; result name
  `res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA`), against which capri-mod's
  `greendeal_2030_scenario()` run is to be checked;
- **CAPRI's Farm-to-Fork dairy market results** (raw milk and dairy product prices and quantities), for the milk
  price gap (K13).

## What makes a good comparison scenario

A strong, well-defined shock that capri-mod applies in the same way:

| CAPRI scenario | capri-mod |
|---|---|
| Green Deal switches (`pol_input/greendeal/greendeal_scenarios.gms`) | `greendeal_scenario(...)` with the same values (README 8.3) |
| change of the direct payments or coupled support | `PolicyScenario.biss_rate_change`, `coupled_support`, `premium_factor_regional` (README 8.1) |
| change of EU import tariffs | `PolicyScenario.tariff_changes` (acts on EU imports only; tariff-rate-quota changes have no effect, K52) |
| biofuel mandate change (`scen/bio_fuels/change_biof_mandate.gms`) | `PolicyScenario.biofuel_mandate` |
| emission tax (`pol_input/ecampa/carbtax50_endotech_*.gms`) | `PolicyScenario.carbon_tax` |

Avoid scenarios driven by exogenous trends or technology paths that capri-mod's comparative-static run does not
represent. Run the scenario against the same 2030 reference, with the same technology (endotech) settings in both
runs, as CAPRI's scenario files do.

## CAPRI side (GUI)

1. Open the CAPRI GUI; task "Run scenario with market model" (capmod).
2. Choose the 2030 reference as baseline and define or select the scenario (examples under `pol_input/`).
3. Run for the single year 2030.
4. Results are written to `output/results/capmod/res_<scenario>...gdx`.

## What to extract

From the reference and the scenario run, the result parameter `DATAOUT`:

```
gdxdump <path>\res_<REFERENCE>.gdx symb=DATAOUT output=<path>\scen_ref.txt
gdxdump <path>\res_<SCENARIO>.gdx  symb=DATAOUT output=<path>\scen_shock.txt
```

or `tools/build/gdx_dump_symbol.py GDX DATAOUT OUT.csv --nonzero`. The comparison is of % changes from reference to
scenario, as `tools/run/run_vcs_2030.py` does for the coupled-support pair (EU27 herds, crop areas, product and
young-animal prices).
