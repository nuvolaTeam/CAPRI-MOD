# S1: CAPRI's two crop technologies as mix columns (design, 8 November 2026)

Status: design, before implementation. Decision of 1 November 2026 (docs/design/S1_S2_DESIGN.md section 5, option (c));
answers of 7 November 2026 (S2 first; MXSETA_ left out as CAPRI; FALL's column only where CAPRI has its T2). S2 is
done (KNOWN_ISSUES K121-K123). DEP-9 is the departure this closes.

## 1. What CAPRI does

Each crop activity of TACT (intens/techf.gms l. 64-75: the crops but grassland; set-aside back in after the factors)
has two technologies, T1 (high yield) and T2 (low yield), split 50-50 at the calibration point. Against the mean
(p_technFact, read from sim_ini_21730 into capri_data/sources/intermediate/technology/techn_fact_2030.csv):

| item | T1 | T2 | source |
|---|---|---|---|
| outputs (PACT_TO_O: main output, straw, ...) and "Yield" | +0.20 | -0.20 | techf.gms l. 83-86 |
| inputs other than nutrients and water (SEED, REPM, REPB, ELEC, EGAS, EFUL, ELUB, INPO) | +0.25 | -0.25 | l. 92-96 |
| irrigation water | 0 | 0 | l. 98-99 |
| plant protection PLAP | +0.40 | -0.40 | l. 104-105 |
| nutrient removal (NITF, PHOF, POTF) | the yield factor | | fert/fertned.gms l. 206-207 |
| rural-development premiums DPRD_AE1..8, SeBete, SeVall | -0.50 | +0.50 | policy/rd_logic.gms |
| DPRD_N2K | -1.00 | +1.00 | idem |
| DPRD_SeExte | -0.50 or -1/3 | +0.50 or +1/3 | idem |
| sugar beet VCOF | SUGDATA | | sugar/techf.gms l. 103 |

VSET carries only DPRD_SeExte (9 regions); FALL the DPRD premiums. GRAE and GRAI have the single technology T.

NUTNED_ (supply/supply_model.gms l. 1095-1137) multiplies each technology's need by
SQRT(1 + yield factor (+0.2 GRAI, -0.2 GRAE)) x (1 + nutrient factor) x v_cropNutNeedMultFact(region, nutrient, A).
In sim_ini_21730 the multiplier is the same for T, T1 and T2 in every region (750 region x nutrient cells checked),
i.e. one per region and nutrient, as the model's kappa. CAPRI's 2030 output is consistent with the model's base need
per ha: the equation's left-hand side per group (nutNed_lhs1) over area x the reported need per ha is the same for the
grassland and barley groups in all 232 regions (ratio 1.0000, N, P and K; 8 November 2026), so the reported per-crop
need already carries the factors at the calibrated mix. What the model lacks is the response to the mix.

PMP: p_pmpQuadTechn holds a 2x2 block per crop and technology pair and p_pmpCnst a linear term per technology
(both in hand: pmp_quad_techn_2030.csv, pmp_cnst_techn_2030.csv). The group terms p_pmpQuadPact act on the crop's total.

## 2. The mix column

For a crop a with both technologies, X = x_T1 + x_T2 (the model's activity) and z = (x_T1 - x_T2) / 2, so
x_T1 = X/2 + z, x_T2 = X/2 - z; z = 0 is CAPRI's calibration point. Bounds -X/2 <= z <= X/2 as two two-entry rows.

PMP, exact: with M = [[1/2, 1], [1/2, -1]], CAPRI's block Qt becomes M' Qt M:
  Q_XX = (q11 + 2 q12 + q22) / 4,  Q_Xz = (q11 - q22) / 2,  Q_zz = q11 - 2 q12 + q22.
The model's present curvature on X is 1 / (1' Qt^-1 1), the Schur complement Q_XX - Q_Xz^2 / Q_zz: checked on all
5,417 T1/T2 blocks of pmp_quad_techn_2030.csv, largest relative difference 1.4e-13; all blocks positive definite;
86% symmetric (Q_Xz = 0). So with z in the model, X's diagonal becomes Q_XX and the block adds Q_Xz and Q_zz; the
group terms stay on X. Without anything else depending on z the model is unchanged (z optimised out gives today's
curvature), which is the first numerical check.

Per unit of z (1000 ha moved from T2 to T1), at the current prices, yields and costs of the crop:
- revenue: +0.4 x output value (main output and by-products, as the crop's revenue);
- costs: +0.5 x the factored inputs' cost, +0.8 x plant protection; none for fertiliser (through NUTNED_) and water;
- premiums: (f_T1 - f_T2) x each rural-development scheme's premium per ha (-1 x AE, -2 x N2K, ...);
- nutrient need: (g_T1 - g_T2) / gbar x the crop's need per ha, g_t = SQRT(1 + y_t) x (1 + y_t), gbar the 50-50
  mean (1.015 at +-0.2): +0.590 x need;
- crop residues and nutrient removal in the balances: +0.4 x the crop's (yield-dependent) part;
- fodder crops (MAIF, ROOF, OFAR): +0.4 x the fodder output u per ha in the fodder rows;
- production: gross output = yield x (X + 0.4 z), the realised yield per ha follows.

Linear term: z gets its own calibrated term with the activities (CapriRegionalNLP.calibrate), so the base is a
first-order point at z = 0, as CAPRI's p_pmpCnst makes it. Not a "late" column: no recalibration after the first
solve (the K120 mechanism).

Columns: one per crop with both technologies in the region (pmp_quad_techn_2030.csv); none for VSET and FALL where no
factor moves anything, i.e. VSET outside its 9 SeExte regions; FALL only where CAPRI has T2 (24 regions, the decision
of 7 November 2026). Expected about 25 per EU region.

## 3. Data still to build

1. Per crop and region, the factored inputs' costs (SEED, REPM, REPB, ELEC, EGAS, EFUL, ELUB, INPO, PLAP, WATR) from
   CAPREG (res_17<CC>.txt), in the model's money: an extension of plant_protection_cost.csv
   (tools/build/build_plant_protection_cost.py, which already writes plap, inpo, fert, eful from the same dumps).
2. The rural-development premiums per scheme and crop: premium_scheme_shares_2030.csv has DPRD_N2K and DPAE; DPAE
   joins CAPRI's DPRD_AE1..8 with the national schemes, which carry no technology factor. To check against CAPRI's
   2030 premium items before deciding; until then only N2K and the DPRD part of DPAE that CAPRI's data identify.
3. The mix PMP terms per region and crop in the model's g convention (g = H x X^2 at CAPRI's 2030 level, as
   pmp_capri_2030.csv): g_XX_extra = (Q_XX - c) X^2, g_Xz = Q_Xz X^2, g_zz = Q_zz X^2, in the model's 2017 money
   (K108): a new output of build_pmp_capri_2030.py, pmp_capri_2030_mix.csv.
4. The need factors per technology (g_t) from techn_fact_2030.csv's Yield row.
Each with its schema entry, provenance, manifest and validate_data at 0 violations.

## 4. Model changes (from the code map of 8 November 2026, branch s1)

- Columns appended after the histosol columns (supply/abatement.py _histosol_columns), labelled "mix_<crop>"
  (nlp._aug_col_labels gives unknown columns positional labels, which would mis-map the calibration's dq), also on the
  plain path (supply_module.py l. 1739-1741).
- PMP: X's diagonal + g_XX_extra / X^2, the X-z and z-z terms (the first X-z cross term in the code).
- Linear term from the crop's components after every mutation of net_revenues (policy.py yield response, organic
  target, pesticide reduction, Green Deal input changes, yield input costs; abatement.py GHG tax; fertilisation.py
  balance price), computed once at c_lin (supply_module.py l. 1662) from the same components, so every scenario rule
  reaches z.
- NLP form: z in the NUTNED_ need pairs (fertilisation._npk_spec, "need" only, not "crops"), in
  _n_row_mineral_parts, in N_balance and mineral_N; the fertiliser cost taken out of c as for X (nlp.py l. 132-136);
  calibrate: z not "free" (capri_regional_nlp.py l. 984) and its dq kept at zero level (l. 1083).
- Fodder rows (livestock._fodder_rows): +0.4 u.
- After the solve: res.last_mix_z; gross_output with 0.4 z x yield (the dairy split's pattern, supply_module.py
  l. 1826-1843); net revenue and income with z's part; the environmental module's realised yield from gross output;
  ghg_tax.py finite differences with a key per z.
- State: the new fields in supply/state.py and SOLVE_STATE / NLP_STATE.
- A setting `supply.crop_technologies` (on / off) in defaults.toml and SETTINGS_INVENTORY, to compare with the
  collapsed form; off reproduces dev exactly.

## 5. Checks

1. Off: dev reproduced exactly (compare_pickles_exact.py).
2. On, nothing depending on z: identical to off up to solver tolerance (the exact PMP transform).
3. On: the 2030 base at z = 0 (calibration residual, dq_z), mini-EU Farm-to-Fork converged, indicators against S2
   with the differences explained; yield per ha and N per ha responses at the Farm-to-Fork and Green Deal gates
   against CAPRI's results where they report them; supply elasticities against CAPRI's supply_elas files.
4. Full EU Farm-to-Fork and Green Deal; the suite.

## 6. Open points

- The premium split (data item 2).
- Sugar beet's VCOF (sugar/techf.gms): read before deciding whether SUGB gets the general factors or its own.
- Whether CAPRI's endogenous yields (supply/endog_yields.gms, in the model as the yield price response) act on the
  technologies' mean yield as in CAPRI; both act together in CAPRI.
