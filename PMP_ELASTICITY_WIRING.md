# Regional PMP elasticity wiring

All five scoped items handled. Gate unchanged: validator 11 pass / 1 warn / 0 fail,
base fidelity 12/12, supply convergence 30/30, test suite **15 passing** (up from 12).

---

## Correction first

I previously reported that `load_regional_supply_elasticities` was never called.
That was wrong — it is called in `SupplyModule.__init__` and was already active
for **107 of 248 regions** across 15 activities. I had misread a grep. The work
below extends and corrects that wiring rather than creating it.

---

## 1. Dampening — CAPRI's rule, not a truncation

`gams/supply/pmp_terms/impose_upper_bound_on_elasticity.gms` does not clip high
elasticities. Above `p_elasHigh = 4.5` it inflates the PMP quadratic slope so the
effective elasticity becomes `min(8, sqrt(e) + 4.5 - sqrt(4.5))`. The source
comment gives worked values: 10 to 5.6, 20 to 7.0, 40 to 8.

The Python code applied `min(e, ELAS_HIGH / dampen)` = `min(e, 2.25)`, which is
wrong twice over — it truncated legitimate values in (2.25, 4.5] that CAPRI leaves
alone, and it over-dampened everything above. Measured on the active file, **694
of 3420 values (20.3%)** were being truncated, all of them in the range CAPRI
does not touch.

`capri_pmp.dampen_elasticity` implements the real rule, tested against CAPRI's own
worked examples in `test_capri_dampening_matches_gams_reference`.

## 2. Share term

CAPRI scales crop curvature by `1 - 0.2*sqrt(LEVL_activity / arable_total)`, so a
crop occupying a large share of regional arable land gets a flatter response.
Implemented in `capri_pmp.share_term`, computed per region in
`RegionalSupplyModel.__init__` and passed to the calibrator. The diagonal is now

```
Q_ii = p_i / (eps_i * x0_i * shareTerm_i)
```

which is CAPRI's `elas = revenue / (LEVL * shareTerm * (pmpQuadTechn + pmpQuadPact))`
rearranged.

## 3. EPRD_TO_GRP — found

`gams/sets.gms:2918`, the ESTNLP mapping, whose groups match our VB extract exactly:

```
(SWHE,DWHE,RYEM,BARL,OATS).CERE     (RAPE,SUNF,SOYA).OILS
(MAIZ,OCER,PARI).CER2               (PULS,POTA,SUGB).OARA
(MAIF,ROOF,OFAR).FARA
```

The variant in `gams/capdis/sets.gms` uses a different group set (`INDU`, `PULS`,
`SETA`) and must not be used here. Ported to `capri_pmp.EPRD_TO_GRP`. This unblocks
Route B; the cross-group terms themselves are not yet wired.

## 4. Explicit provenance

`build_elasticity_table` merges two CAPRI sources and labels every one of the
9920 region x activity cells:

| provenance | cells |
|---|---|
| `REGIONAL_CAPRI` (`supply_elasticities_regional.csv`, pre-bounded) | 1033 |
| `PMP_CAPRI` (`pmp_own_price_elasticities.csv`, raw, dampened on load) | 272 |
| `LITERATURE_DEFAULT` | 8615 |

**132 regions** now carry real estimates, up from 107, because the second source is
keyed by CAPRI region codes and resolves through the NUTS crosswalk. Coverage is
13.2% of cells across 14 activities. `test_elasticity_provenance_is_complete`
asserts no cell is unlabelled and none exceeds the cap.

## 5. Asymmetry — measured, and it found a real bug

`tools/scenario_elasticity_check.py` runs a +20% cereal price shock under both
configurations. The asymmetry is real:

```
covered activities   median elasticity 1.43
uncovered activities median elasticity 0.18
ratio                                  7.97
```

Where the adjustment lands, 25 regions:

| config | total reallocation (kha) | share in covered arable | share elsewhere |
|---|---|---|---|
| legacy | 569.3 | 65.7% | 34.3% |
| capri | 1306.4 | **86.8%** | 13.2% |

So the model becomes markedly more responsive, and adjustment concentrates in
arable. That is a property of the data coverage, not a defect in the wiring — but
it is now visible rather than implicit, and it argues for extending coverage to
permanent crops and livestock before using this for policy scenarios.

### The bug it caught

The first run showed `OFOD` at **+128%** acreage response. Cause: `base_areas.csv`
carries flat constant placeholders — `COTT` 2.0, `OFIB` 1.0, `OFOD` 5.0, `SETA` 3.0
kha in every one of the 248 regions — while `OFOD` has a genuine CAPRI elasticity
of 4.27 against a default of 0.12. Since PMP curvature scales as `1/(eps * x0)`, a
real elasticity on an invented anchor explodes under any shock.

`detect_synthetic_base_activities` now blocks these four from receiving real
elasticities. After the guard, `OFOD` sits at 9.0% in both configurations and the
cereal responses are plausible (`CORN` +16.3%, `SWHE` +11.3% for a +20% shock).

The lognormal fingerprint detector could not see these columns: it looks for a
coefficient of variation near 0.10, and a flat constant has a CV of exactly zero.
`tools/detect_synthetic_columns.py` now reports both signatures, which surfaced a
fifth case — `variable_costs.csv` `OANI` is a flat 300.0 EUR in all 248 regions.

---

## Files

| Path | |
|---|---|
| `capri_python/supply/capri_pmp.py` | new — dampening, share term, group map, provenance, guard |
| `capri_python/supply/supply_module.py` | calibrator takes share terms; crude cap removed |
| `tools/scenario_elasticity_check.py` | new — shock comparison and asymmetry report |
| `tools/detect_synthetic_columns.py` | extended to constant placeholders |
| `capri_python/tests/test_capri.py` | +3 guard tests |
| `capri_data/DATA_SOURCING_REGISTRY.json` | `base_areas.csv` and `variable_costs.csv` corrected |

Legacy behaviour is preserved for comparison:
`SupplyModule(data, eps, use_capri_elasticities=False)`.

## What is still open

- **Route B** — cross-group VB terms replacing the `rho = 0.05/(n-1)` off-diagonal
  heuristic. Unblocked now that `EPRD_TO_GRP` is known.
- **Coverage** — 26 of 40 activities still on literature defaults. Permanent crops
  and livestock are the gap, and they are what drives the 7.97 asymmetry ratio.
- **The four placeholder base areas** — `COTT`, `OFIB`, `OFOD`, `SETA` need real
  COCO or CAPREG activity levels before they can be wired.
- **Validation against `capri_pela_own_elasticities.csv`** — already in
  `capri_data/validation/`, not yet used to check realised versus target elasticities.
