# Changelog

Recorded because the project's documentation had drifted in **both** directions:
claims of validation outlived their truth (the CAP policy layer was inert while
documented as validated), and claims of failure outlived their fix (the pulse
elasticity sign error and the DE60 non-convergence had both been resolved long
before anyone retired the note). Limitations should be re-measured, not
inherited.

Full provenance for every entry is in `capri_data/DATA_SOURCING_REGISTRY.json`.

---

## Validation status

| Component | Reference | Result |
|---|---|---|
| Market prices | CAPRI `PMRK` | 12/12 within 15% |
| 2030 projection | CAPRI 2030 reference run | correlation **+0.997**, total area within 2% |
| Carbon MACC | EcAMPA 2 (JRC 2016) | agrees at €50/t |
| Fertiliser | CAPRI `p_FertPerHa` | ~10% |
| Feed, monogastrics | CAPRI capreg reference | within ~5% |
| CAP budget | Real EU CAP | €58.8bn vs ~€55–58bn |
| Nitrogen balance | Eurostat gross N balance | median 54 vs ~45–50 kg N/ha |
| Water demand | Known EU irrigation geography | Mediterranean 79%, correct hotspots |
| Biofuel | Observed EU statistics | both within 10% |
| **Total cereal output** | **EU Agricultural Outlook 2017-2030 (DG AGRI/JRC)** | **297.2 Mt vs ~300 Mt — ratio 0.99** |
| **Farm-to-Fork scenarios** | Published CAPRI (JRC121368) | reported as a range; CAPRI's figure falls inside it for oilseeds |

---

## New capability

**Projection layer (`projection/`)** — versioned trajectory input with mandatory
provenance, weighted least-squares reconciliation, recursive loop, and baseline
drift reported separately from the policy increment. Driven by CAPRI's own
`captrd` baseline. Two correctness properties hold: a null trajectory reproduces
the comparative-static result **exactly**, and the projection reproduces CAPRI's
independent 2030 reference at +0.997.

This changes what the model *is*: it is no longer purely comparative-static, and
the README description was updated accordingly. Three caveats bound the claim —
validation covers a **single step** to 2030, not multi-period recursion; only
**perennial areas** are carried between periods, so herds are re-optimised each
period and livestock adjustment speed is overstated; and the trajectory is
**exogenous**, adopted rather than generated.

**Nitrogen intensity margin (`supply/intensity.py`)** — N per hectare is now a
decision variable with a Mitscherlich yield response, normalised so the base
year is reproduced exactly. Without it a nitrogen constraint could only cut
*area*, overstating the response roughly tenfold.

**Farm-to-Fork instruments** — all four CAPRI targets are now representable:
landscape elements (a fallow floor, as `landscape.gms` does it), organic area
share (I/O adjustment, as `organic_io.gms` does it), the tiered nutrient-surplus
rule, and the pesticide yield-loss channel.

**Base-year reconciliation (`data/reconcile_base.py`)** — reproduces CAPRI's
`coco`/`capreg` step: weighted least-squares projection onto accounting
identities, the same Highest Posterior Density family CAPRI uses. Reconciling
already-consistent data changes it by 9.09e-13 (machine precision), the gate that
catches a reconciler which rewrites rather than reconciles.

Tested against the three area vintages in `capri_data/archive/` — a Eurostat-derived
matrix (107,828 kha), COCO-reconciled (125,775), CAPRI final (144,719). It closes
**32%** of the distance. **That test is weaker than it first appears**: the
"Eurostat" file is already mapped to CAPRI activity codes, and 35% of its values
carry repeating decimals, so it is share-allocated rather than measured regional
data. It measures recovery of regional detail from allocated totals, *not* whether
raw Eurostat can be turned into CAPRI data — which remains untested. **The residual is definitional, not a
reconciliation failure**: GRAS alone is 18,393 kha of it (Eurostat 13,640 vs CAPRI
44,819 — different grassland definitions), OLIV 1,884 vs 4,808, and CORN runs the
other way because Eurostat's maize includes silage.

That splits a problem previously treated as one: **reconciliation** (making numbers
internally consistent) is now solved and ours; **concordance** (mapping external
statistical categories onto CAPRI activities) is separate and, on this evidence,
larger. Conflating them is why "just use Eurostat" looks easier than it is.

**Water demand (`water/`)** and **farm-income distribution (`income/`)**.

---

## Defects fixed

Every one was surfaced by an **external reference**, not by an internal
consistency check. That is the single most useful lesson in this log.

| Defect | Effect |
|---|---|
| CAP support double-counted | ~29% supply inflation in **every scenario ever run** |
| All policy instruments inert | Scenarios returned baseline numbers while reporting success — four separate causes |
| Nitrogen balance meaningless | Median −170,196 kg N/ha, from a grass fresh-matter artifact and a manure-N scale error |
| Permanent crops destroyed | Olives 78% error in every base solve; invisible to a fidelity measure that only checked annual crops |
| **Arable land bound cut the base year** | **Base fidelity 11.28% → 0.47%.** ARABLE land and crop areas disagreed in 54 of 248 regions by 9,960 kha (LT02 12.7x); the solver shed 9,976 kha, losing most cereals in those regions. Not solver noise — a data conflict, and fixable |
| Grain maize silently excluded | `MAIZ` (not an activity) listed instead of `CORN` in three modules — fertiliser group, pesticide target, abatement N₂O |
| Permanent-crop elasticities inverted | 10× *less* elastic than annuals, where CAPRI has them 2.47× *more* |
| Livestock yields unit-inconsistent | ~56 regions in tonnes, ~192 in kg; drove the MACC 2–3× too high |
| Consumption fabricated | A clamp invented supply where exports exceeded production |
| Set-aside mapped to the wrong instrument | Modelled as an arable cut; CAPRI uses a fallow floor |
| Market price test asserting stale values | Failed for the life of the project against deliberately-corrected data |
| Hard-coded 2017 paths | Re-basing would have silently fallen back to literature defaults |
| Organic target missing | Only a payment *rate* existed, not an area *target* |

---

## Farm-to-Fork comparison (JRC121368)

**Now a single estimate, not a range.** The plant-protection cost was derived
from CAPRI data (see below), which removed the reason for reporting bounds.

| | CAPRI-mod | CAPRI published (JRC121368) |
|---|---|---|
| Cereals | −18.5% | −15% |
| Oilseeds | −12.3% | −15% |
| Permanent / fruit & veg | −9.4% | −12% |

Oilseeds (1.07x) and permanent crops (0.86x) are close. **Cereals still
**All three land within ±25% of CAPRI, with errors in both directions** —
cereals 1.24x over, oilseeds 0.86x and permanent crops 0.78x under. Errors that
do not share a sign argue against a systematic bias.

A large part of the previously-reported cereals overshoot was **a measurement
error of mine, not a model defect**: every comparison had been run with
`max_outer_iter=1`, which executes one supply–market pass and so suppresses the
price feedback. When EU cereal supply falls, prices rise and cushion the area
response; CAPRI's published results include that, ours did not. Running to
convergence moved cereals from −22.6% to −18.5%, closing roughly half the gap.

A convenience setting chosen for speed while iterating became a published
result — the same class of mistake as the stale documentation found elsewhere
here: correct in its moment, wrong once the context changed.

**Fixed at the cause, not the symptom.** The old code printed the
non-convergence warning only when `verbose=True`, so every comparison — all run
with `verbose=False` — failed in silence. A non-converged run now always raises
a `RuntimeWarning` and records `metadata["outer_converged"] = False`, and
`test_unconverged_run_warns_and_is_recorded` pins both that it fires when it
should and stays quiet when it shouldn't.

**The pesticide cost is CAPRI-derived, not assumed.** Built as
`PESTOTAL (g a.i./ha, capreg) / 1000 x UVAB.PLAP (EUR/kg, coco)`. Two unit checks
were run rather than assumed: summing PESTOTAL x area over Spain gives 89,888 t
against a national quantity of 83,104 t (within 8%, fixing the unit as grams per
hectare), and `UVAB x NETF` reproduces `EAAB` exactly at EUR 1,110.7m — which is
Spain's real annual pesticide spend.

**Confirmed independently on a second country.** Both checks were re-run from
scratch on Italy and passed *better*: reconciliation within 2% (against Spain's
8%), and `UVAB x NETF` matching `EAAB` to the decimal (947.6 vs 947.59 m EUR).
Two countries agreeing on the unit interpretation is far stronger than one.

**Country variation is real**, which is why one country was not enough: Italian
costs run a median 1.15x Spanish, but from 0.95x for maize to ~1.7x for olives,
citrus and apples. Mediterranean permanent crops are where the two disagree most.
Shares are now the median across both countries.

---

## Known assumptions carrying weight

- **`PPP_COST_SHARE`** — now **CAPRI-derived** (from `PESTOTAL` x `UVAB.PLAP`,
  two member states, units verified independently in each), no longer assumed.
  The residual uncertainty is country coverage: ES and IT differ by a median
  1.15x, and by ~1.7x for Mediterranean permanent crops.
- **Permanent-crop elasticities** — CAPRI's *relative* structure (2.47× annuals),
  not its absolute levels, which are member-state market elasticities rather than
  regional PMP targets.
- **Organic yield gap 20%, cost premium 15%** — literature (Seufert 2012, Ponisio 2015).
- **Mitscherlich curvature k = 3.0** — agronomic literature; not tuned to fit CAPRI.

---

## Regression anchors

`capri_data/validation/REGRESSION_ANCHORS.json` + `tools/check_regression.py`.

A machine-checkable snapshot of the numbers that **external references**
validated. It reports *which validation broke*, not merely that a number moved —
each anchor names the reference it was checked against, so a failure points at a
source you can go and re-read.

```bash
python tools/check_regression.py            # exit 1 on breach
python tools/check_regression.py --update   # accept an intended change
```

Eight cheap anchors run every time (regions, convergence, base fidelity, olive
fidelity, N surplus, world balance, price reproduction, CAP budget); two
expensive ones (MACC, projection correlation) are recorded but checked on demand.

Two design points worth keeping:

- **Olives have their own anchor.** The aggregate base-fidelity measure looks
  only at annual crops and did not see the permanent-crop collapse. An anchor
  that shares a blind spot with the bug it should catch is worthless.
- **`--update` is how an intended change is accepted, not how a failure is
  silenced.** Verified to exit 1 on a breach and 0 when clean, so it is usable
  in CI.

Run it before and after any base-year re-base — that is the situation this
exists for.

---

## Still open

- **Cereals sit 1.24x above CAPRI's published figure** (−18.5% against −15%),
  within the uncertainty of CAPRI's own numbers — JRC121368 states its production
  impacts are likely overestimated, which would widen the gap, not close it.
- **Pesticide cost shares rest on two member states** (ES, IT), whose costs differ
  by a median 1.15x and by ~1.7x for Mediterranean permanent crops. A third
  country would narrow that.
- Phase 2 (base-year update) not started; the base year remains 2017.
