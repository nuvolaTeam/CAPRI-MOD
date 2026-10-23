# Phosphate balance (CAPRI's gross balance for PHOF)

The environmental accounts carry CAPRI's gross phosphate balance, the balance CAPRI reports in
`reports/calc_nbalance.gms` with `FNUT = PHOF`. Code: `capri_mod/environmental/p_balance.py` (the formulas) and
`EnvironmentalModule.compute_phosphorus_balance` (the items from a regional solution). Data:
`tools/build/build_p_balance.py`. Tests: `capri_mod/tests/test_p_balance.py`.

## Units

CAPRI reports phosphate as **P2O5** throughout (PHOF, MANP, PRET, PCRD), in 1000 t per region and in kg per ha of
UAAR (`dataOut` row `perha`). capri-mod keeps P2O5. The accounts are in **t P2O5** (1000 ha x kg/ha, the same unit as
the N columns), so 1 kt in CAPRI's tables is 1,000 in the accounts. Elemental P = 0.4364 x P2O5.

## Items

| Column of the environmental table | CAPRI item | CAPRI's formula (calc_nbalance.gms) | capri-mod |
|---|---|---|---|
| `p_manure_excretion` | EXCRET | sum over animal activities of LEVL x MANP (l. 144-146) | herd x manure P2O5 per head (`livestock_manure_p_coef.csv`: CAPRI's 2017 MANP totals / the model's herds, as the fertilisation block uses) |
| `p_manure_net_export` | MTRADE | manure exports - imports (l. 175, ManureTradeNEW) | EXCRET - manure P2O5 applied in the region (ManureNPK_); see below |
| `p_mineral_input` | MINFER | NETF = -v_netPutQuant(PHOF) (l. 115) | the regional model's P2O5 purchases; see below |
| `p_crop_residues` | CRESID | sum over crops of LEVL x the crop's residue output (MANP of a crop = PCRD) (l. 197-207); for P nothing is netted out | area x PCRD x yield / base yield |
| `p_uptake` | EXPPRD | sum over crops of LEVL x DATA(crop, PHOF) (l. 55-59), which at that point is still the **retention** (l. 45-46; PRET in the results, not the managed need PHOF they report) | area x PRET x yield / base yield |
| `p_runoff` | RUNANI | sum over animal activities of LEVL x MANP x v_emiLoss(N, RunTot) (l. 71, 103-106): CAPRI applies the N runoff share to manure P2O5 | herd x MANP x RunTot from capri-mod's N loss cascade (`n_cascade.losses`) at the solution's option shares, winter cover and manure inhibitor share |
| `p_input` | IMPORT | EXCRET - MTRADE + MINFER + CRESID (l. 237-243) | same |
| `p_surplus` | SURTOT | IMPORT - EXPPRD (l. 305-313) | same |
| `p_surplus_soil` | SURSOI | SURTOT - RUNANI (l. 247-262); no gaseous terms for P | same |

Removal and residues per ha of the model's crops come from CAPRI's 2030 reference (`p_balance_crop_coefs_2030.csv`:
PRET and PCRD per CAPRI crop pooled into the model's crops by area, as `tools/build/build_npk_balance_2030.py` pools; GRAE and
GRAI on their own for the grassland split column, whose area shift adds z x (GRAE - GRAI)). A crop CAPRI does not grow
in the region takes the country's coefficient.

CAPRI's supply model has its own P surplus (e_SURTOTHa, e_SURSOIHa, supply_model.gms l. 1463-1490); there `v_gasrunani`
is MANN-only (l. 1322), so its SURSOI for P equals SURTOT. The accounts follow the reported balance (calc_nbalance),
which the comparison below uses.

### Mineral P2O5 and manure applied

- **NLP form** (default): the fertilisation block (NUTNED_ per crop group, fertDistMine_, fertDistExcr_; capri_regional_nlp)
  gives the P2O5 purchases (`fert_npk["P"]["purchase"]`) and the manure P2O5 applied (sum of its manure flows); MTRADE =
  EXCRET - applied.
- **Conic form**: the regional model has no fertilisation block. The accounts evaluate CAPRI's NUTNED_ for P summed
  over the crop groups with the block's own data (`p_balance.nutned_mineral`):
  kappa x (sum need_c sqrt(y/y0) x_c - gc x own residues) = eff x MINE + g0 x manure applied + gc x residue pool,
  with kappa closing it at the base levels as the block does: once, with the base manure of the first manure-trade
  setting seen for the region (the run's baseline), and fixed after that (CAPRI's v_cropNutNeedMultFact). Manure applied = CAPRI's 2030 applied share
  (1 - MTRADE/EXCRET) x EXCRET plus the region's manure trade in its base P/N proportion, as the block builds it.
  Purchases are clipped at zero. The P balance does not constrain or cost the conic solution, so this is an
  evaluation after the solve. At the NLP form's solutions the same formula gives the block's purchases exactly (tests).

### Organic area

`organic_area` (1000 ha) is the area converted by the scenario's organic target: each crop's area x its converted share
(`SupplyModel._organic_conv`, exposed as `SupplyResult.organic_conv`; organic_area.gms with capri-mod's per member state
and crop-class conversion). CAPRI's targets are percentage points above the baseline's organic area (EU 10%,
load_organic_targets.gms), and neither CAPRI's data nor capri-mod hold that baseline area per region, so the column is 0
without a target.

## Comparison with CAPRI

### Formula, with CAPRI's own levels

From CAPRI's Green Deal 2030 reference with endogenous technologies at their initial shares (the "ini" run, as for N
leaching), 1000 t P2O5, formula / CAPRI:

| Region | EXCRET | CRESID | EXPPRD | RUNANI (capri-mod cascade) | SURTOT | SURSOI |
|---|---|---|---|---|---|---|
| DE11 | 15.733 / 15.733 | 12.714 / 12.714 | 31.935 / 31.936 | 0.812 / 0.812 | 8.313 / 8.313 | 7.501 / 7.501 |
| NL22 | 39.554 / 39.554 | 12.540 / 12.540 | 23.961 / 23.961 | 1.319 / 1.319 | 26.019 / 26.019 | 24.700 / 24.700 |
| PL22 | 6.094 / 6.094 | 5.054 / 5.054 | 15.502 / 15.504 | 0.484 / 0.484 | 6.920 / 6.920 | 6.436 / 6.436 |
| DK | 127.528 / 127.528 | 80.409 / 80.409 | 199.757 / 199.767 | 5.288 / 5.288 | 44.375 / 44.375 | 39.087 / 39.087 |

EXCRET and CRESID exact; EXPPRD within 0.02% here and 0.4% in the worst of 270 regions of the ini run (exact in the
reference run; in the ini run the reported PRET differs slightly from the coefficient the balance used, cause not
traced); RUNANI from the cascade at CAPRI's option shares and winter cover within 1e-6 (and CAPRI's own per-activity
runoff share reproduces RUNANI in all 250 regions that report it);
IMPORT, SURTOT, SURSOI exact from the items in every region of both runs. CAPRI's elementary bull activities are BULL
(low intensity) and BULH; BULF is their aggregate.

### Levels: the accounts at the model's base data

The accounts at the model's base data (2017 herds and areas, CAPRI's 2030 coefficients; mineral P2O5 = the
fertilisation block's base purchases, which the NLP baseline reproduces; runoff at CAPRI's initial option shares)
against CAPRI's 2030 reference (`res_2_1730greendeal_refdefaulta`), 1000 t P2O5, capri-mod / CAPRI:

| Region | EXCRET | MTRADE | MINFER | CRESID | EXPPRD | RUNANI (ini) | SURTOT | SURSOI |
|---|---|---|---|---|---|---|---|---|
| DE11 | 19.30 / 15.71 | -3.42 / -2.78 | 8.74 / 9.02 | 12.23 / 12.71 | 32.25 / 31.93 | 0.98 / 0.67 (0.81) | 11.43 / 8.30 | 10.46 / 7.63 |
| NL22 | 43.86 / 39.54 | 2.81 / 2.53 | 0.38 / 0.41 | 12.63 / 12.55 | 24.66 / 23.96 | 1.47 / 1.43 (1.32) | 29.40 / 26.01 | 27.93 / 24.58 |
| PL22 | 7.08 / 6.10 | 0.79 / 0.68 | 13.43 / 11.92 | 5.80 / 5.04 | 17.38 / 15.47 | 0.56 / 0.39 (0.48) | 8.13 / 6.90 | 7.57 / 6.52 |
| DK (DK01-05) | 136.06 / 127.17 | 0 / 0 | 41.38 / 36.22 | 86.74 / 80.38 | 202.32 / 199.56 | 5.70 / 4.91 (5.29) | 61.86 / 44.21 | 56.17 / 39.30 |
| EU27 | 4,609 / 4,475 | -16 / 5 | 2,589 / 2,530 | 3,970 / 3,910 | 8,798 / 8,662 | 260 / 229 (249) | 2,386 / 2,248 | 2,125 / 2,019 |

Per ha of UAA (EU27; 165.7 Mha in the model's base data, 162.3 Mha in CAPRI's 2030 reference), kg P2O5/ha:
excretion 27.8 / 27.6, mineral 15.6 / 15.6, residues 24.0 / 24.1, removal 53.1 / 53.4, runoff 1.6 / 1.4, surplus
14.4 / 13.9, soil surplus 12.8 / 12.4. Regional surplus per ha: correlation 0.99 over 213 NUTS-2 regions.

The formulas agree; what differs is the levels. The base data are 2017 herds and areas against CAPRI's 2030 levels,
and manure P2O5 per head is CAPRI's 2017 regional total over the model's herd: excretion is 23% above CAPRI's 2030
reference in DE11 and 16% above in PL22, which carries into MTRADE (a share of excretion) and the surplus (DE11 11.4 kt
against 8.3; DK 61.9 against 44.2). The runoff is evaluated at CAPRI's initial option shares, the ini run's, so it is
closer to that run (EU 249 kt) than to the reference without endogenous technologies (229 kt). These numbers are not
from a solved 2030 baseline.

### Regional solutions

One market iteration, DE11 and NL22 (DE11, NL22, PL22 for Farm-to-Fork), t P2O5:
- NLP baseline: purchases 8,736 (DE11) and 376 (NL22), the base purchases; conic baseline 8,707 and 320.
- Farm-to-Fork, NLP: purchases 5,948, 755, 10,716; NUTNED_ summed over the groups at those solutions gives the same
  three numbers. Organic area 46.1 kha of 486 (DE11) and 24.7 of 228 (NL22). In the conic form NL22's purchases
  are 0 (clipped: manure and residues exceed the need at the conic solution's levels).

## Departures and open points

1. **Removal and residues follow the yield** (realised / base yield), as the N accounts do. CAPRI's e_EXPPRD and
   e_CRESID scale the coefficients with the yield factors of its options (v_yldMit, v_yldPestFac) and its technology
   factors; capri-mod's yields also move with prices and the organic and pesticide targets. The NLP block holds the
   arable residue pool per ha at the base (not scaled), so the block's residues and the accounts' differ under a
   yield change.
2. **Manure P2O5 per head does not change with the split and option columns** (dairy, bulls and heifers, genetics),
   as in the fertilisation block (only N's manure follows them, K50 departure 12). In CAPRI MANP differs between DCOL
   and DCOH (73.9 and 93.3 kg in DE11) and genet_yld changes it.
3. **Manure P2O5 applied with manure trade off**: fixed 20 October 2026 - with trade off the block and the accounts
   apply all of the region's manure P2O5 and K2O, as N (before, CAPRI's 2030 net-export share was applied whatever
   `manure_trade` was).
4. **Runoff share**: capri-mod's animals pool CAPRI's sub-activities; their runoff shares are weighted by manure N, not
   manure P2O5. RunHous and RunSurf are held within [0, 1] in the accounts (CAPRI's bounds on v_emiLoss,
   set_supply_bounds.gms l. 240-243). Since 20 October 2026 the NLP form also bounds every loss of the cascade at zero
   inside the regional model, as CAPRI (a row for each loss that can turn negative at the options' maximum shares and is
   not negative at base): option shares like NL22's earlier ManStorCon 0.50 / 0.75 with CovStorLowCon 0.25, which drove
   RunHous negative, are ruled out as in CAPRI's supply model.
5. **Conic form**: mineral P2O5 is an evaluation of NUTNED_ after the solve, clipped at 0; P does not enter the conic
   solution.
6. **Organic area** is the area converted by the target, not the total organic area (no baseline organic area in
   CAPRI's or capri-mod's data).

Not ported (beyond CAPRI's standard balance): CAPRI's optional endogenous P excretion (`%Phoendogenous%`, off by
default, envind/ammo.gms l. 28; reports/Checking_MANNP.gms, Runoff_PHO.gms) and the soil P losses of its erosion report
(reports/soil_erosion.gms, p_phoErosion).
