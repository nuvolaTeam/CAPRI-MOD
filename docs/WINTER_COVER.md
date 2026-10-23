# Winter cover (catch crops) as a choice of the regional model

*Status: 20 October 2026. NLP form only. In the conic form the share stays CAPRI's 2030 catch-crop share, or the
Farm-to-Fork requirement.*

## What CAPRI does

In CAPRI the catch-crop share is a mitigation option of the regional model: v_Miti(CATC, WinterCov, CO2SEQ). It is the
share of UAAR, and it is tied to the CATC activity (catcMiti_: v_actLevl(CATC) = v_Miti × UAAR). Sources:
envind/cover_crops.gms and supply/supply_model.gms.

| Element | CAPRI (file, lines) | capri-mod |
|---|---|---|
| Upper limit | winterCover_: UAAR − Σ_c crop_c × p_winterCoverShare_c + FALL.FLOOR ≥ CATC (supply_model.gms 1979-1992) | the same row, with the model's crop levels. **REGISTERED:** the right-hand side is at least the base point's. |
| Maximum share | MaxShare = min(1, Σ_c p_coverMax_c × LEVL_c / UAAR), where p_coverMax = 1 − p_winterCoverShare0 (cover_crops.gms 336-345) | the same, at CAPRI's 2030 crop levels (`tools/build/build_winter_cover_option.py`) |
| Initial share | IniShare (cover_crops.gms 348, 382) | CAPRI's 2030 reference share CATC / UAAR (`cover_crops.csv` catc_share_2030): the share the model's base already uses |
| Cost | the CATC activity's input cost (TOIN, costParLin), plus pmpParLin × m + ½ pmpParSqr × m², from the relSubs cases (cover_crops.gms 550-700; sensFac 1; premCapMitTech off in CAPRI's Green Deal settings) | the same; case 1 applies in every region (positive cost, positive initial share) |
| Requirement | e_minCoverCrops: CATC ≥ p_minCoverCrops (supply_model.gms 2352) | the option's lower bound (the Farm-to-Fork requirement, `_cover_crop_requirement`) |
| Nitrogen | BioFix × CATC goes into the arable residue pool (fertDistCres_, l. 1076) and into the gross balance (e_BIOFIX) | the change from the base share goes into the residue pool of the NLP's fertilisation block and into the N-surplus row |
| Runoff and leaching | 0.35 × v_Miti in RUNSURFN_, APPLN_ and LEACHN_ | the share in the loss cascade (manure N kept) and in the accounts' leaching share |
| Emission tax | the crop-residue N2O of CATC (N2OCRO) is in GN2O and so in the taxed GGWP; the soil carbon (CO2SEQ) is not in GGWP | N2OCRO taxed. **REGISTERED:** the purchases' leaching stays at the reference leaching share under the tax, so the share's effect on it is not priced. |
| Calibration | CAPRI's cost curve, calibrated in its reference run | linear term set so that the base share is a first-order point of the model (as for the other options) |

## Behaviour

These are checks on three regions (DE11, FR10, PL22, plus NL22 under the tax), not results of a full run:

- **Baseline:** the base share is reproduced (DE11 0.1242).
- **Farm-to-Fork:** the requirement binds. DE11 goes from 0.124 to 0.198, PL22 from 0.040 to 0.138, and FR10 to 0.300.
- **Emission tax of 100 EUR/t:**
  - without the taxed N2OCRO, the share rose (PL22 0.04 to 0.20);
  - with it, as CAPRI taxes it, it falls slightly or stays: DE11 0.124 to 0.121, NL22 0.128 to 0.133, PL22 0.040 to 0.
- **Why the response is large:** CAPRI's cost curve is flat (Subs1 = 0.8 × MaxIncrease × cost at MaxShare), so a few EUR/ha of net value move the share a long way.

Test: `test_winter_cover_is_chosen_in_the_nlp_form`.
