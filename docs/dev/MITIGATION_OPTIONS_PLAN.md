# CAPRI's mitigation options not yet built: the port plan (15 November 2026)

The project lead's decision of 15 November 2026 (00:37): the options of KNOWN_ISSUES K93 are ported before the Bonn
contact, ahead of D2 and the final Farm-to-Fork + Green Deal pair (S10, deferred on 9 November, brought forward).
Each option enters the regional model in CAPRI's form (supply/supply_model.gms) with its parameters from CAPRI's own
files as CSV; nothing is written here yet.

## What the options do in CAPRI's runs held

In CAPRI's Green Deal 2030 as checked on 29 October 2026 (scen_greendeal_2030, K93) none of them moved the result:
LegSh on 0.002% of the EU's other fodder, the others at no level. The project lead's Green Deal pair of 14 November
2026 (res_2_1730greendeal_lnds8_..._defaultA against res_2_1730greendeal_refdefaulta) differs: ConsTill and NoTill
carry effects in the scenario only (France: soil N2O of mineral N -0.0068 kt, leaching -0.011 kt N, GWP -2.07 kt
CO2eq, ConsTill's cost about -10 EUR per ha of each crop; in the reference none), and UreaSubst's urea CO2 is booked
in both (EU 875 kt). Small next to the Green Deal's own changes, but CAPRI's Green Deal moves them: they are part of
test D's like-for-like comparison, not only of the emission-tax runs. They act most under an emission price. No
CAPRI carbon-tax result is held, so each option is checked against CAPRI's code and calibration (costsavings_ini_21730,
the technology files) unit by unit; a CAPRI carbon-tax run is in the benchmark protocol's requests (test D).

## The options, in the order of the port

| # | Option | CAPRI's equations (supply_model.gms) | Parameters (CAPRI's files) | Hook in capri-mod |
|---|---|---|---|---|
| 1 | UreaSubst | GASTOTNETF_ NH3 term l. 3374-3377; GWPCO2UREA_ l. 3966-3972; the cost in GHG_Mit_Cost_ l. 4945; envind/ammo_tech.gms l. 2353-2372, 3041-3107 | p_fracUseFert(Ureum) (LitRev FracUseFert.csv); othImpact NH3SYN; costs (costsavings) | n_cascade.netf's urea, urea_eff arguments (K153); a share column per region in the abatement block |
| 2 | LegSh | NUTNED_ l. 1111-1112, l. 1231; e_BIOFIX l. 1456 (BioFix multiplier on OFAR) | miti_data_jul15 p_ghgMiti LegSh (costParLin, QEmitt, othImpact BioFix; in capri_data/sources) | the fertilisation block's OFAR need and the N balance's fixation |
| 3 | ConsTill, NoTill | runoff and leaching terms l. 3290-3308; the technologies' split l. 4191-4195 (levl(T1)/levl(T2) shifted by the tillage and buffer shares) | envind/tillage.gms with dat/envind/tillageCover.gdx; costsavings | the mix columns (K155: z free both ways); n_cascade.netf's till_n2o |
| 4 | Buffer strips | the landscape-features row LscpFeatArea_ l. 2323-2340; runoff l. 3290; the technologies' split l. 4191 | envind/bufferStrips.gms with dat/envind/nvz.gdx, waterMetersPerHa.gdx, soc_data.gdx | the landscape floor (e_setaLandscape) and the cascade |
| 5 | Biodiversity options (mitiTechBiod) | LscpFeatArea_ l. 2336-2338; runoff l. 3290 | envind/landscape.gms with dat/envind/landscape_nuts2.gdx, soc_data.gdx | as buffer strips |
| 6 | Biochar | leaching l. 3424; CO2SEQ l. 4077-4079 | envind/biochar.gms | the cascade and the soil carbon accounts |
| 7 | SupplementPerc_ | the ration's total fat | envind/line_nitr.gms | the feeding block (linseed, nitrate, 3-NOP are in) |

Data in hand: dat/envind's tillageCover, nvz, waterMetersPerHa, soc_data and landscape_nuts2 (GDX, in the course copy
of CAPRI's dat folder, capri_sources outside git), costsavings_ini_21730_jul15 (uploaded), miti_data_jul15 (in
capri_data/sources/raw/capri/dat/scen/ghgtech). Each goes to CSV through a builder, with provenance and schema rows.

## Checks, per option

1. The parameters against CAPRI's own values (the builders' output against the GDX, value for value).
2. The base point unchanged: each option at CAPRI's initial share (IniShare), a first-order point of the regional
   model (calibrated as the existing options).
3. A unit check of the option's effect against CAPRI's formula at a given share (the cascade's losses, the need, the
   fixation, the CO2).
4. A mini-EU carbon-tax run (CARBON_TAX_50): the shares adopted and their effects reported; the Farm-to-Fork and Green
   Deal mini runs unchanged within 0.1 point (none of the options moves CAPRI's own result there).

## Open points

- The tillage options and buffer strips shift CAPRI's T1/T2 split (l. 4191-4195): their port follows K155's
  validation, so the mix columns' response is CAPRI's in both directions first.
- The biodiversity options and buffer strips count towards CAPRI's landscape target (LscpFeatArea_): with them the
  Green Deal's landscape floor (DE21's gap, claude/gap_analysis_gd.md) has more ways to be met than now; whether CAPRI's
  Green Deal uses them (no level in scen_greendeal_2030) is checked first in the project lead's Green Deal run.
