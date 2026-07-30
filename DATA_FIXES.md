# Data extraction fixes

Two extraction faults, plus one solver-budget issue surfaced by the second fix.

Gate before / after:

| Check | Before | After |
|---|---|---|
| Validator | 11 pass, 1 warn, 0 fail | 11 pass, 1 warn, 0 fail |
| Base-year market fidelity | 12/12 | 12/12 |
| Supply convergence (30-region sample) | 27/30 | **30/30** |
| Test suite | 10 tests | **12 tests, all passing** |

---

## Fix 1 — activity-code corruption

Four spellings of CAPRI's `OANI` ("other animals") were in circulation, and the
canonical activity list used none of the ones the modules used:

| Spelling | Bytes | Where |
|---|---|---|
| `OANI` | `4F 41 4E 49` | CAPRI truth (`capreg/regio_sets.gms`) — reference files only |
| `OАНИ` | `4F 0410 041D 0418` | Cyrillic homoglyphs — `definitions.py`, `loaders.py`, `model.py`, `utils.py`, 4 data files |
| `OANII` | doubled I | `feed_module.py`, `producer_prices.csv` |
| `OАНИИ` | Cyrillic + doubled I | `environmental_module.py` |

`definitions.py` declared the canonical activity list with the Cyrillic form
while the feed and environmental modules looked up the doubled-I forms, so every
"other animals" feed requirement and emission coefficient silently missed and
fell through to a default. No error was ever raised.

Fixed by `tools/normalize_activity_codes.py` — 25 occurrences across 12 files
rewritten to `OANI`. Idempotent.

Two guard tests now prevent recurrence: `test_no_corrupted_activity_codes` and
`test_data_headers_are_ascii`.

**Correction to an earlier concern.** `cons_levls.gms` does rescale `OANI` by
1000, but it reverses the operation at line 2617, so it is an internal transform
around CAPRI's own `cons_yields` bounds and not a property of the delivered data.
No unit correction was needed. Checked empirically after the join: `OANI` sits at
0.0031, in line with `BROI` at 0.0021 and `LAYS` at 0.0186.

Convergence rose from 27/30 to 29/30 on this fix alone.

---

## Fix 2 — synthetic yields replaced with CAPRI's own

`yields.csv` was labelled `REAL_CAPRI` in the sourcing registry. Sixteen of its
forty columns carried a synthetic fingerprint: a constant multiplied by lognormal
noise at sigma 0.10, giving a coefficient of variation between 0.089 and 0.101
across all 248 regions. Real regional yields scatter at CV 0.2–0.5.

Every livestock yield was generated. So was `GRAS` — which explains the +388%
deviation against the trends file recorded in the point-3 notes. That was never a
fresh-versus-dry-matter unit problem; the model side was simply synthetic, so the
comparison had nothing to measure.

CAPRI's real crop yields were already in the repository, unused, at
`capri_data/sources/coco/coco_yields.csv`. They appeared incompatible because
COCO keys regions as `DE110000` and the model uses `DE11`. The crosswalk is
`NUTS2 + "0000"`, validated against the 1455 authoritative codes in
`gams/capreg/regio_sets.gms`: **160 of 248 regions match**.

`tools/merge_coco_yields.py` applies it under the point-3 discipline — one input
only, certain region matches only, non-market activities excluded, and a margin
guard reusing the validator's own `_ARTIFACT_LOSS` threshold so no substitution
may push a healthy crop into implausible loss.

Result: **1026 cells replaced, 0 rejected by the margin guard.** Median absolute
deviation of the synthetic values that were overwritten:

```
TAGR 171.6   CITR 83.8   OLIV 80.9   TOMA 49.7   OATS 39.9
OOIL 33.8    OCER 30.7   APPL 24.1   RYEM 17.3   PULS 15.7
DWHE 14.8    POTA 14.7   SWHE 12.8   SUNF 12.7   BARL 12.6
SOYA 12.1    SUGB 10.4   RAPE  9.4   TOBA  8.8
```

### Coverage is partial — read this before quoting the fix

160 matched regions is not 160 regions of real data per column. COCO has gaps,
and 1140 cells were skipped as zero or missing. Measured against regions where
the crop is actually grown:

- Best case 43% (`SWHE`, `BARL`); staples generally 30–43%
- `TOBA` 10.5%, `OOIL`/`SOYA`/`DWHE` 17–19%
- `CITR`, `TAGR`, `OLIV`, `OATS`, `TOMA`, `APPL` around 1% — still effectively synthetic

The registry now records this per column, with measured coverage percentages, so
the file can no longer claim more than it holds. `tools/detect_synthetic_columns.py`
re-runs the fingerprint audit and cross-checks it against the registry; it reports
no conflicts.

### Update after coco2.csv arrived — the merge is NOT validated

`coco2.csv` (the real COCO2 dump, 7.9M rows, explicit years) provides an
independent 2017 national benchmark. Units are kg/ha; divide by 1000 for t/ha,
confirmed against SWHE at 5143.9 kg/ha.

Aggregating the model's regional yields to national level with area weights and
comparing against COCO2 national 2017, over 328 country x crop pairs:

| | median absolute error vs COCO2 2017 |
|---|---|
| synthetic yields (before merge) | 20.1% |
| merged COCO yields (after) | 20.9% |

Restricting to the 114 aggregates the merge actually moved by more than 1%:
12.2% before, 13.8% after, with only **36% of aggregates improving**.

**The merge produced no measurable accuracy gain.** The vintage corruption
plausibly cancels the benefit of using real numbers.

One caveat in the other direction: this test measures national aggregates, so it
cannot see regional *signal* quality. The synthetic values were built around a
national anchor with 10% noise, so they sit close to national means by
construction while carrying no real regional variation at all. The merged values
carry genuine regional pattern — which is what PMP cross-effects need — at a
possibly wrong level. Whether that trade is worth making is a modelling judgement,
not something this test settles.

Revert with:

    cp capri_data/2017/supply/yields.csv.pre_coco_merge \
       capri_data/2017/supply/yields.csv

### Vintage caveat — the underlying cause

`coco_provenance.json` records the source of `coco_yields.csv` as
`agriprod_and_fss_data_export.xlsx p_agriProd YILD, **latest year per region/crop**`.

That is an Excel export, not a GDX read, and "latest year per cell" means the file
is a ragged vintage mix rather than a 2017 snapshot. `coco_yields.csv` dropped its
year column, so the per-cell vintage is not recoverable from it. Its sibling from
the same pipeline, `coco_producer_prices.csv`, kept the column and shows the
spread: 1988 to 2020, with 548 cells at 2020, 126 at 2005, 55 at 1999 — and only
8 at 2017.

If yields were exported the same way, the values merged in Fix 2 are real
measurements from mostly the wrong years. That is likely still an improvement over
invented numbers, since yields move far more slowly than prices and real agronomic
variation across regions is the property PMP needs. But it is not the clean win the
table above implies, and the base-fidelity test cannot detect it because that test
runs on market prices, not yields.

Treat the merged columns as *real but vintage-uncertain* until the file is
re-exported at a fixed year. `yields.csv.pre_coco_merge` allows a revert.



The yield merge dropped DE11 out of convergence. The cause was not a bad cell:
all seven changed values moved by factors of 0.78–0.97, which is what real yields
replacing generated ones should look like. The solver returned
`maximum number of function evaluations is exceeded` while sitting within 8% of
base on every activity — it had run out of iterations, not diverged.

The regional programme is a convex QP with a positive-definite PMP matrix and
linear constraints, so the optimum is unique and more iterations approach the
same point. `SOLVER_MAXITER` raised from 1000 to 3000, which clears the full
sample at roughly 8% extra runtime. Verified rather than assumed: the maximum
relative difference in solved activity levels between 3000 and 6000 iterations is
**0.0000%**.

---

## What remains

0. **Re-export COCO from the GDX at a fixed year** — highest value item. See the
   vintage caveat above. Files to look for in the CAPRI tree:
   `results/coco/coco1_output.gdx`, `results/coco/coco1_output/coco1_output_<MS>.gdx`,
   and the `dat/` folder. None are in `gams.zip`, which holds only the source tree.
1. **NUTS2 crosswalk for the 88 unmatched regions** — FR 21, IT 21, DE 15, EL 9,
   PL 7, then FI/IE/HR/HU/SI/LT. These sit on the old classification
   (`FR21 Champagne-Ardenne` vs `FRF2`) and need a real mapping table, not a rule.
   `gams/capreg/` holds official Eurostat correspondence tables, but only for
   1995-2010. The French and Italian renamings happened in NUTS 2016 and 2021, so
   those tables stop short; the 2013/2016/2021 correspondence is needed.
2. **COCO gaps** — even matched regions are only 30–43% real for staples. Worth
   checking whether a fuller COCO extract exists in the CAPRI results tree.
3. **Livestock yields** — all still synthetic. COCO carries no livestock, so these
   need `capreg` output.
4. **The margin warning** — 419 specialty crops still show implausible post-CAP
   losses (`DEA1/OVEG -65593`). Unrelated to these fixes; points at price-data
   gaps for specialty crops.
5. **Vintage mixing** — 2017 base with 2021 trade is still live and untouched here.

## Reproducing

```bash
python tools/normalize_activity_codes.py .
python tools/merge_coco_yields.py --capri-gams /path/to/capri/gams --dry-run
python tools/merge_coco_yields.py --capri-gams /path/to/capri/gams
python tools/detect_synthetic_columns.py capri_data
python tools/run_tests.py          # or: pytest capri_python/tests/ -v
```

`yields.csv.pre_coco_merge` holds the pre-merge backup.
